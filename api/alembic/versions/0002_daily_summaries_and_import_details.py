"""daily summaries and import details

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-06 07:22:16.347815
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_revenue",
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("orders", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_daily_revenue_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("organization_id", "day", name=op.f("pk_daily_revenue")),
    )
    op.create_table(
        "daily_customer_revenue",
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("orders", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name=op.f("fk_daily_customer_revenue_organization_id_customer_id_customers"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_daily_customer_revenue_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint(
            "organization_id", "customer_id", "day", name=op.f("pk_daily_customer_revenue")
        ),
    )
    op.create_index(
        "ix_daily_customer_revenue_organization_id_day",
        "daily_customer_revenue",
        ["organization_id", "day"],
        unique=False,
    )
    op.add_column(
        "customer_metrics", sa.Column("first_order_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "customer_metrics", sa.Column("last_order_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "import_jobs", sa.Column("rows_skipped", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column("import_jobs", sa.Column("failure_reason", sa.Text(), nullable=True))
    op.add_column(
        "organizations",
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("organizations", "currency")
    op.drop_column("import_jobs", "failure_reason")
    op.drop_column("import_jobs", "rows_skipped")
    op.drop_column("customer_metrics", "last_order_at")
    op.drop_column("customer_metrics", "first_order_at")
    op.drop_index(
        "ix_daily_customer_revenue_organization_id_day", table_name="daily_customer_revenue"
    )
    op.drop_table("daily_customer_revenue")
    op.drop_table("daily_revenue")
