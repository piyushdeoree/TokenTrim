"""Optional live smoke test; normal pytest runs never access provider websites."""
import os
import pytest

from cost_engine.pricing_engine import fetch_provider_page, OFFICIAL_SOURCES
from cost_engine.pricing_adapters import PARSERS

pytestmark=pytest.mark.skipif(os.getenv("COST_ENGINE_RUN_LIVE_PRICING")!="1",
    reason="set COST_ENGINE_RUN_LIVE_PRICING=1 to fetch official provider pages")

@pytest.mark.parametrize("provider",list(OFFICIAL_SOURCES))
def test_live_official_page_parser_smoke(provider):
    page=fetch_provider_page(provider,timeout=30)
    rows=PARSERS[provider](page)
    assert rows and all(row["provider"]==provider for row in rows)
    assert all(row["input_price_per_million"]>=0 and row["output_price_per_million"]>=0 for row in rows)
