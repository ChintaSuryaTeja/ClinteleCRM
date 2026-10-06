from app.deps import SESSION_COOKIE
from tests.helpers import PASSWORD, login, signup


def test_signup_creates_organization_and_admin(client):
    body = signup(client, "Acme Ltd", "Owner@Acme.com")

    assert body["email"] == "owner@acme.com"  # stored lowercased
    assert body["role"] == "admin"
    assert body["organization"]["name"] == "Acme Ltd"


def test_signup_sets_an_httponly_cookie(client):
    response = client.post(
        "/auth/signup",
        json={"organization_name": "Acme", "email": "a@acme.com", "password": PASSWORD},
    )
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_me_returns_logged_in_user(client):
    signup(client, "Acme", "a@acme.com")

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "a@acme.com"


def test_signup_rejects_duplicate_email(make_client):
    signup(make_client(), "Acme", "a@acme.com")

    response = make_client().post(
        "/auth/signup",
        json={"organization_name": "Other", "email": "A@acme.com", "password": PASSWORD},
    )

    assert response.status_code == 409


def test_signup_rejects_short_password(client):
    response = client.post(
        "/auth/signup",
        json={"organization_name": "Acme", "email": "a@acme.com", "password": "short"},
    )
    assert response.status_code == 422


def test_login_with_correct_password(make_client):
    signup(make_client(), "Acme", "a@acme.com")
    client = make_client()

    login(client, "A@ACME.com")

    assert client.get("/auth/me").json()["email"] == "a@acme.com"


def test_login_with_wrong_password_fails(make_client):
    signup(make_client(), "Acme", "a@acme.com")

    response = make_client().post(
        "/auth/login", json={"email": "a@acme.com", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_with_unknown_email_gives_same_error(client):
    response = client.post("/auth/login", json={"email": "nobody@acme.com", "password": PASSWORD})

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_me_without_login_is_rejected(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_forged_token_is_rejected(client):
    client.cookies.set(SESSION_COOKIE, "not-a-real-token")
    assert client.get("/auth/me").status_code == 401


def test_logout_ends_session(client):
    signup(client, "Acme", "a@acme.com")

    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401
