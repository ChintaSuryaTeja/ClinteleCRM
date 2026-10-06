from sqlalchemy import func, select

from app.models import Customer, CustomerMetrics, ImportJob, ImportStatus, Order, OrderItem
from tests.helpers import ORDER_COLUMNS, SAMPLE_ORDERS, add_user, login, signup, upload

# A second file: a new order for Ada (also in SAMPLE_ORDERS) and a new customer, Dee.
SECOND_FILE = f"""{ORDER_COLUMNS}
O10,2024-04-02,C1,Ada,P-RED,1,44.50
O11,2024-04-03,C4,Dee,P-CAP,2,5.00
"""


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_deleting_an_import_removes_its_orders_and_restores_the_numbers(client, db):
    signup(client, "Acme", "admin@acme.com")
    upload(client, SAMPLE_ORDERS)
    second = upload(client, SECOND_FILE)
    assert client.get("/dashboard").json()["revenue"] == 140.50 + 44.50 + 10.00

    response = client.delete(f"/imports/{second['id']}")

    assert response.status_code == 202
    assert client.get("/dashboard").json()["revenue"] == 140.50
    assert count(db, Order) == 5
    assert count(db, OrderItem) == 6
    assert [job["filename"] for job in client.get("/imports").json()] == ["orders.csv"]


def test_customers_with_no_orders_left_are_removed(client, db):
    signup(client, "Acme", "admin@acme.com")
    upload(client, SAMPLE_ORDERS)
    second = upload(client, SECOND_FILE)

    client.delete(f"/imports/{second['id']}")

    external_ids = set(db.scalars(select(Customer.external_id)))
    assert external_ids == {"C1", "C2", "C3"}  # Dee (C4) only had orders in the deleted file
    assert count(db, CustomerMetrics) == 3


def test_customer_in_both_imports_keeps_recalculated_totals(client):
    signup(client, "Acme", "admin@acme.com")
    upload(client, SAMPLE_ORDERS)
    second = upload(client, SECOND_FILE)

    client.delete(f"/imports/{second['id']}")

    ada = next(c for c in client.get("/customers").json()["items"] if c["external_id"] == "C1")
    assert (ada["orders"], ada["total_spent"]) == (2, 55.50)


def test_after_deleting_the_same_file_imports_again(client):
    signup(client, "Acme", "admin@acme.com")
    first = upload(client, SAMPLE_ORDERS)
    client.delete(f"/imports/{first['id']}")

    again = upload(client, SAMPLE_ORDERS)

    assert (again["rows_imported"], again["rows_skipped"]) == (6, 0)


def test_failed_import_is_removed_straight_away(client):
    signup(client, "Acme", "admin@acme.com")
    failed = upload(client, "not,the,right,columns\n1,2,3,4\n")

    response = client.delete(f"/imports/{failed['id']}")

    assert response.status_code == 204
    assert client.get("/imports").json() == []


def test_cannot_delete_an_import_that_is_still_running(client, db):
    signup(client, "Acme", "admin@acme.com")
    job = upload(client, SAMPLE_ORDERS)
    db.get(ImportJob, job["id"]).status = ImportStatus.RUNNING
    db.flush()

    response = client.delete(f"/imports/{job['id']}")

    assert response.status_code == 409
    assert client.get("/dashboard").json()["revenue"] == 140.50


def test_viewer_cannot_delete_imports(make_client):
    admin = make_client()
    signup(admin, "Acme", "admin@acme.com")
    job = upload(admin, SAMPLE_ORDERS)
    add_user(admin, "viewer@acme.com", "viewer")
    viewer = make_client()
    login(viewer, "viewer@acme.com")

    assert viewer.delete(f"/imports/{job['id']}").status_code == 403
    assert admin.get("/dashboard").json()["revenue"] == 140.50


def test_cannot_delete_another_organizations_import(make_client):
    acme = make_client()
    signup(acme, "Acme", "admin@acme.com")
    job = upload(acme, SAMPLE_ORDERS)
    globex = make_client()
    signup(globex, "Globex", "admin@globex.com")

    assert globex.delete(f"/imports/{job['id']}").status_code == 404
    assert acme.get("/dashboard").json()["revenue"] == 140.50
