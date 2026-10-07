"""All configuration comes from environment variables.

pydantic-settings reads each field from the environment variable with the same
name (case-insensitive). A missing required variable stops the app at startup,
which is better than failing later with a confusing error.
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # "production" hides the interactive API docs (/docs, /redoc, /openapi.json).
    environment: Literal["development", "production"] = "development"
    database_url: str
    redis_url: str
    # Signs login tokens. Anyone who knows it can forge a login, so it must be
    # long, random and never committed.
    jwt_secret: str = Field(min_length=32)
    jwt_expire_minutes: int = 720
    # Send the login cookie over HTTPS only. Must be true in production.
    cookie_secure: bool = False
    # Uploaded import files wait here until the worker processes them. The API
    # and the worker must both see this folder (a shared Docker volume).
    upload_dir: str = "/data/uploads"
    max_upload_mb: int = 50
    # When the scheduler recalculates every organization's metrics each night.
    nightly_recalculation_hour_utc: int = Field(default=2, ge=0, le=23)
    # Plain-English questions (Ask screen): which AI writes the SQL. Without
    # that provider's key the screen says it isn't set up; nothing else changes.
    ask_provider: Literal["anthropic", "google"] = "anthropic"
    anthropic_api_key: str | None = None
    ask_model: str = "claude-opus-5-5"
    google_api_key: str | None = None
    google_model: str = "gemini-3.5-flash"
    # Tried when Google reports the main model as busy.
    google_fallback_model: str = "gemini-2.5-flash"


settings = Settings()
