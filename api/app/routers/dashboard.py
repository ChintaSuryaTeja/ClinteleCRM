"""Revenue analysis for a date range.

Everything here reads the daily summary tables the worker builds, never the
raw orders, so the response stays fast however many orders exist.
"""

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import Date, DateTime, cast, func, literal_column, select

from app.deps import CurrentUser, DbSession
from app.models import Customer, DailyCustomerRevenue, DailyRevenue
from app.schemas import DashboardOut, RevenuePoint, TopCustomer

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

Granularity = Literal["day", "week", "month"]
TOP_CUSTOMERS = 10


def pick_granularity(start: date, end: date) -> Granularity:
    """Daily bars for up to two months, weekly up to a year, monthly beyond that."""
    days = (end - start).days + 1
    if days <= 62:
        return "day"
    if days <= 366:
        return "week"
    return "month"


def period_start(day: date, granularity: Granularity) -> date:
    if granularity == "week":
        return day - timedelta(days=day.weekday())  # weeks start on Monday
    if granularity == "month":
        return day.replace(day=1)
    return day


def all_periods(start: date, end: date, granularity: Granularity) -> list[date]:
    """Every period from start to end, so days or months without orders still show as zero."""
    periods = []
    current = period_start(start, granularity)
    while current <= end:
        periods.append(current)
        if granularity == "day":
            current += timedelta(days=1)
        elif granularity == "week":
            current += timedelta(weeks=1)
        else:
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
    return periods


def average(revenue: float, orders: int) -> float | None:
    return round(revenue / orders, 2) if orders else None


@router.get("")
def dashboard(
    user: CurrentUser, db: DbSession, start: date | None = None, end: date | None = None
) -> DashboardOut:
    org = user.organization_id
    data_start, data_end = db.execute(
        select(func.min(DailyRevenue.day), func.max(DailyRevenue.day)).where(
            DailyRevenue.organization_id == org
        )
    ).one()

    if data_start is None:  # nothing imported yet
        return DashboardOut(
            currency=user.organization.currency,
            data_start=None,
            data_end=None,
            start=start,
            end=end,
            revenue=0,
            orders=0,
            average_order_value=None,
            customers=0,
            granularity="month",
            series=[],
            top_customers=[],
        )

    start = start or data_start
    end = end or data_end
    if start > end:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "start must be before end")

    in_range = (
        DailyRevenue.organization_id == org,
        DailyRevenue.day >= start,
        DailyRevenue.day <= end,
    )
    revenue, orders = db.execute(
        select(
            func.coalesce(func.sum(DailyRevenue.revenue), 0),
            func.coalesce(func.sum(DailyRevenue.orders), 0),
        ).where(*in_range)
    ).one()

    customer_in_range = (
        DailyCustomerRevenue.organization_id == org,
        DailyCustomerRevenue.day >= start,
        DailyCustomerRevenue.day <= end,
    )
    customers = db.scalar(
        select(func.count(func.distinct(DailyCustomerRevenue.customer_id))).where(
            *customer_in_range
        )
    )

    granularity = pick_granularity(start, end)
    # granularity is one of three fixed words, so it is safe to write into the SQL.
    # (Sent as a parameter, Postgres would see SELECT and GROUP BY as different.)
    period = cast(
        func.date_trunc(literal_column(f"'{granularity}'"), cast(DailyRevenue.day, DateTime)),
        Date,
    )
    totals_by_period = {
        row.period: row
        for row in db.execute(
            select(
                period.label("period"),
                func.sum(DailyRevenue.revenue).label("revenue"),
                func.sum(DailyRevenue.orders).label("orders"),
            )
            .where(*in_range)
            .group_by(period)
        )
    }
    series = []
    for day in all_periods(start, end, granularity):
        row = totals_by_period.get(day)
        period_revenue = float(row.revenue) if row else 0.0
        period_orders = int(row.orders) if row else 0
        series.append(
            RevenuePoint(
                period=day,
                revenue=period_revenue,
                orders=period_orders,
                average_order_value=average(period_revenue, period_orders),
            )
        )

    customer_revenue = func.sum(DailyCustomerRevenue.revenue)
    top = db.execute(
        select(
            Customer.id,
            Customer.external_id,
            Customer.name,
            customer_revenue.label("revenue"),
            func.sum(DailyCustomerRevenue.orders).label("orders"),
        )
        .join(
            Customer,
            (Customer.organization_id == DailyCustomerRevenue.organization_id)
            & (Customer.id == DailyCustomerRevenue.customer_id),
        )
        .where(*customer_in_range)
        .group_by(Customer.id)
        .order_by(customer_revenue.desc(), Customer.id)
        .limit(TOP_CUSTOMERS)
    )

    return DashboardOut(
        currency=user.organization.currency,
        data_start=data_start,
        data_end=data_end,
        start=start,
        end=end,
        revenue=float(revenue),
        orders=int(orders),
        average_order_value=average(float(revenue), int(orders)),
        customers=customers,
        granularity=granularity,
        series=series,
        top_customers=[
            TopCustomer(
                id=row.id,
                external_id=row.external_id,
                name=row.name,
                revenue=float(row.revenue),
                orders=int(row.orders),
            )
            for row in top
        ],
    )
