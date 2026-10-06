"""Pre-computed numbers, rebuilt by the worker after every import.

Each rebuild throws away an organization's summary rows and recomputes them
from its raw orders in SQL. Recomputing everything is simpler than updating
in place and always gives the right answer. PostgreSQL does it in seconds even
for hundreds of thousands of orders.

Days are calendar days in UTC.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

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

# One row per customer with their totals. ON CONFLICT updates an existing row
# and leaves columns filled by later steps (RFM scores, churn...) untouched.
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


STATEMENTS = (
    "DELETE FROM daily_revenue WHERE organization_id = :org",
    REBUILD_DAILY_REVENUE,
    "DELETE FROM daily_customer_revenue WHERE organization_id = :org",
    REBUILD_DAILY_CUSTOMER_REVENUE,
    UPSERT_CUSTOMER_TOTALS,
    DELETE_METRICS_WITHOUT_ORDERS,
)


def recalculate_metrics(db: Session, organization_id: int) -> None:
    """Rebuild one organization's summary tables. Does not commit."""
    for statement in STATEMENTS:
        db.execute(text(statement), {"org": organization_id})
