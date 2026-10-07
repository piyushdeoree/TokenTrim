from tests.conftest import register_and_login


def mk_team(client, h, name="T"):
    return client.post("/teams", json={"name": name}, headers=h).json()["id"]


def test_team_lifecycle_and_roles(client, auth, auth2):
    tid = mk_team(client, auth)
    assert client.get("/teams", headers=auth).json()[0]["my_role"] == "owner"

    r = client.post(f"/teams/{tid}/members", json={"email": "b@example.com", "role": "member"}, headers=auth)
    assert r.status_code == 201 and r.json()["role"] == "member"
    assert client.post(f"/teams/{tid}/members", json={"email": "b@example.com"}, headers=auth).status_code == 409
    assert client.post(f"/teams/{tid}/members", json={"email": "ghost@example.com"}, headers=auth).status_code == 404
    assert len(client.get(f"/teams/{tid}/members", headers=auth2).json()) == 2


def test_member_permissions(client, auth, auth2):
    tid = mk_team(client, auth)
    client.post(f"/teams/{tid}/members", json={"email": "b@example.com"}, headers=auth)
    carol = register_and_login(client, "c@example.com", name="Carol")
    # plain member cannot invite, cannot delete team, cannot change roles
    assert client.post(f"/teams/{tid}/members", json={"email": "c@example.com"}, headers=auth2).status_code == 403
    assert client.delete(f"/teams/{tid}", headers=auth2).status_code == 403
    owner_id = client.get("/auth/me", headers=auth).json()["id"]
    bob_id = client.get("/auth/me", headers=auth2).json()["id"]
    assert client.patch(f"/teams/{tid}/members/{bob_id}", json={"role": "admin"}, headers=auth2).status_code == 403
    # non-members can't even see the team
    assert client.get(f"/teams/{tid}", headers=carol).status_code == 404
    # owner can't be removed
    assert client.delete(f"/teams/{tid}/members/{owner_id}", headers=auth2).status_code == 400


def test_admin_rules(client, auth, auth2):
    tid = mk_team(client, auth)
    client.post(f"/teams/{tid}/members", json={"email": "b@example.com", "role": "admin"}, headers=auth)
    carol = register_and_login(client, "c@example.com", name="Carol")
    # admin can add members but not admins
    assert client.post(f"/teams/{tid}/members", json={"email": "c@example.com", "role": "admin"}, headers=auth2).status_code == 403
    assert client.post(f"/teams/{tid}/members", json={"email": "c@example.com", "role": "member"}, headers=auth2).status_code == 201
    carol_id = client.get("/auth/me", headers=carol).json()["id"]
    assert client.delete(f"/teams/{tid}/members/{carol_id}", headers=auth2).status_code == 204


def test_member_can_leave_and_owner_can_delete(client, auth, auth2):
    tid = mk_team(client, auth)
    client.post(f"/teams/{tid}/members", json={"email": "b@example.com"}, headers=auth)
    bob_id = client.get("/auth/me", headers=auth2).json()["id"]
    assert client.delete(f"/teams/{tid}/members/{bob_id}", headers=auth2).status_code == 204
    assert client.delete(f"/teams/{tid}", headers=auth).status_code == 204


def test_team_project_access(client, auth, auth2):
    tid = mk_team(client, auth)
    client.post(f"/teams/{tid}/members", json={"email": "b@example.com"}, headers=auth)
    pid = client.post("/projects", json={"name": "Shared", "team_id": tid}, headers=auth).json()["id"]
    assert client.get(f"/projects/{pid}", headers=auth2).status_code == 200      # member can read
    assert client.put(f"/projects/{pid}", json={"name": "x"}, headers=auth2).status_code == 403  # but not modify
    # outsiders can't attach projects to a team they're not in
    assert client.post("/projects", json={"name": "Sneaky", "team_id": tid},
                       headers=register_and_login(client, "z@example.com", name="Z")).status_code == 403
    # team usage is visible to members
    client.post("/api/analyze-prompt", json={"prompt": "hello world", "model": "gpt-4o", "project_id": pid}, headers=auth2)
    assert client.get(f"/usage/{pid}", headers=auth).json()["total"] == 1
