"""Builds CSV downloads."""

import csv
import io
from collections.abc import Iterable

from fastapi import Response

# A cell starting with one of these is run as a formula by Excel and Google
# Sheets. Customer names come from uploaded files, so a name like
# "=HYPERLINK(...)" could do harm when someone opens the export.
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def _safe(value: object) -> object:
    if isinstance(value, str) and value.startswith(FORMULA_STARTS):
        return "'" + value  # the apostrophe makes spreadsheets show it as plain text
    return value


def csv_response(rows: Iterable[Iterable[object]], filename: str) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow([_safe(value) for value in row])
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
