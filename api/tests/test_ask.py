"""Plain-English questions: the SQL checks, the restricted database role, the
row limit and time limit, organization isolation, and the endpoint.

No test calls the real Claude API: a fake writer returns the SQL instead.
"""

from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app import ask_llm, ask_sql
from app.ask_llm import AskNotConfigured, AskServiceError, ChartSpec, SqlAnswer
from app.ask_sql import QueryFailed, UnsafeQuery, run_select, validate_sql
from app.config import settings
from app.main import app
from app.routers.ask import get_sql_writer
from tests.helpers import SAMPLE_ORDERS, add_user, login, signup, upload

# --- The SQL checks ---------------------------------------------------------------

ALLOWED = [
    "SELECT date_trunc('month', order_date) AS month, SUM(total) AS revenue "
    "FROM orders GROUP BY 1 ORDER BY 1",
    "SELECT segment, COUNT(*) FROM customers WHERE name ILIKE '%a%' OR segment LIKE 'C%' "
    "GROUP BY segment",
    "WITH spend AS (SELECT customer_id, SUM(total) AS s FROM orders GROUP BY 1) "
    "SELECT c.customer_ref, ROUND(s, 2) FROM spend JOIN customers c USING (customer_id)",
    "SELECT product_code, SUM(line_total), RANK() OVER (ORDER BY SUM(line_total) DESC) "
    "FROM order_items GROUP BY 1",
    "SELECT CASE WHEN churn_risk > 0.5 THEN 'high' ELSE 'low' END AS band, COUNT(*) "
    "FROM customers WHERE NOT is_churned GROUP BY 1",
    "SELECT EXTRACT(YEAR FROM day)::int, SUM(revenue) FROM daily_revenue GROUP BY 1",
    "SELECT COUNT(*) FROM customers WHERE EXISTS "
    "(SELECT 1 FROM orders WHERE orders.customer_id = customers.customer_id)",
]

REFUSED = {
    "DELETE FROM orders": "Only SELECT",
    "UPDATE customers SET name = 'x'": "Only SELECT",
    "INSERT INTO orders VALUES (1)": "Only SELECT",
    "DROP TABLE orders": "Only SELECT",
    "SELECT 1; DROP TABLE orders": "single query",
    "SELECT * INTO copy_of_orders FROM orders": "Only reading",
    "WITH gone AS (DELETE FROM orders RETURNING *) SELECT * FROM gone": "Only reading",
    "SELECT * FROM orders FOR UPDATE": "Only reading",
    "SELECT * FROM public.orders": "schema",
    "SELECT * FROM pg_catalog.pg_user": "schema",
    "SELECT * FROM information_schema.tables": "schema",
    "SELECT * FROM users": "isn't one of the tables",
    "SELECT * FROM organizations": "isn't one of the tables",
    "SELECT set_config('crm.organization_id', '1', true)": "set_config",
    "SELECT pg_sleep(60)": "pg_sleep",
    "SELECT current_setting('crm.organization_id')": "current_setting",
    "SELECT * FROM dblink('host=x', 'select 1') AS t(a int)": "isn't one of the tables",
    "SELECT lo_import('/etc/passwd')": "lo_import",
    "SET ROLE crm": "Only SELECT",
    "this is not sql at all": "",
}


@pytest.mark.parametrize("sql", ALLOWED)
def test_ordinary_questions_pass_the_checks(sql):
    assert validate_sql(sql) == sql


@pytest.mark.parametrize(("sql", "reason"), REFUSED.items())
def test_anything_else_is_refused(sql, reason):
    with pytest.raises(UnsafeQuery) as refused:
        validate_sql(sql)
    assert reason in str(refused.value)


# --- Running as the restricted role ------------------------------------------------


@pytest.fixture
def two_orgs(make_client):
    acme = make_client()
    acme_id = signup(acme, "Acme", "admin@acme.com")["organization"]["id"]
    upload(acme, SAMPLE_ORDERS)
    globex = make_client()
    globex_id = signup(globex, "Globex", "admin@globex.com")["organization"]["id"]
    return acme, acme_id, globex, globex_id


def test_queries_only_see_their_own_organization(two_orgs, db):
    _, acme_id, _, globex_id = two_orgs
    connection = db.connection()

    acme = run_select(connection, acme_id, "SELECT customer_ref FROM customers ORDER BY 1")
    globex = run_select(connection, globex_id, "SELECT COUNT(*) FROM orders")

    assert acme.rows == [["C1"], ["C2"], ["C3"]]
    assert globex.rows == [[0]]


def test_the_database_refuses_writes_even_without_the_checks(two_orgs, db):
    _, acme_id, _, _ = two_orgs
    with pytest.raises(QueryFailed, match="permission denied"):
        run_select(db.connection(), acme_id, "DELETE FROM orders")


def test_the_database_refuses_the_real_tables_even_without_the_checks(two_orgs, db):
    _, acme_id, _, _ = two_orgs
    with pytest.raises(QueryFailed, match="permission denied"):
        run_select(db.connection(), acme_id, "SELECT COUNT(*) FROM public.orders")


def test_the_database_refuses_switching_organization_even_without_the_checks(two_orgs, db):
    _, _, _, globex_id = two_orgs
    escape = "SELECT set_config('crm.organization_id', '1', true)"
    with pytest.raises(QueryFailed, match="permission denied for function set_config"):
        run_select(db.connection(), globex_id, escape)


def test_slow_queries_are_stopped(two_orgs, db, monkeypatch):
    _, acme_id, _, _ = two_orgs
    monkeypatch.setattr(ask_sql, "TIMEOUT_SECONDS", 1)
    with pytest.raises(QueryFailed, match="statement timeout"):
        run_select(db.connection(), acme_id, "SELECT pg_sleep(3)")


def test_results_are_capped(two_orgs, db, monkeypatch):
    _, acme_id, _, _ = two_orgs
    monkeypatch.setattr(ask_sql, "ROW_LIMIT", 2)

    result = run_select(db.connection(), acme_id, "SELECT * FROM order_items")

    assert len(result.rows) == 2
    assert result.truncated is True


def test_the_connection_is_restored_afterwards(two_orgs, db):
    _, acme_id, _, _ = two_orgs
    before = db.execute(text("SELECT current_user")).scalar()

    run_select(db.connection(), acme_id, "SELECT 1")

    assert db.execute(text("SELECT current_user")).scalar() == before
    assert db.execute(text("SELECT current_setting('crm.organization_id', true)")).scalar() in (
        None,
        "",
    )


# --- The endpoint --------------------------------------------------------------------


def fake_writer(sql: str | None, chart="bar", answerable=True, calls=None):
    def write(question, *, currency, as_of):
        if calls is not None:
            calls.append({"question": question, "currency": currency, "as_of": as_of})
        return SqlAnswer(
            answerable=answerable,
            reason=None if answerable else "There is no data about refunds.",
            title="Revenue by customer",
            sql=sql,
            chart=ChartSpec(type=chart, x="customer_ref", y="revenue"),
        )

    return write


def use_writer(writer):
    app.dependency_overrides[get_sql_writer] = lambda: writer


def test_question_returns_rows_chart_and_sql(two_orgs):
    acme, *_ = two_orgs
    calls = []
    sql = (
        "SELECT c.customer_ref, SUM(o.total) AS revenue FROM orders o "
        "JOIN customers c USING (customer_id) GROUP BY 1 ORDER BY 2 DESC"
    )
    use_writer(fake_writer(sql, calls=calls))

    data = acme.post("/ask", json={"question": "  Revenue by customer?  "}).json()

    assert data["error"] is None
    assert data["sql"] == sql
    assert data["columns"] == ["customer_ref", "revenue"]
    assert data["rows"] == [["C2", 75.0], ["C1", 55.5], ["C3", 10.0]]
    assert data["chart"] == {"type": "bar", "x": "customer_ref", "y": "revenue"}
    assert [(c["question"], c["currency"]) for c in calls] == [("Revenue by customer?", "USD")]
    assert calls[0]["as_of"].isoformat() == "2024-03-01"  # the latest order, as "today"


def test_unsafe_sql_from_the_model_is_refused_and_shown(two_orgs):
    acme, *_ = two_orgs
    use_writer(fake_writer("DELETE FROM orders"))

    data = acme.post("/ask", json={"question": "Delete everything"}).json()

    assert data["error"].startswith("The query was refused before running")
    assert data["sql"] == "DELETE FROM orders"
    assert data["rows"] == []
    assert acme.get("/dashboard").json()["orders"] == 5  # nothing was deleted


def test_unanswerable_question_says_why(two_orgs):
    acme, *_ = two_orgs
    use_writer(fake_writer(None, answerable=False))

    data = acme.post("/ask", json={"question": "How many refunds?"}).json()

    assert data["error"] == "There is no data about refunds."
    assert data["sql"] is None


def test_failing_sql_reports_the_database_error(two_orgs):
    acme, *_ = two_orgs
    use_writer(fake_writer("SELECT no_such_column FROM orders"))

    data = acme.post("/ask", json={"question": "Broken"}).json()

    assert data["error"].startswith("The query failed:")
    assert "no_such_column" in data["error"]


def test_each_organization_asks_about_its_own_data(two_orgs):
    acme, _, globex, _ = two_orgs
    use_writer(fake_writer("SELECT COUNT(*) AS orders FROM orders", chart="number"))

    assert acme.post("/ask", json={"question": "How many orders?"}).json()["rows"] == [[5]]
    assert globex.post("/ask", json={"question": "How many orders?"}).json()["rows"] == [[0]]


def test_viewers_can_ask(two_orgs, make_client):
    acme, *_ = two_orgs
    add_user(acme, "viewer@acme.com", "viewer")
    viewer = make_client()
    login(viewer, "viewer@acme.com")
    use_writer(fake_writer("SELECT COUNT(*) FROM customers", chart="number"))

    assert viewer.post("/ask", json={"question": "How many customers?"}).json()["rows"] == [[3]]


def test_asking_requires_login(client):
    assert client.post("/ask", json={"question": "Anything?"}).status_code == 401


def test_without_an_api_key_the_feature_says_it_is_not_set_up(client, monkeypatch):
    signup(client, "Acme", "admin@acme.com")
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    app.dependency_overrides.pop(get_sql_writer, None)  # use the real writer

    response = client.post("/ask", json={"question": "Revenue last month?"})

    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


# --- The request sent to Claude (with a fake client, no network) ----------------------


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def fake_anthropic(monkeypatch, response):
    messages = FakeMessages(response)
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    monkeypatch.setattr(ask_llm.anthropic, "Anthropic", lambda **_: client)
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    return messages


def reply(text_json: str, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text_json)]
    )


def test_request_to_claude(monkeypatch):
    answer = (
        '{"answerable": true, "reason": null, "title": "Orders", '
        '"sql": "SELECT COUNT(*) FROM orders", '
        '"chart": {"type": "number", "x": null, "y": "count"}}'
    )
    messages = fake_anthropic(monkeypatch, reply(answer))

    result = ask_llm.write_sql("How many orders?", currency="GBP", as_of=None)

    assert result.sql == "SELECT COUNT(*) FROM orders"
    sent = messages.kwargs
    assert sent["model"] == "claude-opus-5-5"
    assert sent["output_config"]["effort"] == "medium"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert sent["betas"] == ["server-side-fallback-2026-07-01"]
    assert sent["extra_body"] == {"fallbacks": "default"}
    assert sent["messages"] == [{"role": "user", "content": "How many orders?"}]
    assert "GBP" in sent["system"]


def test_a_refusal_is_reported(monkeypatch):
    fake_anthropic(monkeypatch, reply("", stop_reason="refusal"))
    with pytest.raises(AskServiceError, match="declined"):
        ask_llm.write_sql("Anything", currency="USD", as_of=None)


def test_a_malformed_answer_is_reported(monkeypatch):
    fake_anthropic(monkeypatch, reply('{"not": "what we asked for"}'))
    with pytest.raises(AskServiceError, match="unexpected shape"):
        ask_llm.write_sql("Anything", currency="USD", as_of=None)


def test_no_key_means_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    with pytest.raises(AskNotConfigured):
        ask_llm.write_sql("Anything", currency="USD", as_of=None)


# --- The request sent to Gemini (with a fake client, no network) ----------------------

GOOD_ANSWER = (
    '{"answerable": true, "reason": null, "title": "Orders", '
    '"sql": "SELECT COUNT(*) FROM orders", "chart": {"type": "number", "x": null, "y": "count"}}'
)


class FakeGeminiModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)  # per call: a response, or an exception to raise
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def gemini_reply(text_json, finish="STOP"):
    from google.genai import types

    return SimpleNamespace(
        text=text_json,
        candidates=[SimpleNamespace(finish_reason=getattr(types.FinishReason, finish))],
    )


def fake_gemini(monkeypatch, *outcomes):
    models = FakeGeminiModels(outcomes)
    monkeypatch.setattr(ask_llm.genai, "Client", lambda **_: SimpleNamespace(models=models))
    monkeypatch.setattr(settings, "ask_provider", "google")
    monkeypatch.setattr(settings, "google_api_key", "test-key")
    return models


def busy():
    from google.genai import errors

    return errors.ServerError(503, {"error": {"message": "high demand", "status": "UNAVAILABLE"}})


def test_request_to_gemini(monkeypatch):
    models = fake_gemini(monkeypatch, gemini_reply(GOOD_ANSWER))

    result = ask_llm.write_sql("How many orders?", currency="GBP", as_of=None)

    assert result.sql == "SELECT COUNT(*) FROM orders"
    sent = models.calls[0]
    assert sent["model"] == settings.google_model
    assert sent["contents"] == "How many orders?"
    assert sent["config"].response_mime_type == "application/json"
    assert sent["config"].response_json_schema == ask_llm.OUTPUT_SCHEMA
    assert "GBP" in sent["config"].system_instruction


def test_gemini_falls_back_when_the_main_model_is_busy(monkeypatch):
    models = fake_gemini(monkeypatch, busy(), gemini_reply(GOOD_ANSWER))

    result = ask_llm.write_sql("How many orders?", currency="USD", as_of=None)

    assert result.sql == "SELECT COUNT(*) FROM orders"
    assert [call["model"] for call in models.calls] == [
        settings.google_model,
        settings.google_fallback_model,
    ]


def test_gemini_busy_everywhere_is_reported(monkeypatch):
    fake_gemini(monkeypatch, busy(), busy())
    with pytest.raises(AskServiceError, match="busy"):
        ask_llm.write_sql("Anything", currency="USD", as_of=None)


def test_gemini_rejected_request_is_reported(monkeypatch):
    from google.genai import errors

    rejected = errors.ClientError(
        400, {"error": {"message": "API key not valid", "status": "INVALID"}}
    )
    fake_gemini(monkeypatch, rejected)
    with pytest.raises(AskServiceError, match="rejected the request"):
        ask_llm.write_sql("Anything", currency="USD", as_of=None)


def test_gemini_safety_block_is_reported(monkeypatch):
    fake_gemini(monkeypatch, gemini_reply(None, finish="SAFETY"))
    with pytest.raises(AskServiceError, match="declined"):
        ask_llm.write_sql("Anything", currency="USD", as_of=None)


def test_gemini_without_a_key_is_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "ask_provider", "google")
    with pytest.raises(AskNotConfigured, match="GOOGLE_API_KEY"):
        ask_llm.write_sql("Anything", currency="USD", as_of=None)


def test_provider_setting_picks_the_service(monkeypatch):
    gemini = fake_gemini(monkeypatch, gemini_reply(GOOD_ANSWER))
    claude = fake_anthropic(monkeypatch, reply(GOOD_ANSWER))

    monkeypatch.setattr(settings, "ask_provider", "google")
    ask_llm.write_sql("Q", currency="USD", as_of=None)
    monkeypatch.setattr(settings, "ask_provider", "anthropic")
    ask_llm.write_sql("Q", currency="USD", as_of=None)

    assert len(gemini.calls) == 1
    assert claude.kwargs is not None
