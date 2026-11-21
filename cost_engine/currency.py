"""Optional USD to INR display conversion with cached, timestamped rates."""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import logging
import os
import tempfile
import threading
import urllib.request
from . import config

ISO_4217_CODES = {
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN",
    "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BRL",
    "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHF", "CLP", "CNY",
    "COP", "CRC", "CUC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP", "DZD",
    "EGP", "ERN", "ETB", "EUR", "FJD", "FKP", "GBP", "GEL", "GHS", "GIP",
    "GMD", "GNF", "GTQ", "GYD", "HKD", "HNL", "HRK", "HTG", "HUF", "IDR",
    "ILS", "INR", "IQD", "IRR", "ISK", "JMD", "JOD", "JPY", "KES", "KGS",
    "KHR", "KMF", "KPW", "KRW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR",
    "LRD", "LSL", "LYD", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP",
    "MRU", "MUR", "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN", "NIO",
    "NOK", "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN",
    "PYG", "QAR", "RON", "RSD", "RUB", "RWF", "SAR", "SBD", "SCR", "SDG",
    "SEK", "SGD", "SHP", "SLL", "SOS", "SRD", "SSP", "STN", "SVC", "SYP",
    "SZL", "THB", "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TWD", "TZS",
    "UAH", "UGX", "USD", "UYU", "UZS", "VES", "VND", "VUV", "WST", "XAF",
    "XCD", "XOF", "XPF", "YER", "ZAR", "ZMW", "ZWL",
}

def is_valid_currency(currency: str) -> bool:
    """Validate whether currency is a recognized ISO 4217 code."""
    if not isinstance(currency, str):
        return False
    return currency.strip().upper() in ISO_4217_CODES

def normalize_currency(currency: str) -> str:
    """Normalize and validate an ISO 4217 currency code."""
    if not isinstance(currency, str) or not is_valid_currency(currency):
        raise ValueError(f"Invalid ISO 4217 currency code: {currency!r}")
    return currency.strip().upper()

RATE_FILE=config.DATA_DIR/"exchange_rate.json"
RATE_URL="https://api.frankfurter.app/latest?from=USD&to=INR"
_logger = logging.getLogger(__name__)
_rate_lock = threading.RLock()
_cached_rate = None

def get_usd_inr_rate(*, refresh: bool = False, timeout: float = 10.0) -> dict:
    global _cached_rate
    with _rate_lock:
        if _cached_rate is not None and not refresh:
            age = (date.today() - date.fromisoformat(_cached_rate["rate_date"])).days
            return {**_cached_rate,"stale":age > 1}
        if RATE_FILE.exists() and _cached_rate is None:
            try:
                record=json.loads(RATE_FILE.read_text(encoding="utf-8"))
                rate=Decimal(str(record["rate"]))
                if (not rate.is_finite() or rate <= 0 or record.get("source_url") != RATE_URL
                        or not record.get("rate_date") or not record.get("retrieved_at")):
                    raise ValueError("invalid cached exchange-rate record")
                date.fromisoformat(record["rate_date"])
                datetime.fromisoformat(record["retrieved_at"].replace("Z", "+00:00"))
                _cached_rate=record
            except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
                _logger.warning("Ignoring invalid cached exchange rate: %s", exc)
        if refresh:
            try:
                req=urllib.request.Request(RATE_URL,headers={"User-Agent":"TokenTrim-CostEngine/1.0"})
                with urllib.request.urlopen(req,timeout=timeout) as response: data=json.loads(response.read())
                rate=Decimal(str(data["rates"]["INR"]))
                rate_date=data["date"]
                if not rate.is_finite() or rate<=0 or data.get("base")!="USD": raise ValueError("invalid exchange-rate response")
                date.fromisoformat(rate_date)
                record={"rate":str(rate),"source_url":RATE_URL,"rate_date":rate_date,"retrieved_at":datetime.now(timezone.utc).isoformat()}
                RATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                fd, temp_name = tempfile.mkstemp(prefix=".exchange-rate-", suffix=".tmp", dir=RATE_FILE.parent)
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as output:
                        output.write(json.dumps(record, indent=2))
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(temp_name, RATE_FILE)
                except Exception:
                    try: os.unlink(temp_name)
                    except OSError: pass
                    raise
                _cached_rate=record
                return {**record,"stale":False}
            except Exception as exc:
                _logger.warning("USD/INR refresh failed; using last valid rate when available: %s", exc)
        if _cached_rate is not None:
            return {**_cached_rate,"stale":True}
        raise RuntimeError("No valid USD/INR exchange rate is available; return USD only")

def convert_usd_to_inr(amount: Decimal | str | float, *, refresh: bool = False) -> dict:
    record=get_usd_inr_rate(refresh=refresh)
    try: usd=Decimal(str(amount))
    except (ValueError, TypeError, InvalidOperation): raise ValueError("amount must be a finite non-negative decimal") from None
    if not usd.is_finite() or usd < 0: raise ValueError("amount must be a finite non-negative decimal")
    inr=usd*Decimal(record["rate"])
    if not inr.is_finite(): raise ValueError("converted amount is outside the supported Decimal range")
    return {"usd":str(usd),"inr":str(inr),"rate":record["rate"],"rate_date":record["rate_date"],"stale":record["stale"],"source_url":RATE_URL}
