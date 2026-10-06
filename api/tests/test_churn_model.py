"""Churn prediction: no peeking at the future, hand-checked features, and a
model that must beat the naive "days since last order" rule."""

import math
import random
from datetime import date, timedelta

import numpy as np
import pytest
from sqlalchemy import select

from app.churn_model import (
    CUTOFF_STEP_DAYS,
    HORIZON_DAYS,
    MIN_HISTORY_DAYS,
    churned_after,
    examples_at,
    features_at,
    plan_cutoffs,
    predict_churn,
    top_decile_precision,
)
from app.models import CustomerMetrics
from tests.helpers import SAMPLE_ORDERS, orders_csv, signup, upload

D = date.fromisoformat

# --- Features and outcomes on a hand-made customer -------------------------------

ADA = [(D("2024-01-01"), 10.0), (D("2024-01-11"), 20.0), (D("2024-02-10"), 30.0)]


def test_features_on_a_hand_made_customer():
    features = features_at(ADA, D("2024-03-01"), typical_gap=99)

    assert features["days_since_last"] == 20  # 10 Feb to 1 Mar 2024 (leap year)
    assert features["avg_gap"] == 20  # gaps of 10 and 30 days
    assert features["overdue_ratio"] == 1.0  # 20 days since, usually every 20
    assert features["orders_total"] == 3
    assert features["orders_last_90"] == 3
    assert features["avg_order_value"] == 20
    assert features["spend_trend"] == math.log1p(60) - math.log1p(0)
    assert features["tenure_days"] == 60


def test_one_order_customers_use_the_typical_gap():
    features = features_at(ADA[:1], D("2024-01-21"), typical_gap=40)
    assert features["avg_gap"] == 40
    assert features["overdue_ratio"] == 20 / 40


def test_no_features_before_the_first_order_or_after_churning():
    assert features_at(ADA, D("2023-12-31"), typical_gap=30) is None
    assert features_at(ADA, D("2024-05-10"), typical_gap=30) is None  # 90 days after 10 Feb


def test_features_never_use_orders_after_the_cutoff():
    """Leakage check: adding future orders must not change anything at the cutoff."""
    cutoff = D("2024-03-01")
    future = [(D("2024-03-02"), 500.0), (D("2024-04-15"), 900.0)]

    assert features_at(ADA + future, cutoff, 30) == features_at(ADA, cutoff, 30)


def test_outcome_looks_only_at_the_90_days_after_the_cutoff():
    cutoff = D("2024-03-01")
    assert churned_after(ADA, cutoff) == 1  # no order after 10 Feb
    assert churned_after(ADA + [(cutoff + timedelta(days=90), 5.0)], cutoff) == 0  # day 90 counts
    assert churned_after(ADA + [(cutoff + timedelta(days=91), 5.0)], cutoff) == 1  # too late
    assert churned_after(ADA + [(cutoff, 5.0)], cutoff) == 1  # the cutoff day itself is the past


def test_training_outcomes_are_all_known_before_the_test_cutoff():
    data_start, as_of = D("2023-01-01"), D("2024-12-31")
    train, test, everything = plan_cutoffs(data_start, as_of)

    assert test + timedelta(days=HORIZON_DAYS) == as_of
    assert all(c + timedelta(days=HORIZON_DAYS) <= test for c in train)
    assert all(c >= data_start + timedelta(days=MIN_HISTORY_DAYS) for c in everything)
    assert all(
        a - b == timedelta(days=CUTOFF_STEP_DAYS) for a, b in zip(train, train[1:], strict=False)
    )
    assert test in everything and set(train) < set(everything)


def test_examples_at_a_cutoff_ignore_later_history():
    histories = synthetic_histories()
    cutoff = D("2024-06-01")
    trimmed = {cid: [o for o in orders if o[0] <= cutoff] for cid, orders in histories.items()}

    rows_full, _ = examples_at(histories, cutoff)
    rows_trimmed, _ = examples_at(trimmed, cutoff)

    assert rows_full == rows_trimmed


def test_top_decile_precision():
    outcomes = np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0] * 2)
    scores = np.arange(20, 0, -1, dtype=float)  # first two are the riskiest
    assert top_decile_precision(outcomes, scores) == 0.5  # 1 of the top 2 churned


# --- A synthetic business that fools the naive rule --------------------------------
# Weekly regulars: half of them quietly stop at some point. Monthly buyers: order
# every 45-70 days and never leave. A regular who stopped 20 days ago is about to
# churn; a monthly buyer last seen 40 days ago is fine. "Days since last order"
# gets that backwards, so the real model, which knows each customer's usual
# rhythm, should rank much better.


def synthetic_histories(seed: int = 7) -> dict[str, list[tuple[date, float]]]:
    rng = random.Random(seed)
    start, end = D("2023-01-01"), D("2024-12-31")
    histories = {}
    for number in range(120):
        gap = rng.randint(6, 12)
        stops = start + timedelta(days=rng.randint(150, 700)) if number % 2 else end
        day, orders = start + timedelta(days=rng.randint(0, 30)), []
        while day <= min(stops, end):
            orders.append((day, float(rng.randint(20, 40))))
            day += timedelta(days=gap + rng.randint(-2, 2))
        histories[f"W{number}"] = orders
    for number in range(120):
        day, orders = start + timedelta(days=rng.randint(0, 60)), []
        while day <= end:
            orders.append((day, float(rng.randint(80, 120))))
            day += timedelta(days=rng.randint(45, 70))
        histories[f"M{number}"] = orders
    return histories


def synthetic_csv() -> str:
    rows = []
    for customer, orders in synthetic_histories().items():
        for index, (day, amount) in enumerate(orders):
            rows.append((f"{customer}-{index}", day.isoformat(), customer, str(amount)))
    return orders_csv(rows)


@pytest.fixture
def trained(client, db):
    me = signup(client, "Acme", "admin@acme.com")
    upload(client, synthetic_csv())
    run = predict_churn(db, me["organization"]["id"])
    db.flush()
    return client, run


def test_model_beats_the_naive_baseline(trained):
    _, run = trained

    assert run.status == "trained"
    assert run.used == "model"
    assert run.model_auc > run.baseline_auc + 0.1
    assert run.model_auc > 0.85
    assert run.model_top10 >= run.baseline_top10
    assert run.train_rows > run.test_rows > 0


def test_scores_and_reasons_for_active_customers_only(trained, db):
    client, run = trained
    customers = client.get("/customers", params={"page_size": 200}).json()["items"]

    for customer in customers:
        if customer["is_churned"]:
            assert customer["churn_risk"] is None  # already gone: nothing to predict
        else:
            assert 0 <= customer["churn_risk"] <= 1
            if customer["churn_risk"] < 0.2:
                assert customer["churn_reasons"] == []
    active = client.get("/customers", params={"status": "active"}).json()["total"]
    assert run.scored_customers == active  # every active customer, on every page

    risky = [c for c in customers if (c["churn_risk"] or 0) >= 0.5]
    assert risky, "some quietly stopped regulars should be flagged"
    for customer in risky:
        assert 1 <= len(customer["churn_reasons"]) <= 3
        assert not any(" 1 orders" in reason for reason in customer["churn_reasons"])


def test_churn_endpoint_reports_the_model(trained):
    client, run = trained
    model = client.get("/churn").json()["model"]

    assert model["status"] == "trained"
    assert model["used"] == "model"
    assert model["model_auc"] == pytest.approx(run.model_auc)
    assert model["baseline_auc"] == pytest.approx(run.baseline_auc)
    assert model["test_cutoff"] == run.test_cutoff.isoformat()


def test_sort_and_filter_by_churn_risk(trained):
    client, _ = trained

    at_risk = client.get(
        "/customers", params={"status": "active", "sort": "churn_risk", "min_churn_risk": 50}
    ).json()["items"]

    risks = [c["churn_risk"] for c in at_risk]
    assert risks and all(risk >= 0.5 for risk in risks)
    assert risks == sorted(risks, reverse=True)


def test_small_history_gets_no_model(client, db):
    me = signup(client, "Acme", "admin@acme.com")
    upload(client, SAMPLE_ORDERS)

    run = predict_churn(db, me["organization"]["id"])
    db.flush()

    assert run.status == "not_enough_data"
    assert "9 months" in run.message
    assert db.scalar(select(CustomerMetrics.churn_score).limit(1)) is None
    assert client.get("/churn").json()["model"]["status"] == "not_enough_data"


def test_each_organization_gets_its_own_model(make_client, db):
    acme = make_client()
    acme_org = signup(acme, "Acme", "admin@acme.com")["organization"]["id"]
    upload(acme, synthetic_csv())
    globex = make_client()
    globex_org = signup(globex, "Globex", "admin@globex.com")["organization"]["id"]
    upload(globex, SAMPLE_ORDERS)

    predict_churn(db, acme_org)
    predict_churn(db, globex_org)
    db.flush()

    assert acme.get("/churn").json()["model"]["status"] == "trained"
    assert globex.get("/churn").json()["model"]["status"] == "not_enough_data"
    assert all(c["churn_risk"] is None for c in globex.get("/customers").json()["items"])
