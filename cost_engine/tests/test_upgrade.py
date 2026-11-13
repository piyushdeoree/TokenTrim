from decimal import Decimal

import pytest

from cost_engine.models import ModelPricing
from cost_engine.pricing import upsert_pricing, get_pricing
from cost_engine.calculator import calculate_cost
from cost_engine.pricing_engine import validate_official_rows, OFFICIAL_SOURCES
from cost_engine.forecasting import aggregate_usage_costs


def test_decimal_cost_cached_and_cache_write():
    item=ModelPricing("unit-test-model","openai",2,4,cached_input_price_per_million=.5,cache_write_price_per_million=3)
    upsert_pricing(item,persist=False)
    result=calculate_cost(item.model,1_000_000,500_000,cached_input_tokens=400_000,cache_write_tokens=100_000)
    assert Decimal(str(result.input_cost)) == Decimal("1.4")
    assert Decimal(str(result.output_cost)) == Decimal("2.0")
    assert Decimal(str(result.other_charges)) == Decimal("0.3")
    assert result.total_cost == pytest.approx(3.7)


def test_cached_tokens_cannot_exceed_input():
    with pytest.raises(ValueError): calculate_cost("gpt-4o",2,1,cached_input_tokens=3)


def test_incomplete_official_rows_rejected():
    with pytest.raises(ValueError): validate_official_rows("openai",[],OFFICIAL_SOURCES["openai"])


def test_usage_aggregation():
    rows=aggregate_usage_costs([{"date":"2026-01-01","cost":"1.25"},{"date":"2026-01-01","cost":"2"}],"monthly")
    assert rows==[{"period":"2026-01","cost":3.25}]
