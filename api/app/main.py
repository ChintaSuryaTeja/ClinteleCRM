from fastapi import FastAPI

from app.routers import analytics, auth, customers, dashboard, health, imports, users

app = FastAPI(title="CRM API")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(imports.router)
app.include_router(dashboard.router)
app.include_router(customers.router)
app.include_router(analytics.router)
