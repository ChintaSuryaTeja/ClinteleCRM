"""Churn history, lifetime value and cohort retention on hand-made customers.

As of 31 Dec 2024 (Z's order is the latest). A churn event is the 90th day
without an order.

    A: 10 Jan, 1 May, 15 Jun   gaps of 112 and 45 days, then 199 days of silence
       -> churned 9 Apr (10 Jan + 90), came back 1 May, churned again 13 Sep
    B: 1 Mar, 30 May, 1 Dec    gap of exactly 90 days (not churn), then 185 days
       -> churned 28 Aug, came back 1 Dec, active today
    Z: 31 Dec                  just arrived

Customers active when each month began (last order less than 90 days before)
and churn events in that month:

    Jan 0/0  Feb 1/0  Mar 1/0  Apr 2/1  May 1/0  Jun 2/0
    Jul 2/0  Aug 2/1  Sep 1/1  Oct 0/0  Nov 0/0  Dec 0/0

Months count as complete once 90 days of history come before them (from
May, as the data starts 10 Jan). Over May to Dec: 2 churned / 8 active
customer-months = 25% a month, so a typical customer stays 1 / 0.25 = 4 months.
"""

import pytest
from sqlalchemy import select

from app.models import MonthlyChurn
from tests.helpers import orders_csv, signup, upload

HISTORY = orders_csv(
    [
        ("A1", "2024-01-10", "A", "10"),
        ("A2", "2024-05-01", "A", "20"),
        ("A3", "2024-06-15", "A", "30"),
        ("B1", "2024-03-01", "B", "10"),
        ("B2", "2024-05-30", "B", "10"),
        ("B3", "2024-12-01", "B", "10"),
        ("Z1", "2024-12-31", "Z", "40"),
    ]
)


@pytest.fixture
def history(client):
    signup(client, "Acme", "admin@acme.com")
    upload(client, HISTORY)
    return client


def customers(client) -> dict:
    return {c["external_id"]: c for c in client.get("/customers").json()["items"]}


def test_monthly_active_and_churned_counts(history, db):
    rows = db.execute(
        select(
            MonthlyChurn.month, MonthlyChurn.active_customers, MonthlyChurn.churned_customers
        ).order_by(MonthlyChurn.month)
    ).all()

    assert [(month.month, active, churned) for month, active, churned in rows] == [
        (1, 0, 0),
        (2, 1, 0),
        (3, 1, 0),
        (4, 2, 1),
        (5, 1, 0),
        (6, 2, 0),
        (7, 2, 0),
        (8, 2, 1),
        (9, 1, 1),
        (10, 0, 0),
        (11, 0, 0),
        (12, 0, 0),
    ]


def test_churn_endpoint_shows_complete_months_and_the_rate(history):
    data = history.get("/churn").json()

    assert data["as_of"] == "2024-12-31"
    assert data["monthly_churn_rate"] == 0.25
    assert data["expected_lifetime_months"] == 4
    assert (data["churned_customers"], data["active_customers"]) == (1, 2)  # A; B and Z
    assert [(m["month"], m["rate"]) for m in data["months"]] == [
        ("2024-05-01", 0.0),
        ("2024-06-01", 0.0),
        ("2024-07-01", 0.0),
        ("2024-08-01", 0.5),
        ("2024-09-01", 1.0),
        ("2024-10-01", None),  # nobody was active, so there is no rate
        ("2024-11-01", None),
        ("2024-12-01", None),
    ]


def test_current_churn_status(history):
    people = customers(history)
    assert (people["A"]["is_churned"], people["A"]["churned_at"]) == (True, "2024-09-13")
    assert (people["B"]["is_churned"], people["B"]["churned_at"]) == (False, None)
    assert people["Z"]["is_churned"] is False


def test_lifetime_value_is_monthly_spend_times_expected_lifetime(history):
    people = customers(history)

    # A spent 60 over the 356 days from 10 Jan to 31 Dec.
    assert people["A"]["lifetime_value"] == round(60 / (356 / 30.4375) * 4, 2)  # 20.52
    # B spent 30 over the 305 days from 1 Mar to 31 Dec.
    assert people["B"]["lifetime_value"] == round(30 / (305 / 30.4375) * 4, 2)  # 11.98
    # Z's first order is today: counted as one month, 40 x 4 months.
    assert people["Z"]["lifetime_value"] == 160.00


def test_lifetime_is_capped_at_36_months_when_nobody_churns(client):
    signup(client, "Acme", "admin@acme.com")
    upload(client, orders_csv([("1", "2024-01-01", "A", "10"), ("2", "2024-01-15", "A", "10")]))

    data = client.get("/churn").json()

    assert data["monthly_churn_rate"] is None  # less than 90 days of history
    assert data["expected_lifetime_months"] == 36
    assert customers(client)["A"]["lifetime_value"] == 20 * 36  # 20 in its first month


def test_cohort_retention(history):
    data = history.get("/retention").json()

    assert data["as_of"] == "2024-12-31"
    cohorts = {c["cohort_month"]: c for c in data["cohorts"]}
    assert list(cohorts) == ["2024-01-01", "2024-03-01", "2024-12-01"]

    # A (January cohort) ordered in Jan, May and Jun: months 0, 4 and 5.
    january = cohorts["2024-01-01"]
    assert january["size"] == 1
    assert january["customers"] == [1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0]
    assert january["rates"][4] == 1.0

    # B (March cohort) ordered in Mar, May and Dec: months 0, 2 and 9.
    assert cohorts["2024-03-01"]["customers"] == [1, 0, 1, 0, 0, 0, 0, 0, 0, 1]
    # Z (December cohort) has only its first month so far.
    assert cohorts["2024-12-01"]["customers"] == [1]


def test_retention_rate_is_share_of_the_cohort(client):
    signup(client, "Acme", "admin@acme.com")
    upload(
        client,
        orders_csv(
            [
                ("1", "2024-01-05", "A", "10"),
                ("2", "2024-01-06", "B", "10"),
                ("3", "2024-01-07", "C", "10"),
                ("4", "2024-01-08", "D", "10"),
                ("5", "2024-02-10", "A", "10"),  # 1 of 4 back in month 1
                ("6", "2024-03-10", "A", "10"),  # 2 of 4 back in month 2
                ("7", "2024-03-11", "B", "10"),
            ]
        ),
    )

    january = client.get("/retention").json()["cohorts"][0]

    assert january["rates"] == [1.0, 0.25, 0.5]


def test_empty_organization_has_no_analytics(client):
    signup(client, "Empty", "admin@empty.com")

    assert client.get("/churn").json()["months"] == []
    assert client.get("/retention").json()["cohorts"] == []
    segments = client.get("/segments").json()
    assert segments["customers"] == 0
    assert all(row["customers"] == 0 for row in segments["segments"])


def test_deleting_all_orders_clears_the_analytics(history):
    job_id = history.get("/imports").json()[0]["id"]

    history.delete(f"/imports/{job_id}")

    assert history.get("/churn").json()["as_of"] is None
    assert history.get("/retention").json()["cohorts"] == []
