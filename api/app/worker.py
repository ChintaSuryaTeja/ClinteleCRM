"""Celery worker. Redis carries the job queue between the API and this process.

Later steps add the import, metrics and nightly scoring tasks here.
Start it with: celery -A app.worker worker
"""

from celery import Celery

from app.config import settings

celery_app = Celery("crm", broker=settings.redis_url)


@celery_app.task(name="ping")
def ping() -> str:
    """Smoke test: proves a job can travel through the queue and run."""
    return "pong"
