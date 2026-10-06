"""Shapes of request and response bodies. Pydantic validates incoming JSON against these."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.models import Role

# Emails are compared case-insensitively, so store them lowercased.
Email = Annotated[EmailStr, AfterValidator(str.lower)]
Password = Annotated[str, Field(min_length=8, max_length=128)]


class SignupIn(BaseModel):
    organization_name: str = Field(min_length=1, max_length=200)
    # The currency the organization's sales data is in, e.g. USD or GBP.
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    email: Email
    password: Password


class LoginIn(BaseModel):
    email: Email
    password: str


class UserCreateIn(BaseModel):
    email: Email
    password: Password
    role: Role


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    currency: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: Role
    created_at: datetime


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: Role
    organization: OrganizationOut


# --- Imports ----------------------------------------------------------------


class ImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: Literal["queued", "running", "succeeded", "failed", "deleting"]
    rows_imported: int
    rows_rejected: int
    rows_skipped: int
    failure_reason: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ManualLineIn(BaseModel):
    product_code: str
    product_name: str | None = None
    # Text, like a cell in a file: the importer's own rules check them.
    quantity: str
    unit_price: str


class ManualOrderIn(BaseModel):
    """One order typed in by hand. It is imported exactly like a one-order file."""

    order_id: str
    order_date: str
    customer_id: str
    customer_name: str | None = None
    customer_email: str | None = None
    lines: list[ManualLineIn] = Field(min_length=1, max_length=100)


# --- Dashboard --------------------------------------------------------------
# Money is sent as a JSON number. That is precise enough for display; CSV
# exports use the exact database values instead.


class RevenuePoint(BaseModel):
    period: date  # first day of the day/week/month
    revenue: float
    orders: int
    average_order_value: float | None


class TopCustomer(BaseModel):
    id: int
    external_id: str
    name: str | None
    revenue: float
    orders: int


class DashboardOut(BaseModel):
    currency: str
    # The first and last day with any orders. None when nothing is imported yet.
    data_start: date | None
    data_end: date | None
    start: date | None
    end: date | None
    revenue: float
    orders: int
    average_order_value: float | None
    customers: int
    granularity: Literal["day", "week", "month"]
    series: list[RevenuePoint]
    top_customers: list[TopCustomer]


# --- Customers --------------------------------------------------------------

CustomerSort = Literal[
    "name", "total_spent", "orders", "last_order", "lifetime_value", "churned_at", "churn_risk"
]
Score = Annotated[int, Field(ge=1, le=5)]


class CustomerFilters(BaseModel):
    """Filters shared by the customer list and its CSV export. All are optional."""

    search: str | None = Field(default=None, max_length=200)
    min_orders: int | None = Field(default=None, ge=0)
    max_orders: int | None = Field(default=None, ge=0)
    min_spent: float | None = Field(default=None, ge=0)
    max_spent: float | None = Field(default=None, ge=0)
    last_order_from: date | None = None
    last_order_to: date | None = None
    # Step 3: segment builder. Repeat ?segment= to pick several.
    segment: list[str] = []
    r_min: Score | None = None
    r_max: Score | None = None
    f_min: Score | None = None
    f_max: Score | None = None
    m_min: Score | None = None
    m_max: Score | None = None
    min_lifetime_value: float | None = Field(default=None, ge=0)
    max_lifetime_value: float | None = Field(default=None, ge=0)
    status: Literal["active", "churned"] | None = None
    # Step 4: predicted chance of churning in the next 90 days, in percent.
    min_churn_risk: int | None = Field(default=None, ge=0, le=100)
    sort: CustomerSort = "total_spent"
    direction: Literal["asc", "desc"] = "desc"


class CustomerListParams(CustomerFilters):
    """The filters plus which page of results to return."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class CustomerRow(BaseModel):
    id: int
    external_id: str
    name: str | None
    email: str | None
    orders: int
    total_spent: float
    first_order_at: datetime | None
    last_order_at: datetime | None
    segment: str | None
    r_score: int | None
    f_score: int | None
    m_score: int | None
    lifetime_value: float | None
    is_churned: bool | None
    churned_at: date | None
    churn_risk: float | None  # 0 to 1; only for active customers
    churn_reasons: list[str] | None


class CustomerPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CustomerRow]


class CustomerOrder(BaseModel):
    id: int
    external_id: str
    ordered_at: datetime
    total_amount: float
    items: int


class CustomerDetail(CustomerRow):
    average_order_value: float | None
    recent_orders: list[CustomerOrder]


# --- Segments, retention, churn ----------------------------------------------


class SegmentRow(BaseModel):
    segment: str
    customers: int
    revenue: float
    customer_share: float  # 0 to 1
    revenue_share: float


class SegmentsOut(BaseModel):
    as_of: date | None
    currency: str
    customers: int
    revenue: float
    segments: list[SegmentRow]


class CohortRow(BaseModel):
    cohort_month: date
    size: int
    # Index 0 is the first month; index N is N months later, up to "as of".
    customers: list[int]
    rates: list[float]


class RetentionOut(BaseModel):
    as_of: date | None
    cohorts: list[CohortRow]


class ChurnMonth(BaseModel):
    month: date
    active_customers: int
    churned_customers: int
    rate: float | None


class ModelRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trained_at: datetime
    status: Literal["trained", "not_enough_data"]
    message: str | None
    used: Literal["model", "baseline"] | None
    test_cutoff: date | None
    train_rows: int | None
    test_rows: int | None
    test_churn_rate: float | None
    model_auc: float | None
    baseline_auc: float | None
    gbm_auc: float | None
    model_top10: float | None
    baseline_top10: float | None
    scored_customers: int | None


class ChurnOut(BaseModel):
    as_of: date | None
    monthly_churn_rate: float | None
    expected_lifetime_months: float | None
    churned_customers: int
    active_customers: int
    months: list[ChurnMonth]
    model: ModelRunOut | None
