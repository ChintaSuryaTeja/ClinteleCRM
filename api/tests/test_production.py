from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app


def test_docs_are_available_in_development(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_docs_are_hidden_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    production = TestClient(create_app())

    for path in ("/docs", "/redoc", "/openapi.json"):
        assert production.get(path).status_code == 404
    assert production.get("/health").json() == {"status": "ok"}


def test_metrics_count_requests(client):
    client.get("/health/db")
    client.get("/auth/me")  # 401, still counted

    metrics = client.get("/metrics")

    assert metrics.status_code == 200
    assert 'http_requests_total{handler="/auth/me",method="GET",status="4xx"}' in metrics.text
    # Health checks and the metrics endpoint itself are left out on purpose.
    assert 'handler="/health/db"' not in metrics.text
