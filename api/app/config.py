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


settings = Settings()
