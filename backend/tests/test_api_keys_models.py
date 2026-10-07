def test_api_key_lifecycle(client, auth):
    r = client.post("/api-keys", json={"name": "ci"}, headers=auth)
    assert r.status_code == 201
    created = r.json()
    assert created["key"].startswith("acp_")
    listed = client.get("/api-keys", headers=auth).json()
    assert len(listed) == 1 and "key" not in listed[0] and "key_hash" not in listed[0]

    # the key authenticates requests
    assert client.get("/auth/me", headers={"X-API-Key": created["key"]}).status_code == 200
    assert client.get("/auth/me", headers={"X-API-Key": "acp_wrong"}).status_code == 401

    assert client.delete(f"/api-keys/{created['id']}", headers=auth).status_code == 204
    assert client.get("/auth/me", headers={"X-API-Key": created["key"]}).status_code == 401


def test_cannot_delete_other_users_key(client, auth, auth2):
    kid = client.post("/api-keys", json={"name": "k"}, headers=auth).json()["id"]
    assert client.delete(f"/api-keys/{kid}", headers=auth2).status_code == 404


def test_models_and_pricing(client, auth):
    models = client.get("/models", headers=auth).json()
    assert len(models) >= 1 and models[0]["pricing"]["input_price_per_1k"] > 0
    pricing = client.get("/models/pricing", headers=auth).json()
    assert isinstance(pricing, list) and pricing[0]["currency"] == "USD"
    assert client.get(f"/models/{models[0]['id']}", headers=auth).json()["name"] == models[0]["name"]
    assert client.get("/models/99999", headers=auth).status_code == 404
