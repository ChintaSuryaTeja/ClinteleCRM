"""Shared test setup.

Tests run against a real PostgreSQL database: the app's database name plus
"_test" (for example crm_test). It is created if missing, and its tables are
built by running the Alembic migrations, the same way a real deploy does.

Each test runs inside a database transaction that is rolled back at the end,
so no test can see data left behind by another.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def _use_test_database() -> str:
    app_url = make_url(os.environ["DATABASE_URL"])
    if app_url.database.endswith("_test"):
        test_url = app_url
    else:
        test_url = app_url.set(database=f"{app_url.database}_test")

    server = create_engine(app_url, isolation_level="AUTOCOMMIT")
    with server.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": test_url.database}
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    server.dispose()
    return test_url.render_as_string(hide_password=False)


# This must happen before any app module is imported, because app.config reads
# DATABASE_URL once at import time.
os.environ["DATABASE_URL"] = _use_test_database()

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.ask_sql import run_select  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import engine, get_db  # noqa: E402
from app.importer import process_delete, process_import  # noqa: E402
from app.main import app  # noqa: E402
from app.routers.ask import get_query_runner  # noqa: E402
from app.routers.imports import JobQueue, get_job_queue  # noqa: E402


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    return Config(str(Path(__file__).parent.parent / "alembic.ini"))


@pytest.fixture(scope="session", autouse=True)
def migrated_database(alembic_config: Config) -> None:
    """Start every test run from an empty database migrated to the latest version."""
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    # "create_savepoint" makes the app's own commit() calls commit only a
    # savepoint, so the outer rollback below still undoes everything.
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def no_real_ai_keys(monkeypatch) -> None:
    """Tests use fake AI clients; make sure no real key from .env is ever used."""
    monkeypatch.setattr(settings, "ask_provider", "anthropic")
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "google_api_key", None)


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch) -> str:
    """Each test gets its own empty folder for uploaded files."""
    path = str(tmp_path / "uploads")
    monkeypatch.setattr(settings, "upload_dir", path)
    return path


@pytest.fixture
def make_client(db: Session):
    """Return a function that creates API clients. Each client is a separate
    browser with its own cookies, which is how tests log in as different users."""
    app.dependency_overrides[get_db] = lambda: db
    # Instead of sending jobs to the worker through Redis, run them straight
    # away inside the test's transaction.
    app.dependency_overrides[get_job_queue] = lambda: JobQueue(
        run_import=lambda job_id: process_import(db, job_id, settings.upload_dir),
        delete_import=lambda job_id: process_delete(db, job_id),
    )
    # Questions run as the restricted role inside the test's transaction.
    app.dependency_overrides[get_query_runner] = lambda: (
        lambda organization_id, sql: run_select(db.connection(), organization_id, sql)
    )
    clients: list[TestClient] = []

    def _make() -> TestClient:
        client = TestClient(app)
        clients.append(client)
        return client

    yield _make
    for client in clients:
        client.close()
    app.dependency_overrides.clear()


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()
