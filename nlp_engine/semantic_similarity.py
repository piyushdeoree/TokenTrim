"""
semantic_similarity.py - optional pretrained semantic similarity.

Uses Sentence-Transformers to generate sentence embeddings.

Design:
  * Disabled by default.
  * Loads the pretrained model only when explicitly enabled.
  * Supports CPU and CUDA.
  * Uses normalized embeddings and cosine similarity.
  * Returns None when the optional model is unavailable.
  * Supports model injection for tests without downloading a model.
"""

from __future__ import annotations

import os
from typing import Optional, Sequence

import numpy as np


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

ENABLE_ENV = "TOKENTRIM_ENABLE_SEMANTIC_MODEL"
MODEL_ENV = "TOKENTRIM_SEMANTIC_MODEL"
DEVICE_ENV = "TOKENTRIM_SEMANTIC_DEVICE"

_cached_model = None
_model_load_attempted = False


def semantic_model_enabled() -> bool:
    """Return True only when the optional model is explicitly enabled."""
    return os.getenv(ENABLE_ENV, "false").strip().lower() in {
        "1", "true", "yes", "on"
    }


def get_semantic_model():
    """
    Lazily load the configured Sentence-Transformer model.

    The default device is CPU. Set TOKENTRIM_SEMANTIC_DEVICE=cuda
    on a compatible GPU machine.
    """
    global _cached_model, _model_load_attempted

    if _cached_model is not None:
        return _cached_model

    # Do not permanently mark the model as attempted while disabled.
    if not semantic_model_enabled():
        return None

    if _model_load_attempted:
        return None

    model_name = os.getenv(MODEL_ENV, DEFAULT_MODEL_NAME).strip()
    device = os.getenv(DEVICE_ENV, "cpu").strip().lower()

    if not model_name:
        return None

    # Mark attempted only when an actual loading attempt is about to occur.
    _model_load_attempted = True

    try:
        from sentence_transformers import SentenceTransformer

        _cached_model = SentenceTransformer(
            model_name,
            device=device,
        )
        return _cached_model

    except Exception:
        # Optional component: existing TF-IDF must keep working.
        _cached_model = None
        return None


def semantic_similarity_matrix(
    texts: Sequence[str],
    model=None,
) -> Optional[np.ndarray]:
    """
    Calculate pairwise cosine similarity using sentence embeddings.

    Args:
        texts: Text clauses to compare.
        model: Optional injected model, primarily for testing.

    Returns:
        A square NumPy similarity matrix, or None if unavailable.

    Supplying a model bypasses the environment feature flag.
    """
    if isinstance(texts, (str, bytes)):
        return None

    try:
        clean_texts = [
            str(text).strip()
            for text in texts
            if text is not None and str(text).strip()
        ]

        if len(clean_texts) != len(texts) or len(clean_texts) < 2:
            return None

    except (TypeError, ValueError):
        return None

    active_model = model if model is not None else get_semantic_model()

    if active_model is None:
        return None

    try:
        embeddings = active_model.encode(
            clean_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        embeddings = np.asarray(embeddings, dtype=float)

        if embeddings.ndim != 2:
            return None

        if embeddings.shape[0] != len(clean_texts):
            return None

        if embeddings.shape[1] == 0:
            return None

        if not np.all(np.isfinite(embeddings)):
            return None

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)

        if np.any(norms == 0):
            return None

        normalized = embeddings / norms
        similarities = normalized @ normalized.T

        return np.clip(similarities, -1.0, 1.0)

    except Exception:
        # A semantic-model failure must never break prompt optimization.
        return None
