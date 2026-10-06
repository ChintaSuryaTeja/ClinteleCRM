"""views and a read-only role for plain-English questions

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-06

Questions are answered by SQL an LLM writes. That SQL runs as the role
crm_ask, which can read the views in the "ask" schema and nothing else.

Each view shows only the rows of the organization named in the transaction
setting crm.organization_id (set by the API before running a query). If the
setting is missing, the views are empty.

The views belong to the app's own user, so they can read the real tables on
crm_ask's behalf; crm_ask itself has no rights on those tables.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENT_ORG = "current_setting('crm.organization_id', true)::bigint"


def upgrade() -> None:
    op.execute("CREATE SCHEMA ask")
    op.execute(
        f"""
        CREATE VIEW ask.customers AS
        SELECT c.id AS customer_id,
               c.external_id AS customer_ref,
               c.name,
               c.email,
               (m.first_order_at AT TIME ZONE 'UTC')::date AS first_order_date,
               (m.last_order_at AT TIME ZONE 'UTC')::date AS last_order_date,
               COALESCE(m.frequency, 0) AS orders,
               COALESCE(m.monetary, 0) AS total_spent,
               m.segment,
               m.r_score AS recency_score,
               m.f_score AS frequency_score,
               m.m_score AS monetary_score,
               m.lifetime_value,
               m.is_churned,
               m.churned_at AS churned_on,
               m.churn_score AS churn_risk
        FROM customers c
        LEFT JOIN customer_metrics m
          ON m.organization_id = c.organization_id AND m.customer_id = c.id
        WHERE c.organization_id = {CURRENT_ORG}
        """
    )
    op.execute(
        f"""
        CREATE VIEW ask.orders AS
        SELECT o.id AS order_id,
               o.external_id AS order_ref,
               o.customer_id,
               (o.ordered_at AT TIME ZONE 'UTC')::date AS order_date,
               o.ordered_at,
               o.total_amount AS total
        FROM orders o
        WHERE o.organization_id = {CURRENT_ORG}
        """
    )
    op.execute(
        f"""
        CREATE VIEW ask.order_items AS
        SELECT i.order_id,
               i.product_code,
               i.product_name,
               i.quantity,
               i.unit_price,
               i.quantity * i.unit_price AS line_total
        FROM order_items i
        WHERE i.organization_id = {CURRENT_ORG}
        """
    )
    op.execute(
        f"""
        CREATE VIEW ask.daily_revenue AS
        SELECT d.day, d.revenue, d.orders
        FROM daily_revenue d
        WHERE d.organization_id = {CURRENT_ORG}
        """
    )

    # Roles belong to the whole database server, so it may already exist
    # (for example from the test database).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'crm_ask') THEN
                CREATE ROLE crm_ask NOLOGIN;
            END IF;
        END
        $$
        """
    )
    op.execute("GRANT USAGE ON SCHEMA ask TO crm_ask")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA ask TO crm_ask")
    # Lets the app switch to crm_ask for one transaction with SET LOCAL ROLE.
    op.execute("GRANT crm_ask TO CURRENT_USER")

    # set_config() could switch a query back to the app's own role, or change
    # which organization the views show. The SQL checks never allow it, and here
    # the database refuses it too: only the app's own user may call it.
    # Changing a built-in function's permissions needs a superuser; where the
    # migration doesn't run as one (some managed databases), it says so and the
    # SQL checks remain the protection.
    op.execute(
        """
        DO $$
        BEGIN
            IF (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) THEN
                REVOKE EXECUTE ON FUNCTION pg_catalog.set_config(text, text, boolean) FROM PUBLIC;
                EXECUTE format(
                    'GRANT EXECUTE ON FUNCTION pg_catalog.set_config(text, text, boolean) TO %I',
                    current_user
                );
            ELSE
                RAISE WARNING 'Not a superuser: set_config() stays callable by crm_ask; '
                              'the SQL checks in app/ask_sql.py are the protection.';
            END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) THEN
                GRANT EXECUTE ON FUNCTION pg_catalog.set_config(text, text, boolean) TO PUBLIC;
            END IF;
        END
        $$
        """
    )
    # The role is kept: it may be used by other databases on the same server.
    op.execute("DROP SCHEMA ask CASCADE")
