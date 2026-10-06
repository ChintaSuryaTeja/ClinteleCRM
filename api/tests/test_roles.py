from tests.helpers import PASSWORD, add_user, login, signup


def test_admin_can_add_a_viewer(client):
    signup(client, "Acme", "admin@acme.com")

    viewer = add_user(client, "viewer@acme.com", "viewer")

    assert viewer["role"] == "viewer"
    emails = [user["email"] for user in client.get("/users").json()]
    assert emails == ["admin@acme.com", "viewer@acme.com"]


def test_added_user_can_log_in_with_their_role(make_client):
    admin = make_client()
    signup(admin, "Acme", "admin@acme.com")
    add_user(admin, "viewer@acme.com", "viewer")

    viewer = make_client()
    login(viewer, "viewer@acme.com")

    me = viewer.get("/auth/me").json()
    assert me["role"] == "viewer"
    assert me["organization"]["name"] == "Acme"


def test_viewer_cannot_list_users(make_client):
    admin = make_client()
    signup(admin, "Acme", "admin@acme.com")
    add_user(admin, "viewer@acme.com", "viewer")
    viewer = make_client()
    login(viewer, "viewer@acme.com")

    assert viewer.get("/users").status_code == 403


def test_viewer_cannot_add_users(make_client):
    admin = make_client()
    signup(admin, "Acme", "admin@acme.com")
    add_user(admin, "viewer@acme.com", "viewer")
    viewer = make_client()
    login(viewer, "viewer@acme.com")

    response = viewer.post(
        "/users", json={"email": "sneaky@acme.com", "password": PASSWORD, "role": "admin"}
    )

    assert response.status_code == 403


def test_unknown_role_is_rejected(client):
    signup(client, "Acme", "admin@acme.com")

    response = client.post(
        "/users", json={"email": "x@acme.com", "password": PASSWORD, "role": "owner"}
    )

    assert response.status_code == 422


def test_logged_out_user_cannot_list_users(client):
    assert client.get("/users").status_code == 401
