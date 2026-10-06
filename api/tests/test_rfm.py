"""RFM scores and segments, checked against hand-made customers.

Five customers, as of 30 Jun 2024 (the latest order):

    customer  orders  spent  last order   days since  R  F  M  segment
    C1        5       1000   30 Jun          0        5  5  5  Champions
    C2        4        800   20 Jun         10        4  4  4  Champions
    C3        3        300   31 May         30        3  3  3  Need attention
    C4        2        200    2 Mar        120        2  2  2  Lost  (churned 31 May)
    C5        1         50    1 Jan        181        1  1  1  Lost  (churned 31 Mar)

With five different values, percent ranks are 0, .25, .5, .75 and 1, so
scores are 1 + floor(5 x rank) = 1, 2, 3, 4 and 5 (capped at 5).
"""

import itertools

import pytest

from app.segments import RULES, SEGMENTS, segment_for
from tests.helpers import orders_csv, signup, upload

FIVE_CUSTOMERS = orders_csv(
    [
        ("A1", "2024-02-01", "C1", "200"),
        ("A2", "2024-03-01", "C1", "200"),
        ("A3", "2024-04-01", "C1", "200"),
        ("A4", "2024-05-01", "C1", "200"),
        ("A5", "2024-06-30", "C1", "200"),
        ("B1", "2024-03-10", "C2", "200"),
        ("B2", "2024-04-10", "C2", "200"),
        ("B3", "2024-05-10", "C2", "200"),
        ("B4", "2024-06-20", "C2", "200"),
        ("C1", "2024-04-01", "C3", "100"),
        ("C2", "2024-05-01", "C3", "100"),
        ("C3", "2024-05-31", "C3", "100"),
        ("D1", "2024-01-15", "C4", "100"),
        ("D2", "2024-03-02", "C4", "100"),
        ("E1", "2024-01-01", "C5", "50"),
    ]
)


@pytest.fixture
def five(client):
    signup(client, "Acme", "admin@acme.com")
    upload(client, FIVE_CUSTOMERS)
    return {c["external_id"]: c for c in client.get("/customers").json()["items"]}


def test_scores(five):
    scores = {cid: (c["r_score"], c["f_score"], c["m_score"]) for cid, c in five.items()}
    assert scores == {
        "C1": (5, 5, 5),
        "C2": (4, 4, 4),
        "C3": (3, 3, 3),
        "C4": (2, 2, 2),
        "C5": (1, 1, 1),
    }


def test_segments(five):
    segments = {cid: c["segment"] for cid, c in five.items()}
    assert segments == {
        "C1": "Champions",
        "C2": "Champions",
        "C3": "Need attention",
        "C4": "Lost",
        "C5": "Lost",
    }


def test_churn_status_is_90_days_without_an_order(five):
    status = {cid: (c["is_churned"], c["churned_at"]) for cid, c in five.items()}
    assert status == {
        "C1": (False, None),
        "C2": (False, None),
        "C3": (False, None),  # 30 days
        "C4": (True, "2024-05-31"),  # 2 Mar + 90 days
        "C5": (True, "2024-03-31"),  # 1 Jan + 90 days (2024 is a leap year)
    }


def test_customers_with_equal_values_get_equal_scores(client):
    signup(client, "Acme", "admin@acme.com")
    upload(
        client,
        orders_csv(
            [
                ("1", "2024-01-01", "T1", "10"),
                ("2", "2024-01-01", "T2", "10"),
                ("3", "2024-01-01", "T3", "10"),
                ("4", "2024-01-02", "T3", "10"),
            ]
        ),
    )
    customers = {c["external_id"]: c for c in client.get("/customers").json()["items"]}

    # T1 and T2 both ordered once for 10: same F and M, both the lowest.
    assert customers["T1"]["f_score"] == customers["T2"]["f_score"] == 1
    assert customers["T1"]["m_score"] == customers["T2"]["m_score"] == 1
    assert customers["T3"]["f_score"] == 5


def test_every_score_combination_has_exactly_one_segment():
    for r, f, m in itertools.product(range(1, 6), repeat=3):
        fm = (f + m + 1) // 2
        matches = [
            name
            for name, r_low, r_high, fm_low, fm_high in RULES
            if r_low <= r <= r_high and fm_low <= fm <= fm_high
        ]
        assert len(matches) == 1, (r, f, m, matches)
        assert segment_for(r, f, m) == matches[0]
    assert {name for name, *_ in RULES} == set(SEGMENTS)


def test_segment_rule_examples():
    assert segment_for(5, 5, 4) == "Champions"
    assert segment_for(3, 4, 4) == "Loyal"
    assert segment_for(5, 2, 3) == "Potential loyalists"
    assert segment_for(4, 1, 1) == "New"
    assert segment_for(1, 5, 5) == "Can't lose them"
    assert segment_for(2, 4, 3) == "At risk"
    assert segment_for(1, 1, 2) == "Lost"


def test_database_segments_match_the_python_rules(five):
    for customer in five.values():
        r, f, m = customer["r_score"], customer["f_score"], customer["m_score"]
        assert customer["segment"] == segment_for(r, f, m)


def test_segments_overview(five, client):
    data = client.get("/segments").json()

    assert data["as_of"] == "2024-06-30"
    assert (data["customers"], data["revenue"]) == (5, 2350.0)
    rows = {row["segment"]: row for row in data["segments"]}
    assert [row["segment"] for row in data["segments"]] == SEGMENTS  # all 8, in order
    assert (rows["Champions"]["customers"], rows["Champions"]["revenue"]) == (2, 1800.0)
    assert rows["Champions"]["customer_share"] == 0.4
    assert rows["Champions"]["revenue_share"] == round(1800 / 2350, 4)
    assert (rows["Lost"]["customers"], rows["Lost"]["revenue"]) == (2, 250.0)
    assert rows["Loyal"]["customers"] == 0


def test_filter_by_segments(five, client):
    response = client.get("/customers", params={"segment": ["Need attention", "Lost"]})
    assert {c["external_id"] for c in response.json()["items"]} == {"C3", "C4", "C5"}


def test_filter_by_score_range_and_status(five, client):
    by_scores = client.get("/customers", params={"r_min": 2, "r_max": 4, "m_min": 3})
    assert {c["external_id"] for c in by_scores.json()["items"]} == {"C2", "C3"}

    churned = client.get("/customers", params={"status": "churned", "sort": "churned_at"})
    assert [c["external_id"] for c in churned.json()["items"]] == ["C4", "C5"]  # newest first

    active = client.get("/customers", params={"status": "active"})
    assert {c["external_id"] for c in active.json()["items"]} == {"C1", "C2", "C3"}


def test_scores_outside_1_to_5_are_refused(five, client):
    assert client.get("/customers", params={"r_min": 0}).status_code == 422
    assert client.get("/customers", params={"m_max": 6}).status_code == 422


def test_export_includes_segment_scores_and_status(five, client):
    lines = client.get("/customers/export.csv", params={"segment": "Lost"}).text.splitlines()
    columns = lines[0].split(",")
    rows = [dict(zip(columns, line.split(","), strict=True)) for line in lines[1:]]

    assert [row["customer_id"] for row in rows] == ["C4", "C5"]
    assert rows[0]["segment"] == "Lost"
    assert (rows[0]["r_score"], rows[0]["f_score"], rows[0]["m_score"]) == ("2", "2", "2")
    assert (rows[0]["status"], rows[0]["churned_on"]) == ("churned", "2024-05-31")
