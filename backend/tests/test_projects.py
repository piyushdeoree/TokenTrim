def test_project_crud(client, auth):
    r = client.post("/projects", json={"name": "P1", "description": "d"}, headers=auth)
    assert r.status_code == 201
    pid = r.json()["id"]
    assert len(client.get("/projects", headers=auth).json()) == 1
    assert client.get(f"/projects/{pid}", headers=auth).json()["name"] == "P1"
    r = client.put(f"/projects/{pid}", json={"name": "P1b"}, headers=auth)
    assert r.status_code == 200 and r.json()["name"] == "P1b" and r.json()["description"] == "d"
    assert client.delete(f"/projects/{pid}", headers=auth).status_code == 204
    assert client.get(f"/projects/{pid}", headers=auth).status_code == 404


def test_duplicate_project_name(client, auth):
    client.post("/projects", json={"name": "P"}, headers=auth)
    assert client.post("/projects", json={"name": "P"}, headers=auth).status_code == 409


def test_projects_are_private(client, auth, auth2):
    pid = client.post("/projects", json={"name": "Mine"}, headers=auth).json()["id"]
    assert client.get(f"/projects/{pid}", headers=auth2).status_code == 404
    assert client.delete(f"/projects/{pid}", headers=auth2).status_code == 404
    assert client.get("/projects", headers=auth2).json() == []


def test_invalid_project_id(client, auth):
    assert client.get("/projects/9999", headers=auth).status_code == 404
    assert client.get("/projects/abc", headers=auth).status_code == 422
