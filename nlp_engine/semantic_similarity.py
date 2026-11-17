"""
semantic_similarity.py - optional pretrained sentence-embedding support.

Purpose:
  Provide cosine similarity scores between clauses using a local pretrained
  sentence-transformer model when explicitly enabled.

Safety rules:
  * Disabled by default.
  * Never downloads models at runtime (local_files_only=True when supported).
  * Never blocks or breaks the rule-based/TF-IDF pipeline if unavailable.
  * Scores are advisory only; they never authorize automatic deletion.
"""

from __future__ import annotations

import inspect
import os
import threading
from typing import Optional, Sequence

import numpy as np

from . import config

ENABLE_ENV = "TOKENTRIM_ENABLE_SEMANTIC_MODEL"
MODEL_ENV = "TOKENTRIM_SEMANTIC_MODEL"
DEVICE_ENV = "TOKENTRIM_SEMANTIC_DEVICE"
DEFAULT_MODEL_NAME = getattr(config, "SEMANTIC_MODEL_NAME", "all-MiniLM-L6-v2")
DEFAULT_DEVICE = getattr(config, "SEMANTIC_DEVICE", "cpu")

_MODEL_LOCK = threading.Lock()
_cached_model = None
_model_load_attempted = False


def semantic_model_enabled() -> bool:
    """Return True when the optional semantic similarity model is explicitly enabled."""
    raw = os.getenv(ENABLE_ENV, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def semantic_model_name() -> str:
    """Return the configured Sentence-Transformers model identifier or local path."""
    env_name = os.getenv(MODEL_ENV, "").strip()
    return env_name or DEFAULT_MODEL_NAME


def semantic_device() -> str:
    """Return the configured inference device (defaults to 'cpu')."""
    env_device = os.getenv(DEVICE_ENV, "").strip()
    return env_device or DEFAULT_DEVICE


def _instantiate_sentence_transformer(cls, model_name: str, device: str):
    """Instantiate ``SentenceTransformer`` with ``local_files_only=True`` if supported."""
    try:
        sig = inspect.signature(cls)
        params = sig.parameters
        accepts_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        )
        if "local_files_only" in params or accepts_kwargs:
            return cls(model_name, device=device, local_files_only=True)
    except (TypeError, ValueError):
        pass
    return cls(model_name, device=device)


def get_semantic_model():
    """
    Lazily load the local pretrained sentence-embedding model if enabled.

    Returns None when disabled, uninstalled, or not cached locally.
    Thread-safe: concurrent cold-start callers serialize initialization
    without duplicating model loads.
    """
    global _cached_model, _model_load_attempted

    if not semantic_model_enabled():
        return None

    if _cached_model is not None or _model_load_attempted:
        return _cached_model

    with _MODEL_LOCK:
        if _cached_model is not None or _model_load_attempted:
            return _cached_model

        try:
            from sentence_transformers import SentenceTransformer

            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

            _cached_model = _instantiate_sentence_transformer(
                SentenceTransformer,
                semantic_model_name(),
                semantic_device(),
            )
        except Exception:
            _cached_model = None
        finally:
            _model_load_attempted = True

    return _cached_model


def _encode_texts(active_model, texts: Sequence[str]):
    """Invoke ``active_model.encode`` across real models and lightweight test stubs."""
    text_list = list(texts)
    try:
        sig = inspect.signature(active_model.encode)
        params = sig.parameters
        accepts_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        )
        kwargs = {}
        if "convert_to_numpy" in params or accepts_kwargs:
            kwargs["convert_to_numpy"] = True
        if "normalize_embeddings" in params or accepts_kwargs:
            kwargs["normalize_embeddings"] = True
        if "show_progress_bar" in params or accepts_kwargs:
            kwargs["show_progress_bar"] = False
        return active_model.encode(text_list, **kwargs)
    except (TypeError, ValueError):
        return active_model.encode(text_list)


def semantic_similarity_matrix(
    texts: Sequence[str],
    model=None,
) -> Optional[np.ndarray]:
    """
    Compute a pairwise cosine similarity matrix for ``texts``.

    Returns None when fewer than 2 texts are provided, any item is blank/non-str,
    the semantic model is unavailable, embeddings are malformed/zero-norm, or
    encoding fails. Inference runs outside ``_MODEL_LOCK``.
    """
    if not texts or len(texts) < 2:
        return None
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        return None

    active_model = model if model is not None else get_semantic_model()
    if active_model is None:
        return None

    try:
        raw_embeddings = _encode_texts(active_model, texts)
        if raw_embeddings is None:
            return None
        embeddings = np.asarray(raw_embeddings, dtype=float)
        if embeddings.ndim != 2 or embeddings.shape[0] != len(texts) or embeddings.shape[1] == 0:
            return None
        if not np.all(np.isfinite(embeddings)):
            return None
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        if np.any(norms <= 0):
            return None
        normalized = embeddings / norms
        return np.matmul(normalized, normalized.T)
    except Exception:
        return None