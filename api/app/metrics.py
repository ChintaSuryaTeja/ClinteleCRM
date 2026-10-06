"""Pre-computed numbers, rebuilt by the worker after every import and every night.

Each rebuild throws away an organization's summary rows and recomputes them
from its raw orders in SQL. Recomputing everything is simpler than updating
in place and always gives the right answer. PostgreSQL does it in seconds even
for hundreds of thousands of orders.

Definitions used throughout:
- Days are calendar days in UTC.
- "As of" is the day of the organization's latest order, not today, so
  historical data (like the demo dataset) still gives meaningful numbers.
- A customer churns when 90 days pass with no order. The churn date is the
  90th day. A customer who orders again later is active again, and can churn
  again, so one customer can have several churn events.
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import DailyRevenue, MonthlyChurn, OrganizationMetrics
from app.segments import segment_case_sql

CHURN_DAYS = 90
DAYS_PER_MONTH = 30.4375  # 365.25 / 12
MAX_LIFETIME_MONTHS = 36  # caps lifetime value when almost nobody churns
CHURN_RATE_WINDOW = 12  # months averaged for the organization's churn rate

# --- Daily summaries and per-customer totals (step 2) -----------------------

REBUILD_DAILY_REVENUE = """
INSERT INTO daily_revenue (organization_id, day, revenue, orders)
SELECT organization_id, (ordered_at AT TIME ZONE 'UTC')::date, SUM(total_amount), COUNT(*)
FROM orders
WHERE organization_id = :org
GROUP BY organization_id, (ordered_at AT TIME ZONE 'UTC')::date;
"""

REBUILD_DAILY_CUSTOMER_REVENUE = """
INSERT INTO daily_customer_revenue (organization_id, customer_id, day, revenue, orders)
SELECT organization_id, customer_id, (ordered_at AT TIME ZONE 'UTC')::date,
       SUM(total_amount), COUNT(*)
FROM orders
WHERE organization_id = :org
GROUP BY organization_id, customer_id, (ordered_at AT TIME ZONE 'UTC')::date;
"""

# One row per customer with their totals. ON CONFLICT updates an existing row.
UPSERT_CUSTOMER_TOTALS = """
INSERT INTO customer_metrics
    (customer_id, organization_id, frequency, monetary, first_order_at, last_order_at,
     computed_at)
SELECT customer_id, organization_id, COUNT(*), SUM(total_amount), MIN(ordered_at),
       MAX(ordered_at), now()
FROM orders
WHERE organization_id = :org
GROUP BY organization_id, customer_id
ON CONFLICT (customer_id) DO UPDATE SET
    frequency = EXCLUDED.frequency,
    monetary = EXCLUDED.monetary,
    first_order_at = EXCLUDED.first_order_at,
    last_order_at = EXCLUDED.last_order_at,
    computed_at = EXCLUDED.computed_at;
"""

# Customers whose orders were all deleted (with their import) lose their metrics row.
DELETE_METRICS_WITHOUT_ORDERS = """
DELETE FROM customer_metrics
WHERE organization_id = :org
  AND NOT EXISTS (
      SELECT 1 FROM orders
      WHERE orders.organization_id = :org AND orders.customer_id = customer_metrics.customer_id
  );
"""

# --- Churn per month (step 3) -----------------------------------------------
# For every calendar month from the first order to "as of":
#   active  = customers who had not churned when the month began: their latest
#             order before the month is less than 90 days before it
#   churned = churn events (90th day without an order) that fall in the month
# Every customer who churns in a month was active when it began, so the
# monthly churn rate active / churned is always between 0 and 1.
REBUILD_MONTHLY_CHURN = f"""
WITH order_days AS (
    SELECT DISTINCT customer_id, (ordered_at AT TIME ZONE 'UTC')::date AS day
    FROM orders
    WHERE organization_id = :org
),
gaps AS (
    SELECT customer_id, day,
           LEAD(day) OVER (PARTITION BY customer_id ORDER BY day) AS next_day
    FROM order_days
),
churn_events AS (
    -- 90 days passed without an order: the next one came more than 90 days
    -- later, or hasn't come by the "as of" day.
    SELECT day + {CHURN_DAYS} AS churn_day
    FROM gaps
    WHERE next_day - day > {CHURN_DAYS}
       OR (next_day IS NULL AND day + {CHURN_DAYS} <= :as_of)
),
months AS (
    SELECT generate_series(
        date_trunc('month', CAST(:data_start AS timestamp)),
        date_trunc('month', CAST(:as_of AS timestamp)),
        interval '1 month'
    )::date AS month
)
INSERT INTO monthly_churn (organization_id, month, active_customers, churned_customers)
SELECT :org,
       months.month,
       (SELECT COUNT(*) FROM gaps
         WHERE gaps.day < months.month
           AND gaps.day >= months.month - {CHURN_DAYS}
           AND (gaps.next_day IS NULL OR gaps.next_day >= months.month)),
       (SELECT COUNT(*) FROM churn_events
         WHERE churn_day >= months.month AND churn_day < months.month + interval '1 month')
FROM months;
"""

# --- Cohort retention (step 3) ----------------------------------------------
# A customer's cohort is the month of their first order. months_since counts
# calendar months from it: 0 is the first month (always the whole cohort).
REBUILD_COHORT_RETENTION = """
WITH first_months AS (
    SELECT customer_id,
           date_trunc('month', MIN(ordered_at AT TIME ZONE 'UTC'))::date AS cohort_month
    FROM orders
    WHERE organization_id = :org
    GROUP BY customer_id
),
active_months AS (
    SELECT DISTINCT customer_id, date_trunc('month', ordered_at AT TIME ZONE 'UTC')::date AS month
    FROM orders
    WHERE organization_id = :org
)
INSERT INTO cohort_retention (organization_id, cohort_month, months_since, customers)
SELECT :org,
       first_months.cohort_month,
       ((EXTRACT(YEAR FROM active_months.month) - EXTRACT(YEAR FROM first_months.cohort_month))
         * 12
        + EXTRACT(MONTH FROM active_months.month)
        - EXTRACT(MONTH FROM first_months.cohort_month))::int,
       COUNT(*)
FROM first_months
JOIN active_months ON active_months.customer_id = first_months.customer_id
GROUP BY 2, 3;
"""

# --- RFM scores, segment, churn status and lifetime value (step 3) ----------
# Scores rank each customer against the organization's other customers with
# PERCENT_RANK (0 for the lowest value, 1 for the highest). Customers with the
# same value get the same rank, so equal customers always get equal scores.
#   score = 1 + floor(5 * percent rank), at most 5
# Recency is ranked from oldest to newest, so the most recent buyers score 5.
#
# Lifetime value = what the customer spends per month x how many months a
# typical customer stays. "Per month" is over the time since their first
# order (at least one month).
UPDATE_CUSTOMER_SCORES = f"""
WITH base AS (
    SELECT customer_id,
           frequency,
           monetary,
           (first_order_at AT TIME ZONE 'UTC')::date AS first_day,
           (last_order_at AT TIME ZONE 'UTC')::date AS last_day,
           CAST(:as_of AS date) - (last_order_at AT TIME ZONE 'UTC')::date AS recency_days
    FROM customer_metrics
    WHERE organization_id = :org
),
scored AS (
    SELECT *,
           LEAST(5, 1 + FLOOR(5 * PERCENT_RANK() OVER (ORDER BY recency_days DESC)))::int AS r,
           LEAST(5, 1 + FLOOR(5 * PERCENT_RANK() OVER (ORDER BY frequency)))::int AS f,
           LEAST(5, 1 + FLOOR(5 * PERCENT_RANK() OVER (ORDER BY monetary)))::int AS m
    FROM base
)
UPDATE customer_metrics
SET recency_days = scored.recency_days,
    r_score = scored.r,
    f_score = scored.f,
    m_score = scored.m,
    segment = {segment_case_sql("scored.r", "scored.f", "scored.m")},
    is_churned = scored.recency_days >= {CHURN_DAYS},
    churned_at = CASE
        WHEN scored.recency_days >= {CHURN_DAYS} THEN scored.last_day + {CHURN_DAYS}
    END,
    lifetime_value = ROUND(
        scored.monetary
        / GREATEST(1, (CAST(:as_of AS date) - scored.first_day) / {DAYS_PER_MONTH})
        * CAST(:lifetime_months AS numeric),
        2
    ),
    computed_at = now()
FROM scored
WHERE customer_metrics.organization_id = :org
  AND customer_metrics.customer_id = scored.customer_id;
"""


def month_end(month: date) -> date:
    """Last day of the month that starts on `month`."""
    return (month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def is_complete_month(month: date, data_start: date, as_of: date) -> bool:
    """A month's churn rate is meaningful once it is over and 90 days of history
    came before it. Before that, nobody could have churned yet, so early months
    would always show 0%."""
    return month >= data_start + timedelta(days=CHURN_DAYS) and month_end(month) <= as_of


def churn_rate_and_lifetime(
    db: Session, organization_id: int, data_start: date, as_of: date
) -> tuple[float | None, float]:
    """The organization's monthly churn rate over its last 12 complete months
    (all churn events / all active customer-months), and the expected lifetime
    in months that follows from it."""
    rows = db.scalars(
        select(MonthlyChurn)
        .where(MonthlyChurn.organization_id == organization_id)
        .order_by(MonthlyChurn.month)
    ).all()
    window = [row for row in rows if is_complete_month(row.month, data_start, as_of)]
    window = window[-CHURN_RATE_WINDOW:]
    active = sum(row.active_customers for row in window)
    churned = sum(row.churned_customers for row in window)
    if active == 0:
        return None, MAX_LIFETIME_MONTHS
    rate = churned / active
    lifetime = MAX_LIFETIME_MONTHS if rate == 0 else min(MAX_LIFETIME_MONTHS, 1 / rate)
    return rate, lifetime


def _run(db: Session, sql: str, **params) -> None:
    db.execute(text(sql), params)


def recalculate_metrics(db: Session, organization_id: int) -> None:
    """Rebuild everything pre-computed for one organization. Does not commit."""
    org = organization_id

    # Step 2: daily summaries and per-customer totals.
    _run(db, "DELETE FROM daily_revenue WHERE organization_id = :org", org=org)
    _run(db, REBUILD_DAILY_REVENUE, org=org)
    _run(db, "DELETE FROM daily_customer_revenue WHERE organization_id = :org", org=org)
    _run(db, REBUILD_DAILY_CUSTOMER_REVENUE, org=org)
    _run(db, UPSERT_CUSTOMER_TOTALS, org=org)
    _run(db, DELETE_METRICS_WITHOUT_ORDERS, org=org)

    # Step 3: churn, cohorts, RFM and lifetime value, as of the latest order.
    _run(db, "DELETE FROM monthly_churn WHERE organization_id = :org", org=org)
    _run(db, "DELETE FROM cohort_retention WHERE organization_id = :org", org=org)
    data_start, as_of = db.execute(
        select(func.min(DailyRevenue.day), func.max(DailyRevenue.day)).where(
            DailyRevenue.organization_id == org
        )
    ).one()
    if as_of is None:  # no orders left
        _run(db, "DELETE FROM organization_metrics WHERE organization_id = :org", org=org)
        return

    _run(
        db,
        REBUILD_MONTHLY_CHURN,
        org=org,
        data_start=data_start,
        as_of=as_of,
    )
    _run(db, REBUILD_COHORT_RETENTION, org=org)

    rate, lifetime = churn_rate_and_lifetime(db, org, data_start, as_of)
    values = {
        "as_of": as_of,
        "data_start": data_start,
        "monthly_churn_rate": rate,
        "expected_lifetime_months": lifetime,
        "computed_at": datetime.now(UTC),
    }
    db.execute(
        insert(OrganizationMetrics)
        .values(organization_id=org, **values)
        .on_conflict_do_update(index_elements=["organization_id"], set_=values)
    )

    _run(
        db,
        UPDATE_CUSTOMER_SCORES,
        org=org,
        as_of=as_of,
        lifetime_months=lifetime,
    )
