"""Uploading sales files, following their import jobs, and deleting them (admins only).

An upload is saved to disk and a job is queued. The worker picks it up, so a
large file never keeps the browser waiting on one long request. Deleting an
import with data also happens in the worker, for the same reason.

An order typed in by hand is turned into a one-order CSV file and imported
like any upload, so it gets the same checks and can be deleted the same way.
"""

import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy import select

from app.config import settings
from app.csv_export import csv_response
from app.deps import AdminUser, DbSession
from app.importer import (
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    SUPPORTED_SUFFIXES,
    parse_line,
    stored_file_path,
)
from app.models import ImportJob, ImportStatus, Order
from app.schemas import ImportJobOut, ManualOrderIn

router = APIRouter(prefix="/imports", tags=["imports"])

CHUNK_SIZE = 1024 * 1024


@dataclass
class JobQueue:
    run_import: Callable[[int], None]
    delete_import: Callable[[int], None]


def get_job_queue() -> JobQueue:
    """How jobs reach the worker. Tests replace this to run the jobs directly."""
    from app import worker

    return JobQueue(
        run_import=lambda job_id: worker.run_import.delay(job_id),
        delete_import=lambda job_id: worker.delete_import.delay(job_id),
    )


Queue = Annotated[JobQueue, Depends(get_job_queue)]


def get_job(db: DbSession, admin: AdminUser, job_id: int) -> ImportJob:
    job = db.scalar(
        select(ImportJob).where(
            ImportJob.id == job_id, ImportJob.organization_id == admin.organization_id
        )
    )
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import not found")
    return job


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def upload(file: UploadFile, admin: AdminUser, db: DbSession, queue: Queue) -> ImportJobOut:
    filename = Path(file.filename or "").name
    if Path(filename).suffix.lower() not in SUPPORTED_SUFFIXES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload a .csv or .xlsx file.")

    job = ImportJob(
        organization_id=admin.organization_id, created_by_user_id=admin.id, filename=filename
    )
    db.add(job)
    db.flush()  # assigns job.id, used in the stored file's name

    path = stored_file_path(settings.upload_dir, job)
    path.parent.mkdir(parents=True, exist_ok=True)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    written = 0
    with open(path, "wb") as out:
        while chunk := file.file.read(CHUNK_SIZE):
            written += len(chunk)
            if written > max_bytes:
                out.close()
                path.unlink(missing_ok=True)
                db.rollback()
                raise HTTPException(
                    status.HTTP_413_CONTENT_TOO_LARGE,
                    f"The file is larger than {settings.max_upload_mb} MB.",
                )
            out.write(chunk)

    db.commit()  # the worker must be able to see the job before it is queued
    queue.run_import(job.id)
    db.refresh(job)
    return ImportJobOut.model_validate(job)


# The form's field labels, used instead of column names in its error messages.
FIELD_LABELS = {
    "order_id": "Order ID",
    "order_date": "Order date",
    "customer_id": "Customer ID",
    "customer_name": "Customer name",
    "customer_email": "Customer email",
    "product_code": "Product code",
    "product_name": "Product name",
    "quantity": "Quantity",
    "unit_price": "Unit price",
}
PRODUCT_FIELDS = ("product_code", "product_name", "quantity", "unit_price")


def form_problems(rows: list[dict]) -> list[str]:
    """Check each product row with the importer's rules and word the problems for the form,
    e.g. 'Order date "31/12/2024" isn't a date...' or 'Product 2: Unit price "abc"...'."""
    problems: list[str] = []
    for number, row in enumerate(rows, start=1):
        result = parse_line(number, row)
        for problem in result if isinstance(result, list) else []:
            column, rest = problem.split(" ", 1)
            message = f"{FIELD_LABELS[column]} {rest}."
            if column in PRODUCT_FIELDS and len(rows) > 1:
                message = f"Product {number}: {message}"
            if message not in problems:  # order-level problems would repeat for every product
                problems.append(message)
    return problems


@router.post("/manual", status_code=status.HTTP_202_ACCEPTED)
def add_order_by_hand(
    body: ManualOrderIn, admin: AdminUser, db: DbSession, queue: Queue
) -> ImportJobOut:
    """Check the order now so mistakes show on the form, then import it as a one-order file."""
    order = {
        "order_id": body.order_id,
        "order_date": body.order_date,
        "customer_id": body.customer_id,
        "customer_name": body.customer_name,
        "customer_email": body.customer_email,
    }
    rows = [{**order, **line.model_dump()} for line in body.lines]

    problems = form_problems(rows)
    if problems:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, " ".join(problems))

    order_id = body.order_id.strip()
    exists_already = db.scalar(
        select(Order.id).where(
            Order.organization_id == admin.organization_id, Order.external_id == order_id
        )
    )
    if exists_already:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Order {order_id} already exists.")

    job = ImportJob(
        organization_id=admin.organization_id,
        created_by_user_id=admin.id,
        filename=f"manual-entry-order-{order_id}.csv",
    )
    db.add(job)
    db.flush()
    path = stored_file_path(settings.upload_dir, job)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS]
    with open(path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    db.commit()
    queue.run_import(job.id)
    db.refresh(job)
    return ImportJobOut.model_validate(job)


@router.get("")
def list_imports(admin: AdminUser, db: DbSession) -> list[ImportJobOut]:
    jobs = db.scalars(
        select(ImportJob)
        .where(ImportJob.organization_id == admin.organization_id)
        .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
        .limit(50)
    )
    return [ImportJobOut.model_validate(job) for job in jobs]


@router.get("/{job_id}")
def read_import(job: Annotated[ImportJob, Depends(get_job)]) -> ImportJobOut:
    return ImportJobOut.model_validate(job)


@router.get("/{job_id}/errors.csv")
def error_report(job: Annotated[ImportJob, Depends(get_job)]) -> Response:
    """The rejected rows as a spreadsheet: row number and what was wrong with it."""
    rows = [["row", "problem"]]
    if job.failure_reason:
        rows.append(["", job.failure_reason])
    entries = job.error_report or []
    for entry in entries:
        rows.append([entry["row"], "; ".join(entry["errors"])])
    if job.rows_rejected > len(entries):
        rows.append(["", f"...and {job.rows_rejected - len(entries)} more rejected rows"])
    return csv_response(rows, filename=f"import-{job.id}-errors.csv")


@router.delete("/{job_id}")
def delete_import(
    job: Annotated[ImportJob, Depends(get_job)], db: DbSession, queue: Queue
) -> Response:
    """Delete an import and the orders it added.

    A failed import added nothing, so it is removed straight away (204). One
    with data is marked "deleting" and the worker removes its orders (202).
    """
    if job.status in (ImportStatus.QUEUED, ImportStatus.RUNNING, ImportStatus.DELETING):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This import is still in progress. Delete it once it's done."
        )
    if job.status == ImportStatus.FAILED:
        db.delete(job)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    job.status = ImportStatus.DELETING
    db.commit()
    queue.delete_import(job.id)
    return Response(status_code=status.HTTP_202_ACCEPTED)
