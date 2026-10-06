"""Churn prediction: for each active customer, the chance they place no order in
the next 90 days (which is when step 3's rule would call them churned).

How the model learns without seeing the future
----------------------------------------------
It replays the past. For a past "cutoff" date it:
  1. computes each customer's features from orders on or before the cutoff only,
  2. looks up what really happened: did they order in the 90 days after it?
Each (features, outcome) pair is one training example. Using any order after
the cutoff to build features would be "leakage": the model would look great in
testing and fail on real customers. features_at() only ever sees past orders.

How it is tested
----------------
The most recent cutoff whose 90-day outcome is known (as_of - 90 days) is kept
aside as the test set. Training cutoffs are at least 90 days before it, so
every training outcome was already known on the test date: nothing from the
test period leaks into training.

On the test set the model is compared with a naive baseline that only looks at
days since the last order. If the model doesn't beat it, the baseline's scores
are used instead and the Churn screen says so.

The model is a logistic regression: fast, and each feature's contribution to a
customer's score can be read straight off it, which gives the reasons shown
next to each score. A gradient-boosting model is measured too, for comparison.
"""

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import median

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import bindparam, select, text, update
from sqlalchemy.orm import Session

from app.metrics import CHURN_DAYS
from app.models import CustomerMetrics, ModelRun, Order

HORIZON_DAYS = CHURN_DAYS  # predict: no order in the next 90 days
CUTOFF_STEP_DAYS = 30  # training cutoffs every 30 days
MIN_HISTORY_DAYS = 90  # a cutoff needs this much history before it
MIN_TRAIN_ROWS = 100
MIN_TEST_ROWS = 30
MAX_REASONS = 3
REASON_THRESHOLD = 0.15  # contributions smaller than this (in log-odds) aren't worth saying
REASONS_FROM_SCORE = 0.2  # below this risk, the customer is low risk: no reasons

FEATURES = [
    "days_since_last",
    "overdue_ratio",
    "orders_total",
    "orders_last_90",
    "avg_order_value",
    "spend_trend",
    "tenure_days",
]
# Total spend is left out on purpose: it is orders x average order value, so it
# would repeat what those two already say and muddle the model's weights.
# Counts and money are skewed (a few huge customers), so the model sees log(1 + x).
LOG_FEATURES = {"orders_total", "orders_last_90", "avg_order_value", "tenure_days"}

Orders = list[tuple[date, float]]  # one customer's (day, amount), oldest first


# --- Features and outcomes ----------------------------------------------------


def features_at(orders: Orders, cutoff: date, typical_gap: float) -> dict | None:
    """Features for one customer on the cutoff day, from orders on or before it only.
    None if they had no orders yet, or had already churned (nothing to predict)."""
    past = [(day, amount) for day, amount in orders if day <= cutoff]
    if not past:
        return None
    days = sorted({day for day, _ in past})
    days_since_last = (cutoff - days[-1]).days
    if days_since_last >= CHURN_DAYS:
        return None

    gaps = [(later - earlier).days for earlier, later in zip(days, days[1:], strict=False)]
    avg_gap = sum(gaps) / len(gaps) if gaps else typical_gap
    recent_start = cutoff - timedelta(days=90)
    earlier_start = cutoff - timedelta(days=180)
    spend_recent = sum(amount for day, amount in past if day > recent_start)
    spend_before = sum(amount for day, amount in past if earlier_start < day <= recent_start)
    spend_total = sum(amount for _, amount in past)
    return {
        "days_since_last": days_since_last,
        # How late they are compared with their own rhythm: 2.0 = twice their usual gap.
        "overdue_ratio": days_since_last / max(avg_gap, 1.0),
        "orders_total": len(past),
        "orders_last_90": sum(1 for day, _ in past if day > recent_start),
        "spend_total": spend_total,
        "avg_order_value": spend_total / len(past),
        # Positive: spending more in the last 90 days than in the 90 before.
        "spend_trend": math.log1p(spend_recent) - math.log1p(spend_before),
        "tenure_days": (cutoff - days[0]).days,
        "avg_gap": avg_gap,  # kept for the reason text, not a model input
    }


def churned_after(orders: Orders, cutoff: date) -> int:
    """The outcome: 1 if the customer placed no order in the 90 days after the cutoff."""
    end = cutoff + timedelta(days=HORIZON_DAYS)
    return 0 if any(cutoff < day <= end for day, _ in orders) else 1


def typical_gap_at(histories: dict[int, Orders], cutoff: date) -> float:
    """Median days between orders across customers, before the cutoff. Used as the
    'usual gap' for customers with only one order so far."""
    gaps = []
    for orders in histories.values():
        days = sorted({day for day, _ in orders if day <= cutoff})
        gaps += [(later - earlier).days for earlier, later in zip(days, days[1:], strict=False)]
    return float(median(gaps)) if gaps else 30.0


BASELINE_FEATURES = ["days_since_last"]


def matrix(rows: list[dict], columns: list[str] = FEATURES) -> np.ndarray:
    return np.array(
        [[math.log1p(row[f]) if f in LOG_FEATURES else row[f] for f in columns] for row in rows],
        dtype=float,
    )


def examples_at(histories: dict[int, Orders], cutoff: date) -> tuple[list[dict], list[int]]:
    """Training or test examples: every customer active on the cutoff, with their outcome."""
    gap = typical_gap_at(histories, cutoff)
    rows, outcomes = [], []
    for orders in histories.values():
        row = features_at(orders, cutoff, gap)
        if row is not None:
            rows.append(row)
            outcomes.append(churned_after(orders, cutoff))
    return rows, outcomes


def plan_cutoffs(data_start: date, as_of: date) -> tuple[list[date], date, list[date]]:
    """(training cutoffs for testing, the test cutoff, all cutoffs for the final model).

    The test cutoff is the latest date whose 90-day outcome is known. Training
    cutoffs end 90 days before it, so their outcomes were known by then.
    """
    test = as_of - timedelta(days=HORIZON_DAYS)
    earliest = data_start + timedelta(days=MIN_HISTORY_DAYS)

    def every_30_days_back_from(start: date) -> list[date]:
        cutoffs, cutoff = [], start
        while cutoff >= earliest:
            cutoffs.append(cutoff)
            cutoff -= timedelta(days=CUTOFF_STEP_DAYS)
        return cutoffs

    return (
        every_30_days_back_from(test - timedelta(days=HORIZON_DAYS)),
        test,
        every_30_days_back_from(test),
    )


# --- Measuring --------------------------------------------------------------------


def top_decile_precision(outcomes: np.ndarray, scores: np.ndarray) -> float:
    """Of the 10% of customers scored riskiest, the share that really churned."""
    count = max(1, len(scores) // 10)
    riskiest = np.argsort(-scores, kind="stable")[:count]
    return float(outcomes[riskiest].mean())


def new_model() -> Pipeline:
    # Features are scaled to a common range so the coefficients are comparable,
    # which is what makes the per-customer reasons meaningful.
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))


def baseline_scores(rows: list[dict]) -> np.ndarray:
    """The naive rule: the longer since the last order, the riskier."""
    return np.array([row["days_since_last"] for row in rows], dtype=float)


@dataclass
class Evaluation:
    train_rows: int
    test_rows: int
    test_churn_rate: float
    model_auc: float
    baseline_auc: float
    gbm_auc: float
    model_top10: float
    baseline_top10: float

    @property
    def use_model(self) -> bool:
        return self.model_auc > self.baseline_auc


class NotEnoughData(Exception):
    pass


def evaluate(histories: dict[int, Orders], data_start: date, as_of: date) -> Evaluation:
    train_cutoffs, test_cutoff, _ = plan_cutoffs(data_start, as_of)
    train_rows, train_outcomes = [], []
    for cutoff in train_cutoffs:
        rows, outcomes = examples_at(histories, cutoff)
        train_rows += rows
        train_outcomes += outcomes
    test_rows, test_outcomes = examples_at(histories, test_cutoff)

    if len(train_rows) < MIN_TRAIN_ROWS or len(test_rows) < MIN_TEST_ROWS:
        raise NotEnoughData(
            "Predictions need about 9 months of orders and at least "
            f"{MIN_TEST_ROWS} active customers."
        )
    if len(set(train_outcomes)) < 2 or len(set(test_outcomes)) < 2:
        raise NotEnoughData(
            "The history has no churn yet (or nobody stays), so there's nothing to learn."
        )

    x_train, y_train = matrix(train_rows), np.array(train_outcomes)
    x_test, y_test = matrix(test_rows), np.array(test_outcomes)

    model_scores = new_model().fit(x_train, y_train).predict_proba(x_test)[:, 1]
    gbm_scores = (
        HistGradientBoostingClassifier(random_state=0)
        .fit(x_train, y_train)
        .predict_proba(x_test)[:, 1]
    )
    simple = baseline_scores(test_rows)
    return Evaluation(
        train_rows=len(train_rows),
        test_rows=len(test_rows),
        test_churn_rate=float(y_test.mean()),
        model_auc=float(roc_auc_score(y_test, model_scores)),
        baseline_auc=float(roc_auc_score(y_test, simple)),
        gbm_auc=float(roc_auc_score(y_test, gbm_scores)),
        model_top10=top_decile_precision(y_test, model_scores),
        baseline_top10=top_decile_precision(y_test, simple),
    )


# --- Reasons ------------------------------------------------------------------------


def orders(count: int) -> str:
    return f"{count} order" if count == 1 else f"{count} orders"


# For each feature: what to say when its value pushes the risk up, depending on
# whether the customer's value is above or below the average customer's.
REASON_TEXT = {
    "days_since_last": (
        lambda v: f"No order for {v['days_since_last']} days",
        lambda v: f"Last ordered only {v['days_since_last']} days ago",
    ),
    "overdue_ratio": (
        lambda v: (
            f"No order for {v['days_since_last']} days; usually orders every "
            f"{round(v['avg_gap'])} days"
        ),
        lambda v: "Ordering sooner than usual",
    ),
    "orders_total": (
        lambda v: f"Has placed {orders(v['orders_total'])}",
        lambda v: f"Only {orders(v['orders_total'])} so far",
    ),
    "orders_last_90": (
        lambda v: f"{orders(v['orders_last_90'])} in the last 90 days",
        lambda v: f"Only {orders(v['orders_last_90'])} in the last 90 days",
    ),
    "avg_order_value": (
        lambda v: "Large orders on average",
        lambda v: "Small orders on average",
    ),
    "spend_trend": (
        lambda v: "Spending more than in the 90 days before",
        lambda v: "Spending less than in the 90 days before",
    ),
    "tenure_days": (
        lambda v: f"Customer for {v['tenure_days']} days",
        lambda v: f"New customer: first order {v['tenure_days']} days ago",
    ),
}


def reasons_for(model: Pipeline, x: np.ndarray, row: dict) -> list[str]:
    """The features pushing this customer's risk up the most, in plain words.

    In a logistic regression a customer's score is the sum of
    coefficient x (their value - average) / spread, one term per feature.
    The largest positive terms are the reasons their risk is high.
    """
    scaler, regression = (
        model.named_steps["standardscaler"],
        model.named_steps["logisticregression"],
    )
    scaled = scaler.transform(x.reshape(1, -1))[0]
    contributions = regression.coef_[0] * scaled
    strongest = [
        int(index)
        for index in np.argsort(-contributions)
        if contributions[index] >= REASON_THRESHOLD
    ]
    names = [FEATURES[index] for index in strongest]
    # Skip reasons that would repeat another one:
    # "usually orders every N days" already says how long it has been, and when
    # all their orders were in the last 90 days, "only N orders so far" says it.
    repeats = []
    if "overdue_ratio" in names:
        repeats.append("days_since_last")
    if "orders_total" in names and row["orders_total"] == row["orders_last_90"]:
        repeats.append("orders_last_90")
    strongest = [index for index in strongest if FEATURES[index] not in repeats]

    reasons = []
    for index in strongest[:MAX_REASONS]:
        above, below = REASON_TEXT[FEATURES[index]]
        reasons.append((above if scaled[index] > 0 else below)(row))
    return reasons


# --- Running it for an organization ----------------------------------------------


def load_histories(db: Session, organization_id: int) -> dict[int, Orders]:
    histories: dict[int, Orders] = defaultdict(list)
    day = text("(ordered_at AT TIME ZONE 'UTC')::date")
    rows = db.execute(
        select(Order.customer_id, day, Order.total_amount)
        .where(Order.organization_id == organization_id)
        .order_by(Order.customer_id, Order.ordered_at)
    )
    for customer_id, order_day, amount in rows:
        histories[customer_id].append((order_day, float(amount)))
    return dict(histories)


def predict_churn(db: Session, organization_id: int) -> ModelRun | None:
    """Evaluate, train on all known history, and score today's active customers.
    Records the run (or why there wasn't one). Does not commit."""
    histories = load_histories(db, organization_id)
    clear_scores = (
        update(CustomerMetrics)
        .where(CustomerMetrics.organization_id == organization_id)
        .values(churn_score=None, churn_reasons=None)
    )
    if not histories:
        db.execute(clear_scores)
        return None
    all_days = [day for orders in histories.values() for day, _ in orders]
    data_start, as_of = min(all_days), max(all_days)
    run = ModelRun(organization_id=organization_id, trained_at=datetime.now(UTC), as_of=as_of)
    db.execute(clear_scores)

    try:
        evaluation = evaluate(histories, data_start, as_of)
    except NotEnoughData as reason:
        run.status = "not_enough_data"
        run.message = str(reason)
        db.add(run)
        return run

    # The final model learns from every cutoff whose outcome is known, test included.
    _, test_cutoff, all_cutoffs = plan_cutoffs(data_start, as_of)
    rows, outcomes = [], []
    for cutoff in all_cutoffs:
        cutoff_rows, cutoff_outcomes = examples_at(histories, cutoff)
        rows += cutoff_rows
        outcomes += cutoff_outcomes
    # If the model didn't beat the naive rule, use the rule instead, turned into a
    # probability by fitting the same kind of model on days-since-last-order alone.
    columns = FEATURES if evaluation.use_model else BASELINE_FEATURES
    model = new_model().fit(matrix(rows, columns), np.array(outcomes))

    # Score everyone active today.
    gap = typical_gap_at(histories, as_of)
    scored = []
    for customer_id, orders in histories.items():
        row = features_at(orders, as_of, gap)
        if row is None:
            continue  # already churned: nothing left to predict
        x = matrix([row], columns)[0]
        score = float(model.predict_proba(x.reshape(1, -1))[0, 1])
        if score < REASONS_FROM_SCORE:
            reasons = []
        elif evaluation.use_model:
            reasons = reasons_for(model, x, row)
        else:
            reasons = [f"No order for {row['days_since_last']} days"]
        scored.append({"b_id": customer_id, "b_score": round(score, 4), "b_reasons": reasons})

    if scored:
        # One UPDATE statement, run once per customer (an "executemany").
        table = CustomerMetrics.__table__
        db.execute(
            update(table)
            .where(
                table.c.organization_id == organization_id,
                table.c.customer_id == bindparam("b_id"),
            )
            .values(churn_score=bindparam("b_score"), churn_reasons=bindparam("b_reasons")),
            scored,
        )

    coefficients = model.named_steps["logisticregression"].coef_[0]
    run.status = "trained"
    run.used = "model" if evaluation.use_model else "baseline"
    run.test_cutoff = test_cutoff
    run.train_rows = evaluation.train_rows
    run.test_rows = evaluation.test_rows
    run.test_churn_rate = evaluation.test_churn_rate
    run.model_auc = evaluation.model_auc
    run.baseline_auc = evaluation.baseline_auc
    run.gbm_auc = evaluation.gbm_auc
    run.model_top10 = evaluation.model_top10
    run.baseline_top10 = evaluation.baseline_top10
    run.scored_customers = len(scored)
    run.coefficients = {
        name: round(float(c), 4) for name, c in zip(columns, coefficients, strict=True)
    }
    db.add(run)
    return run
