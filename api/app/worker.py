"""Celery worker. Redis carries the job queue between the API and this process.

Later steps add the nightly metrics and scoring tasks here.
Start it with: celery -A app.worker worker
"""

from celery import Celery

from app.config import settings
from app.db import SessionLocal
from app.importer import process_delete, process_import

celery_app = Celery("crm", broker=settings.redis_url)


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
