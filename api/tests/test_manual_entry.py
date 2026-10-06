from tests.helpers import SAMPLE_ORDERS, add_user, login, signup, upload


def order(**changes) -> dict:
    """A valid hand-entered order: 2 x 12.50 + 1 x 6.00 = 31.00."""
    body = {
        "order_id": "1001",
        "order_date": "2024-03-01",
        "customer_id": "C-001",
        "customer_name": "Ada Lovelace",
        "customer_email": "ada@example.com",
        "lines": [
            {
                "product_code": "MUG-01",
                "product_name": "Mug",
                "quantity": "2",
                "unit_price": "12.50",
            },
            {"product_code": "TEA-03", "quantity": "1", "unit_price": "6"},
        ],
    }
    body.update(changes)
    return body


def test_order_entered_by_hand_is_imported(client):
    signup(client, "Acme", "admin@acme.com")

    response = client.post("/imports/manual", json=order())

    assert response.status_code == 202
    job = response.json()
    assert job["filename"] == "manual-entry-order-1001.csv"
    assert (job["status"], job["rows_imported"]) == ("succeeded", 2)
    dashboard = client.get("/dashboard").json()
    assert (dashboard["revenue"], dashboard["orders"]) == (31.00, 1)
    customer = client.get("/customers").json()["items"][0]
    assert (customer["name"], customer["email"]) == ("Ada Lovelace", "ada@example.com")


def test_mistakes_are_reported_on_the_form_and_nothing_is_saved(client):
    signup(client, "Acme", "admin@acme.com")
    lines = [
        {"product_code": "MUG-01", "quantity": "0", "unit_price": "12.50"},
        {"product_code": "", "quantity": "1", "unit_price": "abc"},
    ]

    response = client.post("/imports/manual", json=order(order_date="31/12/2024", lines=lines))

    assert response.status_code == 422
    # The date problem is reported once, not once per product.
    assert response.json()["detail"] == (
        """Order date "31/12/2024" isn't a date like 2024-03-31 or 2024-03-31 14:05. """
        """Product 1: Quantity "0" must be a positive whole number. """
        """Product 2: Product code is empty. """
        """Product 2: Unit price "abc" isn't a number."""
    )
    assert client.get("/imports").json() == []


def test_existing_order_id_is_refused(client):
    signup(client, "Acme", "admin@acme.com")
    upload(client, SAMPLE_ORDERS)

    response = client.post("/imports/manual", json=order(order_id="O1"))

    assert response.status_code == 409
    assert response.json()["detail"] == "Order O1 already exists."


def test_order_entered_by_hand_can_be_deleted(client):
    signup(client, "Acme", "admin@acme.com")
    job = client.post("/imports/manual", json=order()).json()

    client.delete(f"/imports/{job['id']}")

    assert client.get("/dashboard").json()["revenue"] == 0
    assert client.get("/customers").json()["total"] == 0


def test_order_needs_at_least_one_product(client):
    signup(client, "Acme", "admin@acme.com")
    assert client.post("/imports/manual", json=order(lines=[])).status_code == 422


def test_viewer_cannot_add_orders(make_client):
    admin = make_client()
    signup(admin, "Acme", "admin@acme.com")
    add_user(admin, "viewer@acme.com", "viewer")
    viewer = make_client()
    login(viewer, "viewer@acme.com")

    assert viewer.post("/imports/manual", json=order()).status_code == 403


def test_order_goes_to_the_admins_own_organization(make_client):
    acme = make_client()
    signup(acme, "Acme", "admin@acme.com")
    globex = make_client()
    signup(globex, "Globex", "admin@globex.com")

    acme.post("/imports/manual", json=order())

    assert acme.get("/dashboard").json()["orders"] == 1
    assert globex.get("/dashboard").json()["orders"] == 0
