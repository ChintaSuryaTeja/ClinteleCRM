"""A user from one organization must never read or change another organization's data."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Customer, Order, Organization
from tests.helpers import PASSWORD, SAMPLE_ORDERS, add_user, signup, upload


def test_admin_only_sees_users_from_own_organization(make_client):
    acme = make_client()
    signup(acme, "Acme", "admin@acme.com")
    add_user(acme, "viewer@acme.com", "viewer")
    globex = make_client()
    signup(globex, "Globex", "admin@globex.com")
    add_user(globex, "viewer@globex.com", "viewer")

    acme_emails = {user["email"] for user in acme.get("/users").json()}
    globex_emails = {user["email"] for user in globex.get("/users").json()}

    assert acme_emails == {"admin@acme.com", "viewer@acme.com"}
    assert globex_emails == {"admin@globex.com", "viewer@globex.com"}


def test_admin_cannot_add_user_to_another_organization(make_client):
    acme = make_client()
    signup(acme, "Acme", "admin@acme.com")
    globex = make_client()
    globex_org_id = signup(globex, "Globex", "admin@globex.com")["organization"]["id"]

    # An organization_id in the request body is ignored. The new user always
    # joins the organization of the admin who made the request.
    acme.post(
        "/users",
        json={
            "email": "spy@acme.com",
            "password": PASSWORD,
            "role": "viewer",
            "organization_id": globex_org_id,
        },
    )

    globex_emails = {user["email"] for user in globex.get("/users").json()}
    acme_emails = {user["email"] for user in acme.get("/users").json()}
    assert "spy@acme.com" not in globex_emails
    assert "spy@acme.com" in acme_emails


def _order(organization_id: int, customer_id: int) -> Order:
    return Order(
        organization_id=organization_id,
        customer_id=customer_id,
        external_id="INV-1",
        ordered_at=datetime(2026, 1, 15, tzinfo=UTC),
        total_amount=Decimal("49.90"),
    )


def test_database_accepts_order_for_own_customer(db):
    acme = Organization(name="Acme")
    db.add(acme)
    db.flush()
    customer = Customer(organization_id=acme.id, external_id="C-1")
    db.add(customer)
    db.flush()

    db.add(_order(acme.id, customer.id))
    db.flush()  # no error


def test_database_rejects_order_pointing_at_another_organizations_customer(db):
    acme = Organization(name="Acme")
    globex = Organization(name="Globex")
    db.add_all([acme, globex])
    db.flush()
    acme_customer = Customer(organization_id=acme.id, external_id="C-1")
    db.add(acme_customer)
    db.flush()

    db.add(_order(globex.id, acme_customer.id))

    with pytest.raises(IntegrityError):
        db.flush()


# --- Imported data ------------------------------------------------------------


def _two_organizations(make_client):
    """Acme has imported the sample orders; Globex has imported nothing."""
    acme = make_client()
    signup(acme, "Acme", "admin@acme.com")
    job = upload(acme, SAMPLE_ORDERS)
    globex = make_client()
    signup(globex, "Globex", "admin@globex.com")
    return acme, globex, job


def test_dashboard_only_counts_own_orders(make_client):
    acme, globex, _ = _two_organizations(make_client)

    assert acme.get("/dashboard").json()["revenue"] == 140.50
    globex_dashboard = globex.get("/dashboard").json()
    assert globex_dashboard["revenue"] == 0
    assert globex_dashboard["top_customers"] == []


def test_customer_list_and_export_only_show_own_customers(make_client):
    _, globex, _ = _two_organizations(make_client)

    assert globex.get("/customers").json()["total"] == 0
    assert len(globex.get("/customers/export.csv").text.splitlines()) == 1  # header only


def test_cannot_open_another_organizations_customer(make_client):
    acme, globex, _ = _two_organizations(make_client)
    acme_customer_id = acme.get("/customers").json()["items"][0]["id"]

    assert globex.get(f"/customers/{acme_customer_id}").status_code == 404


def test_cannot_see_another_organizations_imports(make_client):
    _, globex, job = _two_organizations(make_client)

    assert globex.get("/imports").json() == []
    assert globex.get(f"/imports/{job['id']}").status_code == 404
    assert globex.get(f"/imports/{job['id']}/errors.csv").status_code == 404


def test_same_order_ids_in_two_organizations_are_separate(make_client):
    acme, globex, _ = _two_organizations(make_client)

    job = upload(globex, SAMPLE_ORDERS)  # same order_ids and customer_ids as Acme's

    assert (job["rows_imported"], job["rows_skipped"]) == (6, 0)
    assert globex.get("/dashboard").json()["revenue"] == 140.50
    assert acme.get("/dashboard").json()["revenue"] == 140.50
