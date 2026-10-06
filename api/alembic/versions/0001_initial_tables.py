"""initial tables

Revision ID: 0001
Revises:
Create Date: 2026-10-06 05:48:08.478292
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_table(
        "customers",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_customers_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customers")),
        sa.UniqueConstraint(
            "organization_id", "external_id", name=op.f("uq_customers_organization_id_external_id")
        ),
        sa.UniqueConstraint("organization_id", "id", name=op.f("uq_customers_organization_id_id")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('admin', 'viewer')", name=op.f("ck_users_role")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_users_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("organization_id", "id", name=op.f("uq_users_organization_id_id")),
    )
    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)
    op.create_table(
        "customer_metrics",
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("recency_days", sa.Integer(), nullable=True),
        sa.Column("frequency", sa.Integer(), nullable=True),
        sa.Column("monetary", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("r_score", sa.SmallInteger(), nullable=True),
        sa.Column("f_score", sa.SmallInteger(), nullable=True),
        sa.Column("m_score", sa.SmallInteger(), nullable=True),
        sa.Column("segment", sa.String(length=40), nullable=True),
        sa.Column("lifetime_value", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("is_churned", sa.Boolean(), nullable=True),
        sa.Column("churned_at", sa.Date(), nullable=True),
        sa.Column("churn_score", sa.Float(), nullable=True),
        sa.Column("churn_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "churn_score BETWEEN 0 AND 1", name=op.f("ck_customer_metrics_churn_score")
        ),
        sa.CheckConstraint("f_score BETWEEN 1 AND 5", name=op.f("ck_customer_metrics_f_score")),
        sa.CheckConstraint("m_score BETWEEN 1 AND 5", name=op.f("ck_customer_metrics_m_score")),
        sa.CheckConstraint("r_score BETWEEN 1 AND 5", name=op.f("ck_customer_metrics_r_score")),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name=op.f("fk_customer_metrics_organization_id_customer_id_customers"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_customer_metrics_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("customer_id", name=op.f("pk_customer_metrics")),
    )
    op.create_index(
        "ix_customer_metrics_organization_id_segment",
        "customer_metrics",
        ["organization_id", "segment"],
        unique=False,
    )
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="queued", nullable=False),
        sa.Column("rows_imported", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_rejected", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name=op.f("ck_import_jobs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name=op.f("fk_import_jobs_organization_id_created_by_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_import_jobs_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_jobs")),
    )
    op.create_index(
        "ix_import_jobs_organization_id_created_at",
        "import_jobs",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name=op.f("fk_orders_organization_id_customer_id_customers"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_orders_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint(
            "organization_id", "external_id", name=op.f("uq_orders_organization_id_external_id")
        ),
        sa.UniqueConstraint("organization_id", "id", name=op.f("uq_orders_organization_id_id")),
    )
    op.create_index(
        "ix_orders_organization_id_customer_id",
        "orders",
        ["organization_id", "customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_orders_organization_id_ordered_at",
        "orders",
        ["organization_id", "ordered_at"],
        unique=False,
    )
    op.create_table(
        "order_items",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("product_code", sa.String(length=64), nullable=False),
        sa.Column("product_name", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id", "order_id"],
            ["orders.organization_id", "orders.id"],
            name=op.f("fk_order_items_organization_id_order_id_orders"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_order_items_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
    )
    op.create_index(
        "ix_order_items_organization_id_order_id",
        "order_items",
        ["organization_id", "order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_order_items_organization_id_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_organization_id_ordered_at", table_name="orders")
    op.drop_index("ix_orders_organization_id_customer_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_import_jobs_organization_id_created_at", table_name="import_jobs")
    op.drop_table("import_jobs")
    op.drop_index("ix_customer_metrics_organization_id_segment", table_name="customer_metrics")
    op.drop_table("customer_metrics")
    op.drop_index(op.f("ix_users_organization_id"), table_name="users")
    op.drop_table("users")
    op.drop_table("customers")
    op.drop_table("organizations")
