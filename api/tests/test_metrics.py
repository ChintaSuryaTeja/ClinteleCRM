"""Metric calculations checked against hand-made customers with known answers.

The sample data is SAMPLE_ORDERS in helpers.py:
    Ada (C1): 5 Jan 2 x 10.00 = 20.00, 20 Jan 30.00 + 5.50 = 35.50  -> 2 orders, 55.50
    Ben (C2): 10 Feb 3 x 25.00 = 75.00                              -> 1 order,  75.00
    Cy  (C3): 1 Mar 9.99, 1 Mar 0.01                                -> 2 orders, 10.00
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import Customer, CustomerMetrics, DailyRevenue
from app.routers.dashboard import all_periods, pick_granularity
from tests.helpers import ORDER_COLUMNS, SAMPLE_ORDERS, signup, upload


@pytest.fixture
def acme(client):
    signup(client, "Acme", "admin@acme.com")
    upload(client, SAMPLE_ORDERS)
    return client


def test_daily_revenue_adds_up_orders_per_day(acme, db):
    rows = db.execute(select(DailyRevenue.day, DailyRevenue.revenue, DailyRevenue.orders)).all()

    assert sorted(rows) == [
        (date(2024, 1, 5), Decimal("20.00"), 1),
        (date(2024, 1, 20), Decimal("35.50"), 1),
        (date(2024, 2, 10), Decimal("75.00"), 1),
        (date(2024, 3, 1), Decimal("10.00"), 2),
    ]


def test_customer_totals(acme, client):
    customers = {c["external_id"]: c for c in client.get("/customers").json()["items"]}

    assert customers["C1"]["orders"] == 2
    assert customers["C1"]["total_spent"] == 55.50
    assert customers["C1"]["first_order_at"].startswith("2024-01-05")
    assert customers["C1"]["last_order_at"].startswith("2024-01-20")
    assert customers["C2"]["orders"] == 1
    assert customers["C2"]["total_spent"] == 75.00
    assert customers["C3"]["orders"] == 2
    assert customers["C3"]["total_spent"] == 10.00


def test_dashboard_for_all_time(acme, client):
    data = client.get("/dashboard").json()

    assert data["data_start"] == "2024-01-05"
    assert data["data_end"] == "2024-03-01"
    assert data["revenue"] == 140.50
    assert data["orders"] == 5
    assert data["average_order_value"] == 28.10  # 140.50 / 5
    assert data["customers"] == 3


def test_dashboard_for_january_only(acme, client):
    data = client.get("/dashboard", params={"start": "2024-01-01", "end": "2024-01-31"}).json()

    assert data["revenue"] == 55.50
    assert data["orders"] == 2
    assert data["average_order_value"] == 27.75
    assert data["customers"] == 1
    assert [c["external_id"] for c in data["top_customers"]] == ["C1"]


def test_date_range_includes_both_end_days(acme, client):
    data = client.get("/dashboard", params={"start": "2024-01-20", "end": "2024-02-10"}).json()

    assert data["revenue"] == 35.50 + 75.00
    assert data["orders"] == 2


def test_top_customers_are_ranked_by_revenue_in_range(acme, client):
    data = client.get("/dashboard", params={"start": "2024-02-01", "end": "2024-03-31"}).json()

    top = [(c["external_id"], c["revenue"], c["orders"]) for c in data["top_customers"]]
    assert top == [("C2", 75.00, 1), ("C3", 10.00, 2)]


def test_monthly_series_fills_months_without_orders_with_zero(acme, client):
    data = client.get("/dashboard", params={"start": "2024-01-01", "end": "2025-01-31"}).json()

    assert data["granularity"] == "month"
    series = [(p["period"], p["revenue"], p["orders"]) for p in data["series"]]
    assert len(series) == 13
    assert series[:4] == [
        ("2024-01-01", 55.50, 2),
        ("2024-02-01", 75.00, 1),
        ("2024-03-01", 10.00, 2),
        ("2024-04-01", 0.0, 0),
    ]
    assert data["series"][0]["average_order_value"] == 27.75
    assert data["series"][3]["average_order_value"] is None


def test_weekly_series_groups_from_monday(acme, client):
    data = client.get("/dashboard", params={"start": "2024-01-01", "end": "2024-03-31"}).json()

    assert data["granularity"] == "week"
    weeks = {p["period"]: p["revenue"] for p in data["series"]}
    assert weeks["2024-01-01"] == 20.00  # Fri 5 Jan is in the week starting Mon 1 Jan
    assert weeks["2024-01-15"] == 35.50  # Sat 20 Jan
    assert weeks["2024-02-05"] == 75.00  # Sat 10 Feb
    assert weeks["2024-02-26"] == 10.00  # Fri 1 Mar


def test_dashboard_rejects_reversed_range(acme, client):
    response = client.get("/dashboard", params={"start": "2024-03-01", "end": "2024-01-01"})
    assert response.status_code == 422


def test_dashboard_before_any_import(client):
    signup(client, "Empty Co", "admin@empty.com")

    data = client.get("/dashboard").json()

    assert data["data_start"] is None
    assert data["revenue"] == 0
    assert data["series"] == []
    assert data["currency"] == "USD"


def test_orders_are_counted_on_their_utc_day(client, db):
    signup(client, "Acme", "admin@acme.com")
    # 23:30 in New York on 31 January is 04:30 UTC on 1 February.
    upload(client, f"{ORDER_COLUMNS}\nO1,2024-01-31T23:30:00-05:00,C1,Ada,P,1,10\n")

    assert db.scalar(select(DailyRevenue.day)) == date(2024, 2, 1)


def test_metrics_are_rebuilt_after_a_second_import(acme, client, db):
    upload(client, f"{ORDER_COLUMNS}\nO6,2024-04-02,C1,Ada,P-RED,1,44.50\n")

    ada = db.scalar(
        select(CustomerMetrics)
        .join(Customer, Customer.id == CustomerMetrics.customer_id)
        .where(Customer.external_id == "C1")
    )
    assert ada.frequency == 3
    assert ada.monetary == Decimal("100.00")  # 55.50 + 44.50
    assert client.get("/dashboard").json()["revenue"] == 185.00


def test_granularity_thresholds():
    assert pick_granularity(date(2024, 1, 1), date(2024, 3, 2)) == "day"  # 62 days
    assert pick_granularity(date(2024, 1, 1), date(2024, 3, 3)) == "week"  # 63 days
    assert pick_granularity(date(2024, 1, 1), date(2024, 12, 31)) == "week"  # 366 days
    assert pick_granularity(date(2024, 1, 1), date(2025, 1, 1)) == "month"


def test_all_periods_covers_partial_first_month():
    periods = all_periods(date(2024, 1, 15), date(2024, 3, 2), "month")
    assert periods == [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1)]
