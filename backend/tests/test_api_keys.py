from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import ApiKey


def test_create_list_delete(client, auth):
    c = client.post("/api-keys", json={"name": "ci"}, headers=auth)
    assert c.status_code == 201
    created = c.json()
    assert created["secret"].startswith("acp_") and created["prefix"] == created["secret"][:10]
    listed = client.get("/api-keys", headers=auth).json()
    assert len(listed) == 1 and "secret" not in listed[0] and "key_hash" not in listed[0]
    assert client.delete(f"/api-keys/{created['id']}", headers=auth).status_code == 204
    assert client.get("/api-keys", headers=auth).json() == []


def test_only_hash_is_stored(client, auth):
    secret = client.post("/api-keys", json={"name": "ci"}, headers=auth).json()["secret"]
    with SessionLocal() as db:
        k = db.scalar(select(ApiKey))
        assert secret not in (k.key_hash, k.prefix) and len(k.key_hash) == 64


def test_key_authenticates_then_stops_after_delete(client, auth):
    created = client.post("/api-keys", json={"name": "ci"}, headers=auth).json()
    h = {"X-API-Key": created["secret"]}
    assert client.get("/auth/me", headers=h).status_code == 200
    assert client.get("/api-keys", headers=auth).json()[0]["last_used_at"] is not None
    client.delete(f"/api-keys/{created['id']}", headers=auth)
    assert client.get("/auth/me", headers=h).status_code == 401


def test_keys_are_private_and_cannot_manage_keys(client, auth, make_user):
    created = client.post("/api-keys", json={"name": "ci"}, headers=auth).json()
    eve = make_user("eve@example.com", "Eve")
    assert client.get("/api-keys", headers=eve).json() == []
    assert client.delete(f"/api-keys/{created['id']}", headers=eve).status_code == 404
    # an API key must not be able to mint more API keys
    assert client.post("/api-keys", json={"name": "x"}, headers={"X-API-Key": created["secret"]}).status_code == 401


def test_api_keys_unauthorized_and_invalid(client, auth):
    assert client.get("/api-keys").status_code == 401
    assert client.post("/api-keys", json={"name": ""}, headers=auth).status_code == 422
