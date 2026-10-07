from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.routers import analytics, ask, auth, customers, dashboard, health, imports, users


def create_app() -> FastAPI:
    # The interactive docs list every endpoint: useful while developing, not
    # something to publish on a live site.
    docs_enabled = settings.environment != "production"
    application = FastAPI(
        title="CRM API",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    for module in (health, auth, users, imports, dashboard, customers, analytics, ask):
        application.include_router(module.router)

    # GET /metrics: request counts and timings for Prometheus. Nginx refuses this
    # path from the internet; only Prometheus, inside the Docker network, reads it.
    Instrumentator(excluded_handlers=["/metrics", "/health.*"]).instrument(application).expose(
        application, include_in_schema=False
    )
    return application


app = create_app()
