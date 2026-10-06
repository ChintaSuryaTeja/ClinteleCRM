"""link orders to imports

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-06

Each order now records the import that created it, so deleting an import can
remove its orders. Import jobs gain a "deleting" status while that happens.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        op.f("uq_import_jobs_organization_id_id"), "import_jobs", ["organization_id", "id"]
    )
    op.add_column("orders", sa.Column("import_job_id", sa.BigInteger(), nullable=True))
    op.create_index(
        "ix_orders_organization_id_import_job_id",
        "orders",
        ["organization_id", "import_job_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_orders_organization_id_import_job_id_import_jobs"),
        "orders",
        "import_jobs",
        ["organization_id", "import_job_id"],
        ["organization_id", "id"],
    )

    # Link orders imported before this migration to their import. An import
    # saves its orders in one transaction that starts after the job's
    # started_at and ends before its finished_at, and an order's created_at is
    # that transaction's start time, so it falls inside the job's window.
    op.execute(
        """
        UPDATE orders
        SET import_job_id = import_jobs.id
        FROM import_jobs
        WHERE orders.organization_id = import_jobs.organization_id
          AND import_jobs.status = 'succeeded'
          AND orders.created_at BETWEEN import_jobs.started_at AND import_jobs.finished_at
        """
    )

    op.drop_constraint(op.f("ck_import_jobs_status"), "import_jobs", type_="check")
    op.create_check_constraint(
        op.f("ck_import_jobs_status"),
        "import_jobs",
        "status IN ('queued', 'running', 'succeeded', 'failed', 'deleting')",
    )


def downgrade() -> None:
    op.execute("UPDATE import_jobs SET status = 'succeeded' WHERE status = 'deleting'")
    op.drop_constraint(op.f("ck_import_jobs_status"), "import_jobs", type_="check")
    op.create_check_constraint(
        op.f("ck_import_jobs_status"),
        "import_jobs",
        "status IN ('queued', 'running', 'succeeded', 'failed')",
    )
    op.drop_constraint(
        op.f("fk_orders_organization_id_import_job_id_import_jobs"), "orders", type_="foreignkey"
    )
    op.drop_index("ix_orders_organization_id_import_job_id", table_name="orders")
    op.drop_column("orders", "import_job_id")
    op.drop_constraint(op.f("uq_import_jobs_organization_id_id"), "import_jobs", type_="unique")
