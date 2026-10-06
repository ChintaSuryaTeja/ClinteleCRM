import io
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import func, select

from app.config import settings
from app.models import Customer, Order, OrderItem
from tests.helpers import ORDER_COLUMNS, SAMPLE_ORDERS, add_user, login, signup, upload


def test_csv_import_creates_customers_orders_and_items(client, db):
    signup(client, "Acme", "admin@acme.com")

    job = upload(client, SAMPLE_ORDERS)

    assert job["status"] == "succeeded"
    assert (job["rows_imported"], job["rows_rejected"], job["rows_skipped"]) == (6, 0, 0)
    assert db.scalar(select(func.count()).select_from(Customer)) == 3
    assert db.scalar(select(func.count()).select_from(Order)) == 5
    assert db.scalar(select(func.count()).select_from(OrderItem)) == 6
    o2 = db.scalar(select(Order).where(Order.external_id == "O2"))
    assert str(o2.total_amount) == "35.50"  # two lines: 30.00 + 5.50


def test_bad_rows_are_reported_and_good_rows_still_import(client):
    signup(client, "Acme", "admin@acme.com")
    csv = f"""{ORDER_COLUMNS}
O1,2024-01-05,C1,Ada,P1,1,10.00
O2,2024-01-05,,Ada,P1,1,10.00
O3,05/01/2024,C1,Ada,P1,1,10.00
O4,2024-01-05,C1,Ada,P1,0,10.00
O5,2024-01-05,C1,Ada,P1,1.5,10.00
O6,2024-01-05,C1,Ada,P1,1,-2
O7,2024-01-05,C1,Ada,P1,1,abc
"""
    job = upload(client, csv)

    assert job["status"] == "succeeded"
    assert job["rows_imported"] == 1
    assert job["rows_rejected"] == 6

    report = client.get(f"/imports/{job['id']}/errors.csv").text.splitlines()
    assert report[0] == "row,problem"
    assert report[1] == "3,customer_id is empty"
    assert report[2].startswith('4,"order_date ""05/01/2024"" isn\'t a date')
    assert report[3] == '5,"quantity ""0"" must be a positive whole number"'
    assert report[4] == '6,"quantity ""1.5"" must be a positive whole number"'
    assert report[5] == '7,"unit_price ""-2"" must be zero or more"'
    assert report[6] == '8,"unit_price ""abc"" isn\'t a number"'


def test_uploading_the_same_file_twice_skips_known_orders(client):
    signup(client, "Acme", "admin@acme.com")
    upload(client, SAMPLE_ORDERS)

    second = upload(client, SAMPLE_ORDERS)

    assert (second["rows_imported"], second["rows_skipped"]) == (0, 6)
    assert client.get("/dashboard").json()["revenue"] == 140.50  # not doubled


def test_lines_of_one_order_must_agree(client):
    signup(client, "Acme", "admin@acme.com")
    csv = f"""{ORDER_COLUMNS}
O1,2024-01-05,C1,Ada,P1,1,10.00
O1,2024-01-06,C1,Ada,P2,1,10.00
O1,2024-01-05,C2,Ben,P3,1,10.00
"""
    job = upload(client, csv)

    assert (job["rows_imported"], job["rows_rejected"]) == (1, 2)
    report = client.get(f"/imports/{job['id']}/errors.csv").text
    assert "order O1 has a different order_date or customer_id on row 2" in report


def test_existing_customer_gets_new_details_but_blank_cells_keep_old_ones(client, db):
    signup(client, "Acme", "admin@acme.com")
    columns = ORDER_COLUMNS.replace("customer_name", "customer_name,customer_email")
    upload(client, f"{columns}\nO1,2024-01-05,C1,Ada,ada@old.com,P1,1,10\n")
    upload(client, f"{columns}\nO2,2024-02-05,C1,Ada Lovelace,,P1,1,10\n")

    ada = db.scalar(select(Customer).where(Customer.external_id == "C1"))
    db.refresh(ada)
    assert ada.name == "Ada Lovelace"
    assert ada.email == "ada@old.com"


def test_excel_import(client, db):
    signup(client, "Acme", "admin@acme.com")
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        ["Order ID", "Order Date", "Customer ID", "Product Code", "Quantity", "Unit Price"]
    )
    # Excel stores the customer number as a float and the date as a real date.
    sheet.append(["536365", datetime(2010, 12, 1, 8, 26), 17850.0, "85123A", 6, 2.55])
    buffer = io.BytesIO()
    workbook.save(buffer)

    job = upload(client, buffer.getvalue(), filename="orders.xlsx")

    assert job["status"] == "succeeded", job
    assert job["rows_imported"] == 1
    assert db.scalar(select(Customer.external_id)) == "17850"
    assert str(db.scalar(select(Order.total_amount))) == "15.30"  # 6 x 2.55


def test_missing_column_fails_the_whole_file(client):
    signup(client, "Acme", "admin@acme.com")

    job = upload(client, "order_id,order_date,customer_id\nO1,2024-01-05,C1\n")

    assert job["status"] == "failed"
    assert job["failure_reason"] == (
        "The file is missing required columns: product_code, quantity, unit_price."
    )


def test_non_utf8_file_fails_with_a_clear_reason(client):
    signup(client, "Acme", "admin@acme.com")
    content = f"{ORDER_COLUMNS}\nO1,2024-01-05,C1,Zoë,P1,1,10\n".encode("latin-1")

    job = upload(client, content)

    assert job["status"] == "failed"
    assert "isn't UTF-8" in job["failure_reason"]


def test_unsupported_file_type_is_refused(client):
    signup(client, "Acme", "admin@acme.com")

    response = client.post("/imports", files={"file": ("orders.pdf", b"%PDF", "application/pdf")})

    assert response.status_code == 400


def test_too_large_file_is_refused(client, monkeypatch, upload_dir):
    signup(client, "Acme", "admin@acme.com")
    monkeypatch.setattr(settings, "max_upload_mb", 0)

    response = client.post("/imports", files={"file": ("orders.csv", SAMPLE_ORDERS, "text/csv")})

    assert response.status_code == 413
    assert client.get("/imports").json() == []
    assert not any(Path(upload_dir).glob("*"))


def test_uploaded_file_is_deleted_after_processing(client, upload_dir):
    signup(client, "Acme", "admin@acme.com")

    upload(client, SAMPLE_ORDERS)

    assert not any(Path(upload_dir).glob("*"))


def test_import_list_shows_newest_first(client):
    signup(client, "Acme", "admin@acme.com")
    first = upload(client, SAMPLE_ORDERS, filename="january.csv")
    second = upload(client, SAMPLE_ORDERS, filename="again.csv")

    jobs = client.get("/imports").json()

    assert [job["id"] for job in jobs] == [second["id"], first["id"]]
    assert client.get(f"/imports/{first['id']}").json()["filename"] == "january.csv"


def test_viewer_cannot_upload_or_see_imports(make_client):
    admin = make_client()
    signup(admin, "Acme", "admin@acme.com")
    job = upload(admin, SAMPLE_ORDERS)
    add_user(admin, "viewer@acme.com", "viewer")
    viewer = make_client()
    login(viewer, "viewer@acme.com")

    upload_response = viewer.post(
        "/imports", files={"file": ("orders.csv", SAMPLE_ORDERS, "text/csv")}
    )

    assert upload_response.status_code == 403
    assert viewer.get("/imports").status_code == 403
    assert viewer.get(f"/imports/{job['id']}/errors.csv").status_code == 403


def test_viewer_can_read_dashboard_and_customers(make_client):
    admin = make_client()
    signup(admin, "Acme", "admin@acme.com")
    upload(admin, SAMPLE_ORDERS)
    add_user(admin, "viewer@acme.com", "viewer")
    viewer = make_client()
    login(viewer, "viewer@acme.com")

    assert viewer.get("/dashboard").json()["revenue"] == 140.50
    assert viewer.get("/customers").json()["total"] == 3
    assert viewer.get("/customers/export.csv").status_code == 200
