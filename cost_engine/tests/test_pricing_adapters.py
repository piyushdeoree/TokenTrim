"""Offline fixtures for official pricing adapters and refresh safety."""
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import json
from pathlib import Path

import pytest

from cost_engine.pricing_adapters.openai import parse_openai_pricing
from cost_engine.pricing_adapters.anthropic import parse_anthropic_pricing
from cost_engine.pricing_adapters.google import parse_google_pricing
from cost_engine.pricing_adapters.base import price
from cost_engine import pricing_engine
from cost_engine import pricing
from cost_engine.calculator import calculate_cost
from cost_engine.models import ModelPricing

FIXTURES=Path(__file__).parent/"fixtures"
def source(name): return (FIXTURES/name).read_text(encoding="utf-8")

@pytest.fixture(autouse=True)
def isolated_catalogue(tmp_path,monkeypatch):
    monkeypatch.setattr(pricing.config,"PRICING_FILE",tmp_path/"pricing.json")
    monkeypatch.setattr(pricing.config,"PRICING_HISTORY_FILE",tmp_path/"pricing_history.json")
    monkeypatch.setattr(pricing_engine,"REFRESH_STATE_FILE",tmp_path/"refresh_state.json")
    monkeypatch.setattr(pricing,"_registry",None); monkeypatch.setattr(pricing,"_history",{})
    (tmp_path/"pricing.json").write_text('{"_meta":{},"models":[]}',encoding="utf-8")
    yield

def test_openai_markdown_extracts_standard_batch_cache_and_context_variants():
    rows=parse_openai_pricing(source("openai_pricing.md"))
    gpt=next(x for x in rows if x["model"]=="gpt-4o")
    assert gpt["input_price_per_million"]==Decimal("2.50")
    assert gpt["output_price_per_million"]==Decimal("10.00")
    assert gpt["cached_input_price_per_million"]==Decimal("1.25")
    assert gpt["cache_write_price_per_million"]==Decimal("3.125")
    assert gpt["batch_input_price_per_million"]==Decimal("1.25")
    assert gpt["batch_output_price_per_million"]==Decimal("5.00")
    assert len(gpt["pricing_tiers"])==3

def test_anthropic_extracts_cache_batch_fast_and_threshold_conditions():
    rows=parse_anthropic_pricing(source("anthropic_pricing.md"))
    sonnet=next(x for x in rows if x["model"]=="claude-sonnet-4-6")
    assert sonnet["cached_input_price_per_million"]==Decimal("0.30")
    assert sonnet["cache_write_price_per_million"]==Decimal("3.75")
    assert sonnet["batch_input_price_per_million"]==Decimal("1.50")
    assert any(t["tier"]=="fast" for t in sonnet["pricing_tiers"])
    haiku=next(x for x in rows if x["model"]=="claude-haiku-5-5")
    assert len(haiku["pricing_tiers"])>=2
    assert any("prompt_tokens" in t["conditions"] for t in haiku["pricing_tiers"])

def test_google_extracts_current_effective_standard_batch_cache():
    rows=parse_google_pricing(source("google_pricing.md"),today=date(2026,11,13))
    carbon=next(x for x in rows if x["model"]=="gemini-4-carbon")
    assert carbon["input_price_per_million"]==Decimal("2.00")
    assert carbon["output_price_per_million"]==Decimal("10.00")
    assert carbon["cached_input_price_per_million"]==Decimal("0.10")
    assert carbon["batch_input_price_per_million"]==Decimal("1.00")
    assert parse_google_pricing(source("google_pricing.md"),today=date(2026,12,2))[0]["input_price_per_million"]==Decimal("4.00")

def test_google_html_page_structure():
    rows=parse_google_pricing(source("google_pricing.html"),today=date(2026,11,13))
    assert rows[0]["model"]=="gemini-4-carbon"
    assert rows[0]["batch_output_price_per_million"]==Decimal("5.00")

@pytest.mark.parametrize("parser",[parse_openai_pricing,parse_anthropic_pricing,parse_google_pricing])
def test_empty_or_unsupported_page_fails_closed(parser):
    with pytest.raises(ValueError): parser("<html>pricing changed</html>")
    with pytest.raises(ValueError): parser("")

def test_adapter_rejects_missing_model_or_required_rates():
    with pytest.raises(ValueError): parse_openai_pricing(source("openai_pricing.md").replace("| gpt-4o |", "|  |", 1))
    with pytest.raises(ValueError): parse_anthropic_pricing(source("anthropic_pricing.md").replace("$3 / MTok", "price unknown", 1))
    with pytest.raises(ValueError): parse_google_pricing(source("google_pricing.md").replace("[`gemini-4-carbon`](/docs/models/gemini-4-carbon)", "", 1))

@pytest.mark.parametrize("value",["-$1.00","NaN","$not-a-price","","Infinity"])
def test_decimal_parser_rejects_invalid_values(value):
    with pytest.raises(ValueError): price(value)

def test_decimal_storage_source_and_provider_validation():
    parsed=parse_openai_pricing(source("openai_pricing.md"))[0]
    entries=pricing_engine.validate_official_rows("openai",[parsed],pricing_engine.OFFICIAL_SOURCES["openai"],_provenance=pricing_engine._ADAPTER_PROVENANCE)
    assert isinstance(entries[0].input_price_per_million,Decimal)
    assert entries[0].to_dict()["input_price_per_million"]=="2.50"
    with pytest.raises(ValueError,match="adapter parse"):
        pricing_engine.validate_official_rows("openai",[parsed],pricing_engine.OFFICIAL_SOURCES["openai"])
    with pytest.raises(ValueError,match="source"):
        pricing_engine.validate_official_rows("openai",[parsed],"https://example.com",_provenance=pricing_engine._ADAPTER_PROVENANCE)
    with pytest.raises(ValueError,match="provider"):
        pricing_engine.validate_official_rows("bogus",[parsed],"https://example.com",_provenance=pricing_engine._ADAPTER_PROVENANCE)
    with pytest.raises(ValueError): pricing._validate(ModelPricing("invalid","openai",Decimal("-1"),Decimal("1")))
    forged=ModelPricing(**{**parsed,"retrieved_at":datetime.now(timezone.utc).isoformat()})
    with pytest.raises(ValueError,match="provider adapter"):
        pricing.upsert_pricing(forged,persist=False)

def test_invalid_manual_verified_request_rejected():
    with pytest.raises(ValueError,match="manual records cannot"):
        pricing_engine.manual_pricing_update({"model":"sample","provider":"openai","input_price_per_million":"1","output_price_per_million":"2","source_url":pricing_engine.OFFICIAL_SOURCES["openai"]},verified=True)

def test_refresh_provider_updates_records_and_does_not_version_unchanged(monkeypatch):
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",lambda provider,timeout:source("openai_pricing.md"))
    first=pricing_engine.refresh_provider("openai")
    assert first["ok"] and first["model_count"]==2
    before=pricing.get_pricing_decimal("gpt-4o")
    assert before.pricing_status=="official_verified"
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",lambda provider,timeout:source("openai_pricing.md"))
    pricing_engine.refresh_provider("openai")
    after=pricing.get_pricing_decimal("gpt-4o")
    assert after.pricing_version==before.pricing_version
    assert pricing.get_pricing_history("gpt-4o")==[]

def test_refresh_provider_failure_preserves_existing_and_attempt_state(monkeypatch):
    good=source("openai_pricing.md")
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",lambda provider,timeout:good)
    assert pricing_engine.refresh_provider("openai")["ok"]
    old=pricing.get_pricing_decimal("gpt-4o").to_dict()
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",lambda provider,timeout:(_ for _ in ()).throw(TimeoutError("timeout")))
    failed=pricing_engine.refresh_provider("openai")
    assert not failed["ok"] and "timeout" in failed["error"]
    assert pricing.get_pricing_decimal("gpt-4o").to_dict()==old

def test_http_timeout_is_reported_without_mutation(monkeypatch):
    original=parse_openai_pricing(source("openai_pricing.md"))
    pricing.upsert_pricing_batch(pricing_engine.validate_official_rows("openai",original,pricing_engine.OFFICIAL_SOURCES["openai"],_provenance=pricing_engine._ADAPTER_PROVENANCE),_provenance=pricing_engine._ADAPTER_PROVENANCE)
    old=pricing.get_pricing_decimal("gpt-4o").to_dict()
    monkeypatch.setattr("urllib.request.urlopen",lambda *args,**kwargs:(_ for _ in ()).throw(TimeoutError("network timeout")))
    result=pricing_engine.refresh_openai_pricing(timeout=.1)
    assert not result["ok"] and "network timeout" in result["error"]
    assert pricing.get_pricing_decimal("gpt-4o").to_dict()==old

def test_provider_failures_independent_and_history_single_store(monkeypatch):
    def fetch(provider,timeout):
        if provider=="anthropic": raise OSError("offline")
        return source({"openai":"openai_pricing.md","google":"google_pricing.md"}[provider])
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",fetch)
    state=pricing_engine.refresh_pricing()
    assert state["providers"]["openai"]["ok"]
    assert not state["providers"]["anthropic"]["ok"]
    assert state["providers"]["google"]["ok"]
    assert pricing.config.PRICING_HISTORY_FILE.exists()
    assert not json.loads(pricing.config.PRICING_FILE.read_text())["models"][0].get("history")

def test_changed_price_creates_one_persisted_version_and_history(tmp_path,monkeypatch):
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",lambda provider,timeout:source("openai_pricing.md"))
    pricing_engine.refresh_provider("openai")
    prior=pricing.get_pricing_decimal("gpt-4o")
    changed=source("openai_pricing.md").replace("$2.50 | $10.00","$2.75 | $10.50",1)
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",lambda provider,timeout:changed)
    pricing_engine.refresh_provider("openai")
    current=pricing.get_pricing_decimal("gpt-4o")
    assert current.pricing_version==prior.pricing_version+1
    assert calculate_cost("gpt-4o",1_000_000,0,pricing_version=prior.pricing_version).input_cost==2.5
    history=pricing.get_pricing_history("gpt-4o")
    assert len(history)==1 and history[0]["previous"]["input_price_per_million"]=="2.50"
    pricing.reload_pricing()
    assert len(pricing.get_pricing_history("gpt-4o"))==1
    assert pricing.get_pricing_version("gpt-4o",prior.pricing_version).input_price_per_million==Decimal("2.50")

def test_freshness_does_not_reset_after_failure(monkeypatch):
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",lambda provider,timeout:source("openai_pricing.md"))
    pricing_engine.refresh_provider("openai")
    record=pricing.get_pricing_decimal("gpt-4o")
    verified=record.last_verified
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",lambda provider,timeout:(_ for _ in ()).throw(TimeoutError("offline")))
    pricing_engine.refresh_provider("openai")
    assert pricing.get_pricing_decimal("gpt-4o").last_verified==verified
    assert not pricing.pricing_freshness(record)["stale"]

def test_stale_manual_expired_and_invalid_timestamps():
    old=(datetime.now(timezone.utc)-timedelta(days=45)).isoformat()
    base=dict(model="stale-test",provider="openai",input_price_per_million=Decimal("1"),output_price_per_million=Decimal("2"),
        source_url=pricing_engine.OFFICIAL_SOURCES["openai"],last_verified=old,retrieved_at=old,pricing_status="official_verified")
    assert pricing.pricing_freshness(ModelPricing(**base))["status"]=="stale"
    base["last_verified"]="not-a-date"
    assert pricing.pricing_freshness(ModelPricing(**base))["status"]=="invalid_verification_timestamp"
    base["pricing_status"]="manual_unverified"
    assert pricing.pricing_freshness(ModelPricing(**base))["stale"]

def test_refresh_reports_last_good_per_provider_after_one_failure(monkeypatch):
    sources={"openai":"openai_pricing.md","anthropic":"anthropic_pricing.md","google":"google_pricing.md"}
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",lambda provider,timeout:source(sources[provider]))
    first=pricing_engine.refresh_pricing(force=True)
    last={provider:report["last_successful_refresh"] for provider,report in first["providers"].items()}
    def only_anthropic_offline(provider,timeout):
        if provider=="anthropic": raise OSError("offline")
        return source(sources[provider])
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",only_anthropic_offline)
    later=pricing_engine.refresh_pricing(force=True)
    assert later["providers"]["anthropic"]["last_successful_refresh"]==last["anthropic"]
    assert later["providers"]["openai"]["ok"] and later["providers"]["google"]["ok"]

def test_refresh_interval_skips_and_force_attempts_all_providers(monkeypatch):
    def fetch(provider,timeout): return source({"openai":"openai_pricing.md","anthropic":"anthropic_pricing.md","google":"google_pricing.md"}[provider])
    calls=[]
    def counted(provider,timeout): calls.append(provider); return fetch(provider,timeout)
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",counted)
    first=pricing_engine.refresh_pricing(force=True)
    assert all(r["ok"] for r in first["providers"].values())
    assert len(calls)==3
    calls.clear()
    due=pricing_engine.refresh_pricing()
    assert all(r["skipped"] for r in due["providers"].values()) and not calls
    monkeypatch.setattr(pricing_engine,"fetch_provider_page",lambda provider,timeout:(_ for _ in ()).throw(OSError("offline")) if provider=="anthropic" else fetch(provider,timeout))
    failed=pricing_engine.refresh_pricing(force=True)
    assert failed["providers"]["anthropic"]["last_successful_refresh"]==first["providers"]["anthropic"]["last_successful_refresh"]
    assert failed["last_successful_refresh"]==first["last_successful_refresh"]
