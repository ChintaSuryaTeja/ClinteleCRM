from app.worker import ping


def test_ping_task_runs():
    # apply() runs the task in this process, so the test needs no Redis.
    assert ping.apply().get() == "pong"


def test_nightly_task_recalculates_every_organization(make_client, db, monkeypatch):
    from sqlalchemy import select

    from app import worker
    from app.models import CustomerMetrics
    from tests.helpers import SAMPLE_ORDERS, signup, upload

    for name in ("Acme", "Globex"):
        client = make_client()
        signup(client, name, f"admin@{name.lower()}.com")
        upload(client, SAMPLE_ORDERS)
    # Wipe the scores, as if they were stale.
    for metrics in db.scalars(select(CustomerMetrics)):
        metrics.segment = None
    db.flush()

    # The task opens its own sessions; point them at the test's transaction.
    monkeypatch.setattr(worker, "SessionLocal", lambda: _NoCloseSession(db))
    assert worker.recalculate_all_organizations() == 2

    db.expire_all()  # the update ran as SQL; reload instead of using objects in memory
    assert all(m.segment for m in db.scalars(select(CustomerMetrics)))


class _NoCloseSession:
    """Lets the task use the test's session without closing or committing it for real."""

    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, *exc):
        return False
