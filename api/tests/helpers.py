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
