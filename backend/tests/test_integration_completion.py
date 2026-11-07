def test_history_profile_and_project_assignment(client, auth, auth2):
    project = client.post("/projects", json={"name": "History"}, headers=auth).json()
    result = client.post("/api/analyze-prompt", json={"prompt": "Please summarize this useful text", "model": "gpt-4o-mini"}, headers=auth)
    assert result.status_code == 200, result.text
    prompt_id = result.json()["prompt_id"]
    assert client.get("/history", headers=auth).json()[0]["id"] == prompt_id
    assert client.get(f"/history/{prompt_id}", headers=auth2).status_code == 404
    linked = client.patch(f"/history/{prompt_id}/project", json={"project_id": project["id"]}, headers=auth)
    assert linked.status_code == 200 and linked.json()["project_id"] == project["id"]
    profile = client.patch("/auth/me", json={"full_name": "Alice Updated"}, headers=auth)
    assert profile.status_code == 200 and profile.json()["full_name"] == "Alice Updated"
    assert client.get("/auth/me", headers=auth).json()["full_name"] == "Alice Updated"


def test_invitation_token_lifecycle(client, auth, auth2):
    team = client.post("/teams", json={"name": "Invite team"}, headers=auth).json()
    created = client.post(f"/teams/{team['id']}/invitations", json={"email": "b@example.com", "role": "member"}, headers=auth)
    assert created.status_code == 201, created.text
    invite = created.json()
    assert invite["delivery"] == "not_sent" and invite["expires_at"] and invite["token"]
    listed = client.get(f"/teams/{team['id']}/invitations", headers=auth).json()
    assert len(listed) == 1 and "token" not in listed[0] and "token_hash" not in listed[0]
    accepted = client.post("/teams/invitations/accept", json={"token": invite["token"]}, headers=auth2)
    assert accepted.status_code == 200, accepted.text
    assert len(client.get(f"/teams/{team['id']}/members", headers=auth).json()) == 2
    assert client.post("/teams/invitations/accept", json={"token": invite["token"]}, headers=auth2).status_code == 404


def test_invitation_can_be_revoked(client, auth):
    team = client.post("/teams", json={"name": "Revocation"}, headers=auth).json()
    invite = client.post(f"/teams/{team['id']}/invitations", json={"email": "new@example.com"}, headers=auth).json()
    assert client.delete(f"/teams/{team['id']}/invitations/{invite['id']}", headers=auth).status_code == 204
    assert client.post("/teams/invitations/accept", json={"token": invite["token"]}, headers=auth).status_code == 404
