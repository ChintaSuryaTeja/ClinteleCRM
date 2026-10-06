from fastapi.testclient import TestClient

PASSWORD = "correct-horse-battery"


def signup(client: TestClient, organization: str, email: str) -> dict:
    """Create an organization and log this client in as its admin."""
    response = client.post(
        "/auth/signup",
        json={"organization_name": organization, "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str, password: str = PASSWORD) -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def add_user(admin_client: TestClient, email: str, role: str) -> dict:
    response = admin_client.post(
        "/users", json={"email": email, "password": PASSWORD, "role": role}
    )
    assert response.status_code == 201, response.text
    return response.json()


ORDER_COLUMNS = "order_id,order_date,customer_id,customer_name,product_code,quantity,unit_price"

# Hand-made customers with known answers (see test_metrics.py):
#   Ada (C1): 2 orders in January, 20.00 + 35.50 = 55.50
#   Ben (C2): 1 order in February, 75.00
#   Cy  (C3): 2 orders on 1 March, 9.99 + 0.01 = 10.00
# All together: 140.50 revenue from 5 orders.
SAMPLE_ORDERS = f"""{ORDER_COLUMNS}
O1,2024-01-05,C1,Ada,P-RED,2,10.00
O2,2024-01-20,C1,Ada,P-BLUE,1,30.00
O2,2024-01-20,C1,Ada,P-PIN,1,5.50
O3,2024-02-10,C2,Ben,P-RED,3,25.00
O4,2024-03-01 09:00,C3,Cy,P-PIN,1,9.99
O5,2024-03-01 17:30,C3,Cy,P-CAP,1,0.01
"""


def upload(client: TestClient, content: str | bytes, filename: str = "orders.csv") -> dict:
    """Upload a file. In tests the import runs immediately, so the job comes back finished."""
    if isinstance(content, str):
        content = content.encode()
    response = client.post("/imports", files={"file": (filename, content, "text/csv")})
    assert response.status_code == 202, response.text
    return response.json()


def orders_csv(orders: list[tuple[str, str, str, str]]) -> str:
    """Build an upload from (order_id, date, customer_id, amount) tuples, one product each."""
    lines = [ORDER_COLUMNS]
    for order_id, day, customer, amount in orders:
        lines.append(f"{order_id},{day},{customer},{customer},P,1,{amount}")
    return "\n".join(lines) + "\n"
