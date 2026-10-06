"""rfm churn and cohort tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-06 09:44:39.772007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cohort_retention",
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("cohort_month", sa.Date(), nullable=False),
        sa.Column("months_since", sa.Integer(), nullable=False),
        sa.Column("customers", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_cohort_retention_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint(
            "organization_id", "cohort_month", "months_since", name=op.f("pk_cohort_retention")
        ),
    )
    op.create_table(
        "monthly_churn",
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("active_customers", sa.Integer(), nullable=False),
        sa.Column("churned_customers", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_monthly_churn_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("organization_id", "month", name=op.f("pk_monthly_churn")),
    )
    op.create_table(
        "organization_metrics",
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("data_start", sa.Date(), nullable=False),
        sa.Column("monthly_churn_rate", sa.Float(), nullable=True),
        sa.Column("expected_lifetime_months", sa.Float(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_metrics_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("organization_id", name=op.f("pk_organization_metrics")),
    )
    op.create_index(
        "ix_customer_metrics_organization_id_churned_at",
        "customer_metrics",
        ["organization_id", "churned_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_customer_metrics_organization_id_churned_at", table_name="customer_metrics")
    op.drop_table("organization_metrics")
    op.drop_table("monthly_churn")
    op.drop_table("cohort_retention")
