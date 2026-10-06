"""Questions in plain English, answered with a chart and the SQL that produced it."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ask_llm import AskNotConfigured, AskServiceError, ChartSpec, SqlAnswer, write_sql
from app.ask_sql import (
    TIMEOUT_SECONDS,
    QueryFailed,
    UnsafeQuery,
    run_question_query,
    validate_sql,
)
from app.db import engine
from app.deps import CurrentUser, DbSession
from app.models import OrganizationMetrics

router = APIRouter(prefix="/ask", tags=["ask"])


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AskOut(BaseModel):
    question: str
    title: str | None
    sql: str | None
    chart: ChartSpec | None
    columns: list[str]
    rows: list[list]
    truncated: bool
    # A problem worth showing next to the SQL (refused, failed, unanswerable).
    error: str | None


SqlWriter = Callable[..., SqlAnswer]
QueryRunner = Callable[[int, str], object]


def get_sql_writer() -> SqlWriter:
    """Who writes the SQL. Tests replace this so they never call the real API."""
    return write_sql


def get_query_runner() -> QueryRunner:
    """Who runs it. Tests replace this to run inside their own transaction."""
    return lambda organization_id, sql: run_question_query(engine, organization_id, sql)


@router.post("")
def ask(
    body: AskIn,
    user: CurrentUser,
    db: DbSession,
    writer: Annotated[SqlWriter, Depends(get_sql_writer)],
    runner: Annotated[QueryRunner, Depends(get_query_runner)],
) -> AskOut:
    question = body.question.strip()
    org_metrics = db.get(OrganizationMetrics, user.organization_id)
    try:
        answer = writer(
            question,
            currency=user.organization.currency,
            as_of=org_metrics.as_of if org_metrics else None,
        )
    except AskNotConfigured as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    except AskServiceError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error

    def reply(error: str | None = None, **found) -> AskOut:
        return AskOut(
            question=question,
            title=answer.title,
            sql=answer.sql,
            chart=answer.chart,
            columns=found.get("columns", []),
            rows=found.get("rows", []),
            truncated=found.get("truncated", False),
            error=error,
        )

    if not answer.answerable or not answer.sql:
        return reply(answer.reason or "That question can't be answered from your sales data.")
    try:
        sql = validate_sql(answer.sql)
    except UnsafeQuery as refused:
        return reply(f"The query was refused before running: {refused}")
    try:
        result = runner(user.organization_id, sql)
    except QueryFailed as failed:
        if failed.timed_out:
            return reply(f"The query took longer than {TIMEOUT_SECONDS} seconds and was stopped.")
        return reply(f"The query failed: {failed}")
    return reply(columns=result.columns, rows=result.rows, truncated=result.truncated)
