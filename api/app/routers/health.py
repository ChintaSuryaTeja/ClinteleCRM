from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.deps import DbSession

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    """The API process is up."""
    return {"status": "ok"}


@router.get("/db")
def health_db(db: DbSession) -> dict[str, str]:
    """The API can reach the database."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Database unreachable") from exc
    return {"status": "ok"}
