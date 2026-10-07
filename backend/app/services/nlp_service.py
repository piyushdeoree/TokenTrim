"""Adapter around Person 1's `nlp_engine`.

The backend keeps the NLP engine isolated behind this service. The engine's
heuristic optimizer remains the baseline, while an optional OpenAI rewriter
provides a stronger candidate when the API is available.

If OpenAI is unavailable, out of credits, misconfigured, or fails for any
reason, the heuristic optimizer continues normally.
"""

import importlib
import logging

from openai import OpenAI

from app.core.config import settings
from app.core.exceptions import NLPServiceError

log = logging.getLogger(__name__)
_REQUIRED = ("original_tokens", "optimized_tokens", "optimized_prompt")


def _engine():
    if settings.USE_STUB_ENGINES:
        from app.services import stubs
        return stubs.nlp_engine

    try:
        return importlib.import_module("nlp_engine")
    except ImportError:
        log.exception("nlp_engine could not be imported")
        raise NLPServiceError(
            "Prompt analysis service is currently unavailable."
        )


def _openai_rewriter(model: str):
    """Create an optional OpenAI rewriter."""

    if not settings.OPENAI_API_KEY:
        return None

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def rewrite(prompt: str) -> str:
        response = client.responses.create(
            model=model,
            instructions=(
                "You are a prompt optimization engine. Rewrite the user's "
                "prompt to use fewer tokens while preserving its original "
                "meaning, requirements, constraints, requested output format, "
                "and important context. Remove unnecessary repetition, filler, "
                "and verbosity. Do not answer the prompt. Return only the "
                "optimized prompt text. Never invent requirements or remove "
                "information that changes the user's intended task."
            ),
            input=prompt,
        )

        return response.output_text.strip()

    return rewrite


def analyze(prompt: str, model: str) -> dict:
    engine = _engine()

    try:
        llm_rewriter = None

        if not settings.USE_STUB_ENGINES:
            try:
                llm_rewriter = _openai_rewriter(model)
            except Exception:
                log.warning(
                    "OpenAI optimizer could not be initialized; "
                    "using heuristic optimizer.",
                    exc_info=True,
                )

        result = engine.analyze_prompt(
            prompt=prompt,
            model=model,
            llm_rewriter=llm_rewriter,
        )

        if not all(k in result for k in _REQUIRED):
            raise ValueError(
                f"nlp_engine result missing keys; got {sorted(result)}"
            )

        return {
            "original_tokens": int(result["original_tokens"]),
            "optimized_tokens": int(result["optimized_tokens"]),
            "optimized_prompt": str(result["optimized_prompt"]),
            "issues": list(result.get("issues", [])),
            "suggestions": list(result.get("suggestions", [])),
        }

    except NLPServiceError:
        raise
    except Exception:
        log.exception("nlp_engine.analyze_prompt failed")
        raise NLPServiceError(
            "Prompt analysis failed. Please try again later."
        )