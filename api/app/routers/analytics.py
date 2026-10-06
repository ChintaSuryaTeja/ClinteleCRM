"""Segments overview, cohort retention and churn history.

These read the tables the worker pre-computes (see app/metrics.py); no
endpoint here scans the raw orders.
"""

from datetime import date

from fastapi import APIRouter
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.metrics import is_complete_month
from app.models import CohortRetention, CustomerMetrics, MonthlyChurn, OrganizationMetrics
from app.schemas import (
    ChurnMonth,
    ChurnOut,
    CohortRow,
    RetentionOut,
    SegmentRow,
    SegmentsOut,
)
from app.segments import SEGMENTS

router = APIRouter(tags=["analytics"])


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


def share(part: float, whole: float) -> float:
    return round(part / whole, 4) if whole else 0.0


def organization_metrics(db: DbSession, organization_id: int) -> OrganizationMetrics | None:
    return db.get(OrganizationMetrics, organization_id)


@router.get("/segments")
def segments(user: CurrentUser, db: DbSession) -> SegmentsOut:
    """How many customers, and how much of the revenue, each segment holds."""
    org = user.organization_id
    org_metrics = organization_metrics(db, org)
    totals = {
        row.segment: row
        for row in db.execute(
            select(
                CustomerMetrics.segment,
                func.count().label("customers"),
                func.sum(CustomerMetrics.monetary).label("revenue"),
            )
            .where(CustomerMetrics.organization_id == org, CustomerMetrics.segment.is_not(None))
            .group_by(CustomerMetrics.segment)
        )
    }
    all_customers = sum(row.customers for row in totals.values())
    all_revenue = float(sum(row.revenue for row in totals.values()))
    rows = []
    for name in SEGMENTS:  # every segment, in display order, even when empty
        row = totals.get(name)
        customers = row.customers if row else 0
        revenue = float(row.revenue) if row else 0.0
        rows.append(
            SegmentRow(
                segment=name,
                customers=customers,
                revenue=revenue,
                customer_share=share(customers, all_customers),
                revenue_share=share(revenue, all_revenue),
            )
        )
    return SegmentsOut(
        as_of=org_metrics.as_of if org_metrics else None,
        currency=user.organization.currency,
        customers=all_customers,
        revenue=all_revenue,
        segments=rows,
    )


@router.get("/retention")
def retention(user: CurrentUser, db: DbSession) -> RetentionOut:
    """For each cohort (month of first order), the share still ordering N months later."""
    org = user.organization_id
    org_metrics = organization_metrics(db, org)
    if org_metrics is None:
        return RetentionOut(as_of=None, cohorts=[])

    counts: dict[date, dict[int, int]] = {}
    for row in db.scalars(select(CohortRetention).where(CohortRetention.organization_id == org)):
        counts.setdefault(row.cohort_month, {})[row.months_since] = row.customers

    last_month = org_metrics.as_of.replace(day=1)
    cohorts = []
    for cohort_month in sorted(counts):
        by_month = counts[cohort_month]
        size = by_month[0]
        # Every month up to "as of", so months when nobody came back show as 0.
        span = range(months_between(cohort_month, last_month) + 1)
        customers = [by_month.get(month, 0) for month in span]
        cohorts.append(
            CohortRow(
                cohort_month=cohort_month,
                size=size,
                customers=customers,
                rates=[share(count, size) for count in customers],
            )
        )
    return RetentionOut(as_of=org_metrics.as_of, cohorts=cohorts)


@router.get("/churn")
def churn(user: CurrentUser, db: DbSession) -> ChurnOut:
    """Monthly churn rate over time, plus where the customers stand today."""
    org = user.organization_id
    org_metrics = organization_metrics(db, org)
    if org_metrics is None:
        return ChurnOut(
            as_of=None,
            monthly_churn_rate=None,
            expected_lifetime_months=None,
            churned_customers=0,
            active_customers=0,
            months=[],
        )

    status_counts = dict(
        db.execute(
            select(CustomerMetrics.is_churned, func.count())
            .where(CustomerMetrics.organization_id == org)
            .group_by(CustomerMetrics.is_churned)
        )
        .tuples()
        .all()
    )
    months = [
        ChurnMonth(
            month=row.month,
            active_customers=row.active_customers,
            churned_customers=row.churned_customers,
            rate=share(row.churned_customers, row.active_customers)
            if row.active_customers
            else None,
        )
        for row in db.scalars(
            select(MonthlyChurn)
            .where(MonthlyChurn.organization_id == org)
            .order_by(MonthlyChurn.month)
        )
        # Only finished months with 90 days of history before them; see is_complete_month.
        if is_complete_month(row.month, org_metrics.data_start, org_metrics.as_of)
    ]
    return ChurnOut(
        as_of=org_metrics.as_of,
        monthly_churn_rate=org_metrics.monthly_churn_rate,
        expected_lifetime_months=org_metrics.expected_lifetime_months,
        churned_customers=status_counts.get(True, 0),
        active_customers=status_counts.get(False, 0),
        months=months,
    )
