"""The customer list (with filters and CSV export) and one customer's detail.

Per-customer totals come from customer_metrics, which the worker fills after
each import. The detail page also lists that customer's latest orders, a
small indexed lookup rather than a heavy calculation.
"""

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import Select, func, or_, select

from app.csv_export import csv_response
from app.deps import CurrentUser, DbSession
from app.models import Customer, CustomerMetrics, Order, OrderItem
from app.schemas import (
    CustomerDetail,
    CustomerFilters,
    CustomerListParams,
    CustomerOrder,
    CustomerPage,
    CustomerRow,
)

router = APIRouter(prefix="/customers", tags=["customers"])

RECENT_ORDERS = 100

# Customers imported moments ago may not have a metrics row yet: count them as 0.
orders_column = func.coalesce(CustomerMetrics.frequency, 0)
spent_column = func.coalesce(CustomerMetrics.monetary, 0)

SORT_COLUMNS = {
    "name": Customer.name,
    "total_spent": spent_column,
    "orders": orders_column,
    "last_order": CustomerMetrics.last_order_at,
    "lifetime_value": CustomerMetrics.lifetime_value,
    "churned_at": CustomerMetrics.churned_at,
    "churn_risk": CustomerMetrics.churn_score,
}
SCORE_COLUMNS = {
    "r": CustomerMetrics.r_score,
    "f": CustomerMetrics.f_score,
    "m": CustomerMetrics.m_score,
}


def _start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def _escape_like(text: str) -> str:
    """Make % and _ in a search match themselves instead of acting as wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def customers_query(organization_id: int, filters: CustomerFilters) -> Select:
    query = (
        select(
            Customer.id,
            Customer.external_id,
            Customer.name,
            Customer.email,
            orders_column.label("orders"),
            spent_column.label("total_spent"),
            CustomerMetrics.first_order_at,
            CustomerMetrics.last_order_at,
            CustomerMetrics.segment,
            CustomerMetrics.r_score,
            CustomerMetrics.f_score,
            CustomerMetrics.m_score,
            CustomerMetrics.lifetime_value,
            CustomerMetrics.is_churned,
            CustomerMetrics.churned_at,
            CustomerMetrics.churn_score.label("churn_risk"),
            CustomerMetrics.churn_reasons,
        )
        .outerjoin(
            CustomerMetrics,
            (CustomerMetrics.organization_id == Customer.organization_id)
            & (CustomerMetrics.customer_id == Customer.id),
        )
        .where(Customer.organization_id == organization_id)
    )

    if filters.search and filters.search.strip():
        pattern = f"%{_escape_like(filters.search.strip())}%"
        query = query.where(
            or_(
                Customer.name.ilike(pattern, escape="\\"),
                Customer.email.ilike(pattern, escape="\\"),
                Customer.external_id.ilike(pattern, escape="\\"),
            )
        )
    if filters.min_orders is not None:
        query = query.where(orders_column >= filters.min_orders)
    if filters.max_orders is not None:
        query = query.where(orders_column <= filters.max_orders)
    if filters.min_spent is not None:
        query = query.where(spent_column >= filters.min_spent)
    if filters.max_spent is not None:
        query = query.where(spent_column <= filters.max_spent)
    if filters.last_order_from is not None:
        query = query.where(CustomerMetrics.last_order_at >= _start_of_day(filters.last_order_from))
    if filters.last_order_to is not None:
        # "to" includes that whole day
        end = _start_of_day(filters.last_order_to + timedelta(days=1))
        query = query.where(CustomerMetrics.last_order_at < end)

    if filters.segment:
        query = query.where(CustomerMetrics.segment.in_(filters.segment))
    for letter, column in SCORE_COLUMNS.items():
        low = getattr(filters, f"{letter}_min")
        high = getattr(filters, f"{letter}_max")
        if low is not None:
            query = query.where(column >= low)
        if high is not None:
            query = query.where(column <= high)
    if filters.min_lifetime_value is not None:
        query = query.where(CustomerMetrics.lifetime_value >= filters.min_lifetime_value)
    if filters.max_lifetime_value is not None:
        query = query.where(CustomerMetrics.lifetime_value <= filters.max_lifetime_value)
    if filters.status is not None:
        query = query.where(CustomerMetrics.is_churned.is_(filters.status == "churned"))
    if filters.min_churn_risk is not None:
        query = query.where(CustomerMetrics.churn_score >= filters.min_churn_risk / 100)

    column = SORT_COLUMNS[filters.sort]
    ordered = column.asc() if filters.direction == "asc" else column.desc()
    return query.order_by(ordered.nulls_last(), Customer.id)


@router.get("")
def list_customers(
    user: CurrentUser, db: DbSession, params: Annotated[CustomerListParams, Query()]
) -> CustomerPage:
    query = customers_query(user.organization_id, params)
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    offset = (params.page - 1) * params.page_size
    rows = db.execute(query.limit(params.page_size).offset(offset)).mappings()
    return CustomerPage(
        total=total,
        page=params.page,
        page_size=params.page_size,
        items=[CustomerRow.model_validate(dict(row)) for row in rows],
    )


@router.get("/export.csv")
def export_customers(
    user: CurrentUser, db: DbSession, filters: Annotated[CustomerFilters, Query()]
) -> Response:
    """Every customer matching the filters (not just one page), as a CSV file."""
    rows = db.execute(customers_query(user.organization_id, filters)).all()
    header = [
        "customer_id",
        "name",
        "email",
        "orders",
        "total_spent",
        "first_order_date",
        "last_order_date",
        "segment",
        "r_score",
        "f_score",
        "m_score",
        "lifetime_value",
        "status",
        "churned_on",
        "churn_risk_percent",
        "churn_reasons",
    ]
    lines = [
        [
            row.external_id,
            row.name or "",
            row.email or "",
            row.orders,
            row.total_spent,
            row.first_order_at.date().isoformat() if row.first_order_at else "",
            row.last_order_at.date().isoformat() if row.last_order_at else "",
            row.segment or "",
            row.r_score or "",
            row.f_score or "",
            row.m_score or "",
            row.lifetime_value if row.lifetime_value is not None else "",
            "" if row.is_churned is None else ("churned" if row.is_churned else "active"),
            row.churned_at.isoformat() if row.churned_at else "",
            "" if row.churn_risk is None else round(row.churn_risk * 100),
            "; ".join(row.churn_reasons or []),
        ]
        for row in rows
    ]
    return csv_response([header, *lines], filename=f"customers-{date.today().isoformat()}.csv")


@router.get("/{customer_id}")
def read_customer(customer_id: int, user: CurrentUser, db: DbSession) -> CustomerDetail:
    org = user.organization_id
    row = (
        db.execute(customers_query(org, CustomerFilters()).where(Customer.id == customer_id))
        .mappings()
        .one_or_none()
    )
    if row is None:
        # Also the answer for another organization's customer: don't reveal it exists.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")

    units = (
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .where(OrderItem.organization_id == org, OrderItem.order_id == Order.id)
        .scalar_subquery()
    )
    orders = db.execute(
        select(
            Order.id, Order.external_id, Order.ordered_at, Order.total_amount, units.label("items")
        )
        .where(Order.organization_id == org, Order.customer_id == customer_id)
        .order_by(Order.ordered_at.desc(), Order.id.desc())
        .limit(RECENT_ORDERS)
    ).mappings()

    total_spent = float(row["total_spent"])
    return CustomerDetail(
        **dict(row),
        average_order_value=round(total_spent / row["orders"], 2) if row["orders"] else None,
        recent_orders=[CustomerOrder.model_validate(dict(order)) for order in orders],
    )
