"""
tokenizer.py - model-aware token counting.

Design
------
* ``count_tokens(prompt, model)`` is the single public entry point.
* Each model family is served by a *token counter* object. Counters are looked
  up through a small registry, so a new tokenizer can be added without editing
  any other module:

      from nlp_engine.tokenizer import register_tokenizer, BaseTokenCounter

      register_tokenizer("my-model", lambda m: m.startswith("my-"), MyCounter)

* Token counts are never invented:
    - OpenAI models  -> exact, via ``tiktoken`` (when the encoding can be loaded)
    - everything else (Anthropic Claude, Google Gemini, unknown models, or
      OpenAI models if tiktoken/encoding files are unavailable)
                     -> a clearly labelled *heuristic estimate*.
  Anthropic and Google publish token counting only through their web APIs, not
  as an offline tokenizer, so exact counts for them require a network call and
  API key. Such a counter can be registered here later (see README).

The method actually used is exposed by ``tokenizer_info(model)``.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Dict, List, Optional, Tuple

from . import config
from .textutils import prepare_prompt


@dataclass(frozen=True)
class TokenizerInfo:
    model: str
    family: str          # openai | anthropic | google | unknown
    method: str          # e.g. "tiktoken:o200k_base" or "heuristic_estimate"
    exact: bool          # True only when an official tokenizer produced the count
    note: str = ""


class BaseTokenCounter:
    """Interface every tokenizer implements."""

    info: TokenizerInfo

    def count(self, text: str) -> int:  # pragma: no cover - interface
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Heuristic fallback (clearly an ESTIMATE)
# ---------------------------------------------------------------------------
_PIECE_RE = re.compile(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]")


def heuristic_token_estimate(text: str) -> int:
    """Approximate BPE token count without any vocabulary file.

    Pre-tokenises into alphabetic runs, digit runs and single symbols, then
    assumes ~4 characters per alphabetic token and ~3 digits per numeric token
    (typical of BPE vocabularies); every non-ASCII symbol counts as 1 token.
    This is a documented approximation, NOT an exact tokenizer.
    """
    total = 0
    for piece in _PIECE_RE.findall(text):
        if piece.isascii():
            if piece.isalpha():
                total += max(1, math.ceil(len(piece) / 4))
            elif piece.isdigit():
                total += math.ceil(len(piece) / 3)
            else:
                total += 1
        else:
            total += len(piece)
    return total


class HeuristicCounter(BaseTokenCounter):
    def __init__(self, model: str, family: str, note: str = ""):
        self.info = TokenizerInfo(
            model=model, family=family, method="heuristic_estimate", exact=False,
            note=note or "No offline tokenizer for this model; count is an estimate.",
        )

    def count(self, text: str) -> int:
        return heuristic_token_estimate(text)


class TiktokenCounter(BaseTokenCounter):
    def __init__(self, model: str, encoding):
        self._enc = encoding
        self.info = TokenizerInfo(
            model=model, family="openai", method=f"tiktoken:{encoding.name}", exact=True,
            note="Exact count from OpenAI's tiktoken encoding.",
        )

    def count(self, text: str) -> int:
        return len(self._enc.encode(text, disallowed_special=()))


# ---------------------------------------------------------------------------
# Factories + registry
# ---------------------------------------------------------------------------
def _family(model: str) -> str:
    m = model.lower()
    if m.startswith(("gpt", "o1", "o3", "o4", "text-", "chatgpt")):
        return "openai"
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith(("gemini", "gemma", "models/gemini")):
        return "google"
    return "unknown"


def _openai_factory(model: str) -> BaseTokenCounter:
    try:
        import tiktoken
    except ImportError:
        return HeuristicCounter(model, "openai", "tiktoken is not installed; count is an estimate.")
    try:
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            name = next((e for p, e in config.OPENAI_PREFIX_ENCODINGS if model.lower().startswith(p)), None)
            if name is None:
                return HeuristicCounter(model, "openai", "Unknown OpenAI model name; count is an estimate.")
            enc = tiktoken.get_encoding(name)
        return TiktokenCounter(model, enc)
    except Exception as exc:  # e.g. encoding file could not be downloaded (offline)
        return HeuristicCounter(
            model, "openai",
            f"tiktoken encoding could not be loaded ({type(exc).__name__}); count is an estimate.",
        )


def _fallback_factory(model: str) -> BaseTokenCounter:
    fam = _family(model)
    notes = {
        "anthropic": "Claude has no offline tokenizer; count is an estimate (exact counts need the Anthropic count_tokens API).",
        "google": "Gemini has no offline tokenizer; count is an estimate (exact counts need the Gemini countTokens API).",
    }
    return HeuristicCounter(model, fam, notes.get(fam, ""))


# (name, matcher, factory) - first matching entry wins; later registrations take priority.
_REGISTRY: List[Tuple[str, Callable[[str], bool], Callable[[str], BaseTokenCounter]]] = [
    ("openai", lambda m: _family(m) == "openai", _openai_factory),
]


def register_tokenizer(name: str, matcher: Callable[[str], bool],
                       factory: Callable[[str], BaseTokenCounter]) -> None:
    """Register an additional tokenizer (takes priority over built-ins)."""
    _REGISTRY.insert(0, (name, matcher, factory))
    get_counter.cache_clear()


@lru_cache(maxsize=64)
def get_counter(model: str) -> BaseTokenCounter:
    for _, matcher, factory in _REGISTRY:
        if matcher(model):
            return factory(model)
    return _fallback_factory(model)


def tokenizer_info(model: str) -> TokenizerInfo:
    """Which method is used for ``model``? (exact tokenizer or estimate)."""
    return get_counter(model).info


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_WORD_COUNT_RE = re.compile(r"\b\w+(?:[-'\u2019]\w+)*\b")


def count_tokens_only(text: str, model: str = config.DEFAULT_MODEL) -> int:
    return get_counter(model).count(text)


def count_tokens(prompt: str, model: str = config.DEFAULT_MODEL) -> Dict[str, int]:
    """Return the four basic text statistics for ``prompt``.

    {"input_tokens", "word_count", "character_count", "sentence_count"}
    ``input_tokens`` is exact only if ``tokenizer_info(model).exact`` is True.
    """
    return {
        "input_tokens": count_tokens_only(prompt, model),
        "word_count": len(_WORD_COUNT_RE.findall(prompt)),
        "character_count": len(prompt),
        "sentence_count": len(prepare_prompt(prompt).segments) if prompt.strip() else 0,
    }
