"""Database tables, defined as SQLAlchemy 2 models.

Organization isolation is enforced in two places:
1. Every API query filters by the logged-in user's organization_id.
2. Foreign keys between tenant tables include organization_id, e.g. an order
   points at (organization_id, customer_id). The database therefore rejects an
   order that belongs to one organization but points at another's customer.
   For that to work, each referenced table has a unique (organization_id, id).
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Predictable constraint names, so migrations can refer to them reliably.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Role(StrEnum):
    ADMIN = "admin"
    VIEWER = "viewer"


class ImportStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DELETING = "deleting"  # the worker is removing this import's orders


def id_column() -> Mapped[int]:
    return mapped_column(BigInteger, Identity(), primary_key=True)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = id_column()
    name: Mapped[str] = mapped_column(String(200))
    # ISO 4217 code (USD, GBP, EUR...). All of an organization's amounts are in this currency.
    currency: Mapped[str] = mapped_column(String(3), server_default="USD")
    created_at: Mapped[datetime] = created_at_column()


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        CheckConstraint("role IN ('admin', 'viewer')", name="role"),
    )

    id: Mapped[int] = id_column()
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    # Emails are unique across the whole app, so login needs no organization picker.
    # The API stores them lowercased.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = created_at_column()

    organization: Mapped[Organization] = relationship()


class Customer(Base):
    """A customer of the business. Customers never log in; they are only data."""

    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        # external_id is the customer ID from the business's own data.
        # Imports use it to recognise customers they have seen before.
        UniqueConstraint("organization_id", "external_id"),
    )

    id: Mapped[int] = id_column()
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    external_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = created_at_column()


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "external_id"),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
        ),
        ForeignKeyConstraint(
            ["organization_id", "import_job_id"],
            ["import_jobs.organization_id", "import_jobs.id"],
        ),
        Index("ix_orders_organization_id_import_job_id", "organization_id", "import_job_id"),
        # Most analytics queries ask "orders for this organization in this date range".
        Index("ix_orders_organization_id_ordered_at", "organization_id", "ordered_at"),
        Index("ix_orders_organization_id_customer_id", "organization_id", "customer_id"),
    )

    id: Mapped[int] = id_column()
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    customer_id: Mapped[int] = mapped_column(BigInteger)
    # The import that created this order, so deleting the import can remove it.
    import_job_id: Mapped[int | None] = mapped_column(BigInteger)
    external_id: Mapped[str] = mapped_column(String(100))
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Money is stored as an exact decimal, never a float, to avoid rounding errors.
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = created_at_column()


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "order_id"],
            ["orders.organization_id", "orders.id"],
        ),
        Index("ix_order_items_organization_id_order_id", "organization_id", "order_id"),
    )

    id: Mapped[int] = id_column()
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    order_id: Mapped[int] = mapped_column(BigInteger)
    product_code: Mapped[str] = mapped_column(String(64))
    product_name: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))


class CustomerMetrics(Base):
    """One row per customer, written by the worker. Columns are filled in by later steps."""

    __tablename__ = "customer_metrics"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
        ),
        CheckConstraint("r_score BETWEEN 1 AND 5", name="r_score"),
        CheckConstraint("f_score BETWEEN 1 AND 5", name="f_score"),
        CheckConstraint("m_score BETWEEN 1 AND 5", name="m_score"),
        CheckConstraint("churn_score BETWEEN 0 AND 1", name="churn_score"),
        Index("ix_customer_metrics_organization_id_segment", "organization_id", "segment"),
        Index("ix_customer_metrics_organization_id_churn_score", "organization_id", "churn_score"),
        Index("ix_customer_metrics_organization_id_churned_at", "organization_id", "churned_at"),
    )

    customer_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    # RFM: days since last order, number of orders (frequency), total spend (monetary).
    recency_days: Mapped[int | None] = mapped_column(Integer)
    frequency: Mapped[int | None] = mapped_column(Integer)
    monetary: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    r_score: Mapped[int | None] = mapped_column(SmallInteger)
    f_score: Mapped[int | None] = mapped_column(SmallInteger)
    m_score: Mapped[int | None] = mapped_column(SmallInteger)
    segment: Mapped[str | None] = mapped_column(String(40))
    first_order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lifetime_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    is_churned: Mapped[bool | None] = mapped_column(Boolean)
    churned_at: Mapped[date | None] = mapped_column(Date)
    churn_score: Mapped[float | None] = mapped_column(Float)
    churn_reasons: Mapped[list | None] = mapped_column(JSONB)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'deleting')", name="status"
        ),
        Index("ix_import_jobs_organization_id_created_at", "organization_id", "created_at"),
    )

    id: Mapped[int] = id_column()
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    created_by_user_id: Mapped[int] = mapped_column(BigInteger)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), server_default=ImportStatus.QUEUED.value)
    rows_imported: Mapped[int] = mapped_column(Integer, server_default="0")
    rows_rejected: Mapped[int] = mapped_column(Integer, server_default="0")
    # Rows of orders that were already imported earlier, so were left alone.
    rows_skipped: Mapped[int] = mapped_column(Integer, server_default="0")
    # A list of {"row": n, "errors": [...]} for rows that failed validation.
    error_report: Mapped[list | None] = mapped_column(JSONB)
    # Why the whole file failed (e.g. a required column is missing).
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- Daily summaries -------------------------------------------------------
# The worker rebuilds these from the raw orders after every import. The
# dashboard's date-range filter adds up daily rows instead of scanning every
# order, so it stays fast however many orders there are.


class DailyRevenue(Base):
    """Revenue and order count per day for one organization."""

    __tablename__ = "daily_revenue"

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    orders: Mapped[int] = mapped_column(Integer)


class DailyCustomerRevenue(Base):
    """Revenue and order count per customer per day. Used for top customers in a date range."""

    __tablename__ = "daily_customer_revenue"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
        ),
        Index("ix_daily_customer_revenue_organization_id_day", "organization_id", "day"),
    )

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    orders: Mapped[int] = mapped_column(Integer)


# --- Step 3 analytics -------------------------------------------------------
# Rebuilt from the orders by the worker after every import and every night.


class OrganizationMetrics(Base):
    """Organization-wide numbers the per-customer metrics are based on."""

    __tablename__ = "organization_metrics"

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    # Metrics are measured as of the day of the latest order, not today, so
    # historical data still makes sense.
    as_of: Mapped[date] = mapped_column(Date)
    data_start: Mapped[date] = mapped_column(Date)
    # Share of active customers who churn in a month, over the last 12 complete
    # months. None when there isn't 90 days of history yet.
    monthly_churn_rate: Mapped[float | None] = mapped_column(Float)
    # How long a typical customer stays: 1 / monthly churn rate, capped.
    expected_lifetime_months: Mapped[float] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MonthlyChurn(Base):
    """Per calendar month: customers active when it began, and how many churned in it."""

    __tablename__ = "monthly_churn"

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    month: Mapped[date] = mapped_column(Date, primary_key=True)  # first day of the month
    active_customers: Mapped[int] = mapped_column(Integer)
    churned_customers: Mapped[int] = mapped_column(Integer)


class CohortRetention(Base):
    """Customers grouped by the month of their first order (their cohort), and how
    many of them ordered again N months later."""

    __tablename__ = "cohort_retention"

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    cohort_month: Mapped[date] = mapped_column(Date, primary_key=True)
    months_since: Mapped[int] = mapped_column(Integer, primary_key=True)
    customers: Mapped[int] = mapped_column(Integer)


# --- Step 4: churn prediction -------------------------------------------------


class ModelRun(Base):
    """One training run of an organization's churn model, with how well it tested."""

    __tablename__ = "model_runs"
    __table_args__ = (
        CheckConstraint("status IN ('trained', 'not_enough_data')", name="status"),
        CheckConstraint("used IN ('model', 'baseline')", name="used"),
        Index("ix_model_runs_organization_id_trained_at", "organization_id", "trained_at"),
    )

    id: Mapped[int] = id_column()
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    as_of: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    message: Mapped[str | None] = mapped_column(Text)  # why there is no model
    used: Mapped[str | None] = mapped_column(String(10))  # whose scores were saved
    test_cutoff: Mapped[date | None] = mapped_column(Date)
    train_rows: Mapped[int | None] = mapped_column(Integer)
    test_rows: Mapped[int | None] = mapped_column(Integer)
    test_churn_rate: Mapped[float | None] = mapped_column(Float)
    # ROC AUC: the chance that a customer who churned is scored riskier than one
    # who didn't. 0.5 is a coin flip, 1.0 is perfect.
    model_auc: Mapped[float | None] = mapped_column(Float)
    baseline_auc: Mapped[float | None] = mapped_column(Float)
    gbm_auc: Mapped[float | None] = mapped_column(Float)
    # Of the 10% scored riskiest, the share that really churned.
    model_top10: Mapped[float | None] = mapped_column(Float)
    baseline_top10: Mapped[float | None] = mapped_column(Float)
    scored_customers: Mapped[int | None] = mapped_column(Integer)
    coefficients: Mapped[dict | None] = mapped_column(JSONB)
