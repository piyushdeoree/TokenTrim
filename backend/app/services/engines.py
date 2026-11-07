"""Adapter layer around Person 1's `nlp_engine` and Person 2's `cost_engine`.

Integration contract (agree on this with Persons 1 and 2; change only here):

  nlp_engine.analyze_prompt(prompt: str, model: str) -> dict
      {"original_tokens": int, "optimized_tokens": int, "optimized_prompt": str,
       "issues": list[str], "suggestions": list[str]}

  cost_engine.predict_output_tokens(prompt: str, input_tokens: int, model: str) -> int
  cost_engine.estimate_cost(model: str, input_tokens: int, output_tokens: int, pricing: dict) -> float
      pricing = {"input_per_1k": float, "output_per_1k": float, "currency": str}   (from the DB)
  cost_engine.forecast_cost(daily_costs: list[float], horizon_days: int) -> list[float]

If an engine module can't be imported and USE_ENGINE_STUBS=true, simple placeholder logic is used so the
backend runs standalone. With stubs off, a missing engine yields a 502 (NLP_SERVICE_ERROR / ML_SERVICE_ERROR).
Any exception raised inside an engine is logged and converted to a clean 502 - no internals leak to clients.
"""
import importlib
import logging
import math
import re

from app.core.config import get_settings
from app.core.errors import AppError, MLServiceError, NLPServiceError

logger = logging.getLogger("app.engines")


def _engine(module_name: str, err_cls):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        if get_settings().use_engine_stubs:
            return None
        logger.error("Engine module %s is not importable", module_name)
        raise err_cls()


# ---------------- NLP (Person 1) ----------------
_FILLER = re.compile(r"\b(please|kindly|i would like you to|could you|basically|actually)\b\s*", re.I)


def _stub_tokens(text: str) -> int:
    return max(1, math.ceil(len(text.split()) * 1.3))


def _stub_nlp(prompt: str, model: str) -> dict:
    optimized = re.sub(r"\s+", " ", _FILLER.sub("", prompt)).strip() or prompt.strip()
    issues = ["Filler words detected"] if optimized != re.sub(r"\s+", " ", prompt).strip() else []
    return {"original_tokens": _stub_tokens(prompt), "optimized_tokens": _stub_tokens(optimized),
            "optimized_prompt": optimized, "issues": issues,
            "suggestions": ["Remove filler phrases such as 'please' or 'kindly'"] if issues else []}


def _nonneg_int(v, name: str) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
        raise ValueError(f"{name} must be a non-negative number")
    return int(v)


def analyze_prompt(prompt: str, model: str) -> dict:
    mod = _engine("nlp_engine", NLPServiceError)
    try:
        raw = _stub_nlp(prompt, model) if mod is None else mod.analyze_prompt(prompt=prompt, model=model)
        return {
            "original_tokens": _nonneg_int(raw["original_tokens"], "original_tokens"),
            "optimized_tokens": _nonneg_int(raw["optimized_tokens"], "optimized_tokens"),
            "optimized_prompt": str(raw["optimized_prompt"]),
            "issues": [str(i) for i in raw.get("issues", [])],
            "suggestions": [str(s) for s in raw.get("suggestions", [])],
        }
    except AppError:
        raise
    except Exception:
        logger.exception("nlp_engine.analyze_prompt failed")
        raise NLPServiceError()


# ---------------- Cost / ML (Person 2) ----------------
def predict_output_tokens(prompt: str, input_tokens: int, model: str) -> int:
    mod = _engine("cost_engine", MLServiceError)
    try:
        value = max(50, input_tokens * 2) if mod is None else mod.predict_output_tokens(
            prompt=prompt, input_tokens=input_tokens, model=model)
        return _nonneg_int(value, "predicted_output_tokens")
    except AppError:
        raise
    except Exception:
        logger.exception("cost_engine.predict_output_tokens failed")
        raise MLServiceError()


def estimate_cost(model: str, input_tokens: int, output_tokens: int, pricing: dict) -> float:
    mod = _engine("cost_engine", MLServiceError)
    try:
        if mod is None:
            value = input_tokens / 1000 * pricing["input_per_1k"] + output_tokens / 1000 * pricing["output_per_1k"]
        else:
            value = mod.estimate_cost(model=model, input_tokens=input_tokens, output_tokens=output_tokens,
                                      pricing=pricing)
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError("estimate_cost returned an invalid value")
        return float(value)
    except AppError:
        raise
    except Exception:
        logger.exception("cost_engine.estimate_cost failed")
        raise MLServiceError()


def forecast_cost(daily_costs: list[float], horizon_days: int) -> list[float]:
    mod = _engine("cost_engine", MLServiceError)
    try:
        if mod is None:
            recent = daily_costs[-7:] or [0.0]
            return [sum(recent) / len(recent)] * horizon_days
        out = [float(x) for x in mod.forecast_cost(daily_costs=daily_costs, horizon_days=horizon_days)]
        if len(out) != horizon_days or any(x < 0 for x in out):
            raise ValueError("forecast_cost returned an unexpected shape")
        return out
    except AppError:
        raise
    except Exception:
        logger.exception("cost_engine.forecast_cost failed")
        raise MLServiceError()
