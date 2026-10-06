"""Running SQL written by an LLM, safely.

Three independent layers, so that one mistake is not enough to leak or damage data:

1. Checking (validate_sql): the query is parsed, not pattern-matched. It must be
   exactly one SELECT, read only the four tables below, and call only
   functions on an allowlist. Anything else is refused before it runs.

2. A restricted database role (crm_ask, created in migration 0006): it can
   read the views in the "ask" schema and nothing else. Even a query that got
   past the checks could not touch the real tables or change anything.

3. The views themselves show only the current organization's rows. The
   organization is set for the transaction by the API, and the function a
   query would need to change it (set_config) is not on the allowlist.

On top: the transaction is read-only, has a time limit, and at most
ROW_LIMIT rows are returned.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

import psycopg
import sqlglot
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlglot import exp

# The tables the LLM is told about. They are views in the "ask" schema.
ALLOWED_TABLES = {"customers", "orders", "order_items", "daily_revenue"}

# sqlglot's names for the functions a sales question can need. Everything
# else (pg_sleep, set_config, current_setting, dblink, lo_import...) is refused.
ALLOWED_FUNCTIONS = {
    # aggregates
    "Count",
    "Sum",
    "Avg",
    "Min",
    "Max",
    "Stddev",
    "StddevSamp",
    "StddevPop",
    "Variance",
    "PercentileCont",
    "PercentileDisc",
    "Median",
    "GroupConcat",
    "ArrayAgg",
    # window functions
    "RowNumber",
    "Rank",
    "DenseRank",
    "Ntile",
    "PercentRank",
    "CumeDist",
    "Lag",
    "Lead",
    "FirstValue",
    "LastValue",
    # dates
    "DateTrunc",
    "TimestampTrunc",
    "Extract",
    "CurrentDate",
    "CurrentTimestamp",
    "TimeToStr",
    "DateDiff",
    "DateAdd",
    "DateSub",
    "StrToDate",
    "TsOrDsToDate",
    # numbers
    "Round",
    "Abs",
    "Ceil",
    "Floor",
    "Sqrt",
    "Ln",
    "Log",
    "Exp",
    "Pow",
    "Greatest",
    "Least",
    "SafeDivide",
    # text
    "Lower",
    "Upper",
    "Length",
    "Concat",
    "ConcatWs",
    "Substring",
    "Trim",
    "Initcap",
    "StrPosition",
    "SplitPart",
    # logic and types
    "Coalesce",
    "Nullif",
    "Case",
    "If",
    "Cast",
    "TryCast",
}
# Functions sqlglot doesn't model, by their SQL name.
ALLOWED_PLAIN_FUNCTIONS = {"age", "date_part", "make_date", "to_date", "to_char"}

# Statement types that write or change anything, anywhere in the query
# (including inside a WITH clause).
FORBIDDEN_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop, exp.Alter,
    exp.Command, exp.Copy, exp.Into, exp.Lock, exp.Set, exp.Use, exp.Transaction,
)  # fmt: skip

ROW_LIMIT = 1000
TIMEOUT_SECONDS = 5


class UnsafeQuery(Exception):
    """The query was refused before running. The message says why."""


class QueryFailed(Exception):
    """The database rejected or stopped the query. The message is the database's reason."""

    @property
    def timed_out(self) -> bool:
        return "statement timeout" in str(self)


def validate_sql(sql: str) -> str:
    """Return the query if it is safe to run, or raise UnsafeQuery."""
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except sqlglot.errors.ParseError:
        raise UnsafeQuery("The query isn't valid SQL.") from None
    if len(statements) != 1:
        raise UnsafeQuery("Only a single query is allowed.")
    tree = statements[0]

    if not isinstance(tree, exp.Select | exp.Union | exp.Intersect | exp.Except):
        raise UnsafeQuery("Only SELECT queries are allowed.")
    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise UnsafeQuery("Only reading data is allowed.")

    # Names defined in the query's own WITH clauses may be used like tables.
    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if table.db or table.catalog:
            raise UnsafeQuery(f'"{table.sql()}": tables can\'t be prefixed with a schema.')
        if name not in ALLOWED_TABLES and name not in cte_names:
            raise UnsafeQuery(
                f'"{table.sql() or "that table"}" isn\'t one of the tables you can ask about.'
            )

    for function in tree.find_all(exp.Func):
        # sqlglot also files AND, OR and EXISTS under functions; they're operators.
        if isinstance(function, exp.Connector | exp.Predicate | exp.Binary | exp.Unary):
            continue
        if isinstance(function, exp.Anonymous):
            if function.name.lower() not in ALLOWED_PLAIN_FUNCTIONS:
                raise UnsafeQuery(f'The function "{function.name}" isn\'t allowed.')
        elif type(function).__name__ not in ALLOWED_FUNCTIONS:
            raise UnsafeQuery(f'The function "{function.sql_name()}" isn\'t allowed.')
    return sql


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list]
    truncated: bool


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def run_select(connection: Connection, organization_id: int, sql: str) -> QueryResult:
    """Run an already-validated query as the restricted role, scoped to one organization.

    Everything happens inside a savepoint that is rolled back at the end, which
    also undoes the role and settings, so the connection is left as it was.
    """
    savepoint = connection.begin_nested()
    try:
        # set_config(..., true) only lasts until the end of this transaction.
        connection.execute(
            text("SELECT set_config('crm.organization_id', :org, true)"),
            {"org": str(organization_id)},
        )
        connection.execute(text(f"SET LOCAL statement_timeout = '{TIMEOUT_SECONDS}s'"))
        connection.execute(text("SET LOCAL search_path = ask"))
        connection.execute(text("SET LOCAL ROLE crm_ask"))
        # Run it on the driver's own cursor with no parameters, so characters
        # like "%" (LIKE '%a%') or ":" in the query are passed through untouched.
        # It is the same connection, so the role and settings above apply.
        try:
            with connection.connection.cursor() as cursor:
                cursor.execute(sql)
                columns = [column.name for column in cursor.description or []]
                fetched = cursor.fetchmany(ROW_LIMIT + 1)
        except psycopg.Error as error:
            raise QueryFailed(str(error).splitlines()[0]) from error
        rows = [[_json_safe(value) for value in row] for row in fetched[:ROW_LIMIT]]
        return QueryResult(columns=columns, rows=rows, truncated=len(fetched) > ROW_LIMIT)
    finally:
        savepoint.rollback()


def run_question_query(engine, organization_id: int, sql: str) -> QueryResult:
    """Production entry point: a fresh read-only transaction on its own connection."""
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            return run_select(connection, organization_id, sql)
