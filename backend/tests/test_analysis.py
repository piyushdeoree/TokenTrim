import sys
import types

import pytest

from tests.conftest import PROMPT, analyze

KEYS = {"original_tokens", "optimized_tokens", "tokens_saved", "reduction_percentage", "predicted_output_tokens",
        "estimated_cost", "potential_saving", "issues", "suggestions", "optimized_prompt"}


def test_analyze_success_shape_and_math(client, auth, project):
    r = analyze(client, auth, project_id=project["id"])
    assert r.status_code == 200, r.text
    b = r.json()
    assert set(b) == KEYS
    assert b["tokens_saved"] == b["original_tokens"] - b["optimized_tokens"] > 0
    assert b["reduction_percentage"] == pytest.approx(b["tokens_saved"] / b["original_tokens"] * 100, abs=0.01)
    # gpt-4o-mini seed pricing: 0.00015 in / 0.0006 out per 1k tokens
    expected = b["original_tokens"] / 1000 * 0.00015 + b["predicted_output_tokens"] / 1000 * 0.0006
    assert b["estimated_cost"] == pytest.approx(expected, rel=1e-4)
    assert 0 < b["potential_saving"] < b["estimated_cost"]
    assert "please" not in b["optimized_prompt"].lower()


def test_analyze_without_project_is_allowed(client, auth):
    assert analyze(client, auth).status_code == 200


@pytest.mark.parametrize("body,code", [
    ({"prompt": "   ", "model": "gpt-4o"}, 422),
    ({"prompt": "", "model": "gpt-4o"}, 422),
    ({"prompt": "hello"}, 422),                       # missing model
    ({"prompt": "hello", "model": ""}, 422),
    ({"model": "gpt-4o"}, 422),                       # missing prompt
    ({"prompt": "x" * 20001, "model": "gpt-4o"}, 422),
    ({"prompt": "hello", "model": "no-such-model"}, 404),
    ({"prompt": "hello", "model": "gpt-4o", "project_id": 9999}, 404),
])
def test_analyze_invalid_requests(client, auth, body, code):
    r = client.post("/api/analyze-prompt", json=body, headers=auth)
    assert r.status_code == code and "error" in r.json()


def test_analyze_unauthorized(client):
    assert client.post("/api/analyze-prompt", json={"prompt": PROMPT, "model": "gpt-4o"}).status_code == 401


def test_cannot_analyze_into_someone_elses_project(client, project, make_user):
    eve = make_user("eve@example.com", "Eve")
    assert analyze(client, eve, project_id=project["id"]).status_code == 404


def test_analyze_with_api_key(client, auth):
    secret = client.post("/api-keys", json={"name": "k"}, headers=auth).json()["secret"]
    r = client.post("/api/analyze-prompt", json={"prompt": PROMPT, "model": "gpt-4o"}, headers={"X-API-Key": secret})
    assert r.status_code == 200
    assert client.post("/api/analyze-prompt", json={"prompt": PROMPT, "model": "gpt-4o"},
                       headers={"X-API-Key": "acp_wrong"}).status_code == 401


def test_analyze_rate_limit(client, auth, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "analyze_rate_limit_per_minute", 2)
    codes = [analyze(client, auth).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_nlp_engine_failure_is_a_clean_502(client, auth, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret internal detail")
    mod = types.ModuleType("nlp_engine")
    mod.analyze_prompt = boom
    monkeypatch.setitem(sys.modules, "nlp_engine", mod)
    r = analyze(client, auth)
    assert r.status_code == 502 and r.json()["error"]["code"] == "NLP_SERVICE_ERROR"
    assert "secret internal detail" not in r.text and "Traceback" not in r.text
    assert client.get("/usage", headers=auth).json() == []  # nothing saved on failure


def test_ml_engine_failure_is_a_clean_502(client, auth, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret internal detail")
    mod = types.ModuleType("cost_engine")
    mod.predict_output_tokens = boom
    monkeypatch.setitem(sys.modules, "cost_engine", mod)
    r = analyze(client, auth)
    assert r.status_code == 502 and r.json()["error"]["code"] == "ML_SERVICE_ERROR"
    assert "secret internal detail" not in r.text


def test_missing_engines_without_stubs_gives_502(client, auth, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "use_engine_stubs", False)
    assert analyze(client, auth).status_code == 502
