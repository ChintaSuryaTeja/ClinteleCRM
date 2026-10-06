"""Celery worker. Redis carries the job queue between the API and this process.

Start the worker with:     celery -A app.worker worker
and the scheduler with:    celery -A app.worker beat
The scheduler only puts tasks on the queue at the right time; the worker runs them.
"""

import logging

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.importer import process_delete, process_import
from app.metrics import recalculate_metrics
from app.models import Organization

logger = logging.getLogger(__name__)

celery_app = Celery("crm", broker=settings.redis_url)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "recalculate-all-nightly": {
        "task": "recalculate_all",
        "schedule": crontab(hour=settings.nightly_recalculation_hour_utc, minute=0),
    },
}


@celery_app.task(name="ping")
def ping() -> str:
    """Smoke test: proves a job can travel through the queue and run."""
    return "pong"


@celery_app.task(name="run_import")
def run_import(job_id: int) -> None:
    """Import an uploaded file, then recalculate the organization's metrics."""
    with SessionLocal() as db:
        process_import(db, job_id, settings.upload_dir)


@celery_app.task(name="delete_import")
def delete_import(job_id: int) -> None:
    """Remove an import's orders, then recalculate the organization's metrics."""
    with SessionLocal() as db:
        process_delete(db, job_id)


def recalculate_all_organizations() -> int:
    """Recalculate every organization's metrics, each in its own transaction, so
    one failure doesn't stop the others. Returns how many succeeded."""
    with SessionLocal() as db:
        organization_ids = db.scalars(select(Organization.id)).all()
    done = 0
    for organization_id in organization_ids:
        with SessionLocal() as db:
            try:
                recalculate_metrics(db, organization_id)
                db.commit()
                done += 1
            except Exception:
                db.rollback()
                logger.exception("Recalculating organization %s failed", organization_id)
    return done


@celery_app.task(name="recalculate_all")
def recalculate_all() -> int:
    """Nightly: recalculate every organization's metrics."""
    return recalculate_all_organizations()
