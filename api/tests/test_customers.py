import pytest

from tests.helpers import ORDER_COLUMNS, SAMPLE_ORDERS, signup, upload


@pytest.fixture
def acme(client):
    signup(client, "Acme", "admin@acme.com")
    upload(client, SAMPLE_ORDERS)
    return client


def ids(response) -> list[str]:
    return [customer["external_id"] for customer in response.json()["items"]]


def test_default_order_is_highest_spend_first(acme):
    assert ids(acme.get("/customers")) == ["C2", "C1", "C3"]  # 75.00, 55.50, 10.00


def test_sort_by_name(acme):
    response = acme.get("/customers", params={"sort": "name", "direction": "asc"})
    assert ids(response) == ["C1", "C2", "C3"]  # Ada, Ben, Cy


def test_search_matches_name_and_customer_id_ignoring_case(acme):
    assert ids(acme.get("/customers", params={"search": "ben"})) == ["C2"]
    assert ids(acme.get("/customers", params={"search": "c3"})) == ["C3"]


def test_search_treats_percent_as_a_normal_character(acme):
    assert acme.get("/customers", params={"search": "%"}).json()["total"] == 0


def test_filter_by_number_of_orders(acme):
    assert ids(acme.get("/customers", params={"min_orders": 2})) == ["C1", "C3"]
    assert ids(acme.get("/customers", params={"max_orders": 1})) == ["C2"]


def test_filter_by_amount_spent(acme):
    response = acme.get("/customers", params={"min_spent": 10, "max_spent": 55.50})
    assert ids(response) == ["C1", "C3"]  # both ends included


def test_filter_by_last_order_date_includes_both_end_days(acme):
    response = acme.get(
        "/customers", params={"last_order_from": "2024-01-20", "last_order_to": "2024-02-10"}
    )
    assert ids(response) == ["C2", "C1"]


def test_pagination(acme):
    page = acme.get("/customers", params={"page": 2, "page_size": 2}).json()
    assert page["total"] == 3
    assert [c["external_id"] for c in page["items"]] == ["C3"]


def test_export_uses_the_same_filters_and_includes_every_page(acme):
    response = acme.get("/customers/export.csv", params={"min_orders": 2, "page_size": 1})

    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    lines = response.text.splitlines()
    assert lines[0] == (
        "customer_id,name,email,orders,total_spent,first_order_date,last_order_date"
    )
    assert lines[1:] == [
        "C1,Ada,,2,55.50,2024-01-05,2024-01-20",
        "C3,Cy,,2,10.00,2024-03-01,2024-03-01",
    ]


def test_export_neutralises_spreadsheet_formulas(client):
    signup(client, "Acme", "admin@acme.com")
    upload(client, f'{ORDER_COLUMNS}\nO1,2024-01-05,C1,"=HYPERLINK(""x"")",P1,1,10\n')

    lines = client.get("/customers/export.csv").text.splitlines()

    assert lines[1].startswith("C1,\"'=HYPERLINK(")


def test_customer_detail(acme):
    ada_id = next(c["id"] for c in acme.get("/customers").json()["items"] if c["name"] == "Ada")

    ada = acme.get(f"/customers/{ada_id}").json()

    assert ada["orders"] == 2
    assert ada["total_spent"] == 55.50
    assert ada["average_order_value"] == 27.75
    assert [(o["external_id"], o["total_amount"], o["items"]) for o in ada["recent_orders"]] == [
        ("O2", 35.50, 2),  # newest first; 2 units across two lines
        ("O1", 20.00, 2),  # 2 units of one product
    ]


def test_unknown_customer_is_404(acme):
    assert acme.get("/customers/999999").status_code == 404


def test_customer_list_requires_login(client):
    assert client.get("/customers").status_code == 401
    assert client.get("/customers/export.csv").status_code == 401
