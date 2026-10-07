from app.core.config import settings

PROMPT = "Please   summarise   the   following   text   for   me    thank you   very   much"


def analyze(client, h, **kw):
    body = {"prompt": PROMPT, "model": "gpt-4o-mini", **kw}
    return client.post("/api/analyze-prompt", json=body, headers=h)


def test_analyze_prompt_response_shape(client, auth):
    r = analyze(client, auth)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("original_tokens", "optimized_tokens", "tokens_saved", "reduction_percentage",
              "predicted_output_tokens", "estimated_cost", "potential_saving", "issues", "suggestions",
              "optimized_prompt"):
        assert k in d
    assert d["tokens_saved"] == d["original_tokens"] - d["optimized_tokens"] >= 0
    assert d["estimated_cost"] > 0


def test_invalid_prompt_and_model(client, auth):
    assert client.post("/api/analyze-prompt", json={"prompt": "   ", "model": "gpt-4o"}, headers=auth).status_code == 422
    assert client.post("/api/analyze-prompt", json={"prompt": "hi"}, headers=auth).status_code == 422  # missing model
    r = client.post("/api/analyze-prompt", json={"prompt": "hi", "model": "no-such-model"}, headers=auth)
    assert r.status_code == 400
    too_long = "x" * (settings.MAX_PROMPT_CHARS + 1)
    assert client.post("/api/analyze-prompt", json={"prompt": too_long, "model": "gpt-4o"}, headers=auth).status_code == 422


def test_analyze_requires_auth_and_project_access(client, auth, auth2):
    assert client.post("/api/analyze-prompt", json={"prompt": "hi", "model": "gpt-4o"}).status_code == 401
    pid = client.post("/projects", json={"name": "P"}, headers=auth).json()["id"]
    assert analyze(client, auth2, project_id=pid).status_code == 404


def test_usage_recorded_and_scoped(client, auth, auth2):
    pid = client.post("/projects", json={"name": "P"}, headers=auth).json()["id"]
    analyze(client, auth, project_id=pid)
    analyze(client, auth)
    page = client.get("/usage", headers=auth).json()
    assert page["total"] == 2
    item = page["items"][0]
    assert item["total_tokens"] == item["input_tokens"] + item["output_tokens"]
    assert client.get(f"/usage/{pid}", headers=auth).json()["total"] == 1
    assert client.get("/usage", headers=auth2).json()["total"] == 0
    assert client.get(f"/usage/{pid}", headers=auth2).status_code == 404


def test_dashboard_aggregation(client, auth):
    pid = client.post("/projects", json={"name": "P"}, headers=auth).json()["id"]
    r1, r2 = analyze(client, auth, project_id=pid).json(), analyze(client, auth, project_id=pid).json()
    ov = client.get("/dashboard/overview", headers=auth).json()
    assert ov["total_prompts"] == 2
    assert ov["total_tokens"] == 2 * (r1["original_tokens"] + r1["predicted_output_tokens"])
    assert abs(ov["total_cost"] - (r1["estimated_cost"] + r2["estimated_cost"])) < 1e-6
    assert abs(ov["total_savings"] - (r1["potential_saving"] + r2["potential_saving"])) < 1e-6
    by_model = client.get("/dashboard/cost-by-model", headers=auth).json()
    assert by_model[0]["model"] == "gpt-4o-mini" and by_model[0]["requests"] == 2
    by_project = client.get("/dashboard/cost-by-project", headers=auth).json()
    assert by_project[0]["project"] == "P"
    assert client.get("/dashboard/daily-usage", headers=auth).json()[0]["requests"] == 2
    assert client.get("/dashboard/monthly-usage", headers=auth).json()[0]["requests"] == 2
    assert len(client.get("/dashboard/recent-activity", headers=auth).json()) == 2
    assert client.get("/dashboard/project-history", headers=auth).json()[0]["project_id"] == pid
    assert len(client.get("/dashboard/forecast?days=5", headers=auth).json()["daily_forecast"]) == 5


def test_dashboard_empty(client, auth):
    ov = client.get("/dashboard/overview", headers=auth).json()
    assert ov == {"total_tokens": 0, "total_cost": 0, "total_prompts": 0, "total_savings": 0, "average_reduction": 0}


def test_rate_limit(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 2)
    assert analyze(client, auth).status_code == 200
    assert analyze(client, auth).status_code == 200
    r = analyze(client, auth)
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"


def test_nlp_failure_is_sanitised(client, auth, monkeypatch):
    from app.services import stubs

    def boom(**_):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(stubs.nlp_engine, "analyze_prompt", boom)
    r = analyze(client, auth)
    assert r.status_code == 502 and r.json()["error"]["code"] == "NLP_SERVICE_ERROR"
    assert "secret" not in r.text


def test_ml_failure_is_sanitised(client, auth, monkeypatch):
    from app.services import stubs

    def boom(**_):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(stubs.cost_engine, "estimate_cost", boom)
    r = analyze(client, auth)
    assert r.status_code == 502 and r.json()["error"]["code"] == "ML_SERVICE_ERROR"
    assert client.get("/usage", headers=auth).json()["total"] == 0  # nothing saved on failure
