"""churn model runs

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-06 10:29:06.749828
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("used", sa.String(length=10), nullable=True),
        sa.Column("test_cutoff", sa.Date(), nullable=True),
        sa.Column("train_rows", sa.Integer(), nullable=True),
        sa.Column("test_rows", sa.Integer(), nullable=True),
        sa.Column("test_churn_rate", sa.Float(), nullable=True),
        sa.Column("model_auc", sa.Float(), nullable=True),
        sa.Column("baseline_auc", sa.Float(), nullable=True),
        sa.Column("gbm_auc", sa.Float(), nullable=True),
        sa.Column("model_top10", sa.Float(), nullable=True),
        sa.Column("baseline_top10", sa.Float(), nullable=True),
        sa.Column("scored_customers", sa.Integer(), nullable=True),
        sa.Column("coefficients", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "status IN ('trained', 'not_enough_data')", name=op.f("ck_model_runs_status")
        ),
        sa.CheckConstraint("used IN ('model', 'baseline')", name=op.f("ck_model_runs_used")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_model_runs_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_runs")),
    )
    op.create_index(
        "ix_model_runs_organization_id_trained_at",
        "model_runs",
        ["organization_id", "trained_at"],
        unique=False,
    )
    op.create_index(
        "ix_customer_metrics_organization_id_churn_score",
        "customer_metrics",
        ["organization_id", "churn_score"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_customer_metrics_organization_id_churn_score", table_name="customer_metrics")
    op.drop_index("ix_model_runs_organization_id_trained_at", table_name="model_runs")
    op.drop_table("model_runs")
