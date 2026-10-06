"""All configuration comes from environment variables.

pydantic-settings reads each field from the environment variable with the same
name (case-insensitive). A missing required variable stops the app at startup,
which is better than failing later with a confusing error.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
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


settings = Settings()
