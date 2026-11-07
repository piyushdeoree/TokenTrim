from tests.conftest import register_and_login


def test_register_login_me(client):
    h = register_and_login(client)
    r = client.get("/auth/me", headers=h)
    assert r.status_code == 200 and r.json()["email"] == "a@example.com"
    assert "hashed_password" not in r.json()


def test_duplicate_registration(client, auth):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "password123", "full_name": "X"})
    assert r.status_code == 409


def test_wrong_password(client, auth):
    r = client.post("/auth/login", json={"email": "a@example.com", "password": "wrong-password"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"


def test_weak_or_invalid_registration(client):
    r = client.post("/auth/register", json={"email": "not-an-email", "password": "short", "full_name": ""})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unauthorized_requests(client):
    assert client.get("/projects").status_code == 401
    assert client.get("/projects", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get("/dashboard/overview").status_code == 401


def test_logout_revokes_token(client, auth):
    assert client.post("/auth/logout", headers=auth).status_code == 204
    assert client.get("/auth/me", headers=auth).status_code == 401
