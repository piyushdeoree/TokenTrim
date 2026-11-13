"""Optional USD to INR display conversion with cached, timestamped rates."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
import json
import urllib.request
from . import config

RATE_FILE=config.DATA_DIR/"exchange_rate.json"
RATE_URL="https://api.frankfurter.app/latest?from=USD&to=INR"

def get_usd_inr_rate(*, refresh: bool = False, timeout: float = 10.0) -> dict:
    if refresh:
        try:
            req=urllib.request.Request(RATE_URL,headers={"User-Agent":"TokenTrim-CostEngine/1.0"})
            with urllib.request.urlopen(req,timeout=timeout) as r: data=json.loads(r.read())
            rate=Decimal(str(data["rates"]["INR"]))
            if not rate.is_finite() or rate<=0 or data.get("base")!="USD": raise ValueError("Invalid exchange rate response")
            record={"rate":str(rate),"source_url":RATE_URL,"rate_date":data["date"],"retrieved_at":datetime.now(timezone.utc).isoformat()}
            RATE_FILE.write_text(json.dumps(record,indent=2),encoding="utf-8")
            return {**record,"stale":False}
        except Exception:
            pass
    if RATE_FILE.exists():
        record=json.loads(RATE_FILE.read_text(encoding="utf-8"))
        return {**record,"stale":True}
    raise RuntimeError("No valid USD/INR exchange rate is available; return USD only")

def convert_usd_to_inr(amount: Decimal | str | float, *, refresh: bool = False) -> dict:
    record=get_usd_inr_rate(refresh=refresh)
    usd=Decimal(str(amount)); inr=usd*Decimal(record["rate"])
    return {"usd":str(usd),"inr":str(inr),"rate":record["rate"],"rate_date":record["rate_date"],"stale":record["stale"],"source_url":RATE_URL}
