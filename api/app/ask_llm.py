"""Turning a question into SQL with Claude.

Only the question and a description of the tables are sent to Claude, never
the organization's data. Claude replies with structured JSON (the SQL plus a
chart suggestion), which app/ask_sql.py then checks and runs.
"""

import json
from datetime import date
from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

from app.config import settings


class ChartSpec(BaseModel):
    type: Literal["bar", "line", "number", "table"]
    x: str | None  # column for the x axis (bar and line)
    y: str | None  # numeric column to plot (bar, line and number)


class SqlAnswer(BaseModel):
    answerable: bool
    reason: str | None  # why not, when the data can't answer it
    title: str
    sql: str | None
    chart: ChartSpec


class AskNotConfigured(Exception):
    pass


class AskServiceError(Exception):
    """Claude couldn't be reached or didn't return a usable answer."""


SCHEMA = """
customers(customer_id, customer_ref, name, email, first_order_date, last_order_date,
          orders, total_spent, segment, recency_score, frequency_score, monetary_score,
          lifetime_value, is_churned, churned_on, churn_risk)
  - one row per customer; customer_ref is the business's own customer ID
  - segment is one of: Champions, Loyal, Potential loyalists, New, Need attention,
    At risk, Can't lose them, Lost
  - the three scores are 1 (worst) to 5 (best)
  - is_churned: no order for 90 days; churned_on: the day they became churned
  - churn_risk: predicted chance (0 to 1) an active customer churns in the next
    90 days; empty for churned customers
orders(order_id, order_ref, customer_id, order_date, ordered_at, total)
  - one row per order; join to customers on customer_id; order_ref is the
    business's own order number; total is the order's value
order_items(order_id, product_code, product_name, quantity, unit_price, line_total)
  - one row per product in an order; join to orders on order_id
daily_revenue(day, revenue, orders)
  - revenue and number of orders per day (fastest for revenue over time)
"""

INSTRUCTIONS = """You turn questions about a business's sales data into one PostgreSQL query.

Tables (the only ones that exist; use the names exactly, without a schema prefix):
{schema}
Rules:
- Write exactly one SELECT statement (WITH clauses are fine). Never write anything
  that changes data.
- Use only the tables and columns above and common functions (aggregates,
  date_trunc, extract, round, coalesce, window functions, CASE, casts).
- All money is in {currency}. The data runs until {as_of}; treat that day as
  "today" for questions like "last month" or "this year".
- Name output columns in snake_case. Round money to 2 decimals.
- Order the rows sensibly, and when a question asks for "top" items without a
  number, return the top 10.
- Pick a chart: "line" for a value over time (x = the time column), "bar" to
  compare categories (x = the category), "number" for a single value, "table"
  for anything else. y is the numeric column to plot.
- If the tables can't answer the question, set answerable to false, explain
  why in reason, and leave sql empty.
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean"},
        "reason": {"type": ["string", "null"]},
        "title": {"type": "string"},
        "sql": {"type": ["string", "null"]},
        "chart": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["bar", "line", "number", "table"]},
                "x": {"type": ["string", "null"]},
                "y": {"type": ["string", "null"]},
            },
            "required": ["type", "x", "y"],
            "additionalProperties": False,
        },
    },
    "required": ["answerable", "reason", "title", "sql", "chart"],
    "additionalProperties": False,
}


def write_sql(question: str, *, currency: str, as_of: date | None) -> SqlAnswer:
    if not settings.anthropic_api_key:
        raise AskNotConfigured(
            "Add an Anthropic API key as ANTHROPIC_API_KEY in the .env file, then restart the app."
        )
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=60)
    system = INSTRUCTIONS.format(
        schema=SCHEMA, currency=currency, as_of=as_of.isoformat() if as_of else "today"
    )
    try:
        response = client.beta.messages.create(
            model=settings.ask_model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": question}],
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
            },
            # If a safety classifier declines, the API retries on a suitable
            # fallback model instead of returning a refusal.
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},
        )
    except anthropic.APIConnectionError as error:
        raise AskServiceError("Couldn't reach the AI service. Try again in a moment.") from error
    except anthropic.RateLimitError as error:
        raise AskServiceError("The AI service is busy. Try again in a minute.") from error
    except anthropic.APIStatusError as error:
        raise AskServiceError(f"The AI service returned an error ({error.status_code}).") from error

    if response.stop_reason == "refusal":
        raise AskServiceError("The AI service declined to answer that question.")
    if response.stop_reason == "max_tokens":
        raise AskServiceError("The AI service's answer was cut off. Try a simpler question.")
    text = next((block.text for block in response.content if block.type == "text"), None)
    try:
        return SqlAnswer.model_validate(json.loads(text or ""))
    except (json.JSONDecodeError, ValidationError) as error:
        raise AskServiceError(
            "The AI service returned an answer in an unexpected shape."
        ) from error
