import pytest

from tests.conftest import analyze


@pytest.fixture
def three_runs(client, auth, project):
    out = [analyze(client, auth, project_id=project["id"], model=m).json()
           for m in ("gpt-4o-mini", "gpt-4o-mini", "claude-haiku")]
    return out


def test_usage_recorded(client, auth, project, three_runs):
    rows = client.get("/usage", headers=auth).json()
    assert len(rows) == 3
    first = rows[-1]  # newest first
    assert set(first) >= {"timestamp", "model", "input_tokens", "output_tokens", "total_tokens", "estimated_cost",
                          "project_id", "user_id", "team_id"}
    assert first["total_tokens"] == first["input_tokens"] + first["output_tokens"]
    assert first["project_id"] == project["id"]
    assert len(client.get(f"/usage/{project['id']}", headers=auth).json()) == 3
    assert len(client.get("/usage?limit=2", headers=auth).json()) == 2


def test_usage_is_scoped_to_user(client, auth, project, three_runs, make_user):
    eve = make_user("eve@example.com", "Eve")
    assert client.get("/usage", headers=eve).json() == []
    assert client.get(f"/usage/{project['id']}", headers=eve).status_code == 404
    assert client.get("/usage").status_code == 401


def test_dashboard_overview_aggregation(client, auth, three_runs):
    o = client.get("/dashboard/overview", headers=auth).json()
    assert set(o) == {"total_tokens", "total_cost", "total_prompts", "total_savings", "average_reduction"}
    assert o["total_prompts"] == 3
    assert o["total_tokens"] == sum(r["original_tokens"] + r["predicted_output_tokens"] for r in three_runs)
    assert o["total_cost"] == pytest.approx(sum(r["estimated_cost"] for r in three_runs), rel=1e-6)
    assert o["total_savings"] == pytest.approx(sum(r["potential_saving"] for r in three_runs), rel=1e-6)
    assert o["average_reduction"] == pytest.approx(sum(r["reduction_percentage"] for r in three_runs) / 3, abs=0.01)


def test_dashboard_empty_state(client, auth):
    assert client.get("/dashboard/overview", headers=auth).json() == {
        "total_tokens": 0, "total_cost": 0.0, "total_prompts": 0, "total_savings": 0.0, "average_reduction": 0.0}


def test_dashboard_breakdowns(client, auth, project, three_runs):
    daily = client.get("/dashboard/daily-usage", headers=auth).json()
    assert len(daily) == 1 and daily[0]["prompts"] == 3
    monthly = client.get("/dashboard/monthly-usage", headers=auth).json()
    assert len(monthly) == 1 and monthly[0]["prompts"] == 3 and len(monthly[0]["period"]) == 7
    by_model = {m["model"]: m for m in client.get("/dashboard/cost-by-model", headers=auth).json()}
    assert by_model["gpt-4o-mini"]["prompts"] == 2 and by_model["claude-haiku"]["prompts"] == 1
    by_project = client.get("/dashboard/cost-by-project", headers=auth).json()
    assert by_project[0]["project_id"] == project["id"] and by_project[0]["prompts"] == 3
    recent = client.get("/dashboard/recent-activity?limit=2", headers=auth).json()
    assert len(recent) == 2 and recent[0]["project_name"] == "Chatbot"
    hist = client.get("/dashboard/project-history", headers=auth).json()
    assert hist[0]["prompts"] == 3 and hist[0]["last_activity"] is not None


def test_dashboard_is_scoped_to_user(client, three_runs, make_user):
    eve = make_user("eve@example.com", "Eve")
    assert client.get("/dashboard/overview", headers=eve).json()["total_prompts"] == 0
    assert client.get("/dashboard/cost-by-model", headers=eve).json() == []


def test_team_members_see_team_project_usage(client, make_user):
    owner, member = make_user("o@example.com", "O"), make_user("m@example.com", "M")
    team = client.post("/teams", json={"name": "T"}, headers=owner).json()
    client.post(f"/teams/{team['id']}/members", json={"email": "m@example.com"}, headers=owner)
    pid = client.post("/projects", json={"name": "Shared", "team_id": team["id"]}, headers=owner).json()["id"]
    analyze(client, owner, project_id=pid)
    assert client.get("/dashboard/overview", headers=member).json()["total_prompts"] == 1
    assert client.get(f"/usage/{pid}", headers=member).json()[0]["team_id"] == team["id"]


def test_forecast(client, auth, three_runs):
    r = client.get("/dashboard/forecast?days=7", headers=auth).json()
    assert r["horizon_days"] == 7 and len(r["daily"]) == 7 and r["total_forecast_cost"] >= 0
    assert client.get("/dashboard/forecast?days=0", headers=auth).status_code == 422


def test_models_and_pricing(client, auth):
    models = client.get("/models", headers=auth).json()
    assert {"gpt-4o", "claude-haiku"} <= {m["name"] for m in models} and all(m["pricing"] for m in models)
    pricing = client.get("/models/pricing", headers=auth).json()
    assert len(pricing) == len(models) and "input_price_per_1k" in pricing[0]
    one = client.get(f"/models/{models[0]['id']}", headers=auth).json()
    assert one["name"] == models[0]["name"]
    assert client.get("/models/9999", headers=auth).status_code == 404
    assert client.get("/models").status_code == 401
