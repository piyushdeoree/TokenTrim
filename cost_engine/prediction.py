"""Output-token prediction.

Trains and compares a simple baseline (Linear Regression) against stronger
models (Random Forest, Gradient Boosting), selects by cross-validated RMSE on
the TRAIN split only, and reports MAE / RMSE / R2 on a held-out TEST split.

Metrics are only as meaningful as the data. If trained on the synthetic
dataset, they describe the synthetic generator, NOT real LLM behaviour.

Train:  python -m cost_engine.prediction
"""
from __future__ import annotations

import json
import re
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from . import config

TASK_TYPES = [
    "question_answering", "summarization", "translation", "coding",
    "creative_writing", "extraction", "analysis",
]
NUMERIC_FEATURES = ["input_tokens", "word_count", "sentence_count", "complexity"]
CATEGORICAL_FEATURES = ["task_type", "model"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

_KEYWORDS = {
    "summarization": ["summarize", "summarise", "summary", "tl;dr", "tldr", "condense"],
    "translation": ["translate", "translation", "in french", "in spanish", "in hindi", "into english"],
    "coding": ["code", "function", "python", "javascript", "bug", "debug", "implement", "sql", "class "],
    "creative_writing": ["story", "poem", "write a", "creative", "essay", "lyrics"],
    "extraction": ["extract", "list all", "parse", "pull out", "find all"],
    "analysis": ["analyze", "analyse", "compare", "evaluate", "trend", "why "],
}


# --------------------------------------------------------------------------
# Feature engineering
# --------------------------------------------------------------------------
def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def count_sentences(text: str) -> int:
    parts = [s for s in re.split(r"[.!?]+(?:\s|$)", text or "") if s.strip()]
    return max(1, len(parts)) if (text or "").strip() else 0


def classify_task(prompt_text: str) -> str:
    """Rule-based keyword classifier (simple, explainable, NOT validated)."""
    t = (prompt_text or "").lower()
    for task, kws in _KEYWORDS.items():
        if any(k in t for k in kws):
            return task
    return "question_answering"


def estimate_complexity(input_tokens: int, sentence_count: int) -> int:
    """Crude 1-5 heuristic from prompt length; a placeholder, not a validated metric."""
    if input_tokens < 50:
        return 1
    if input_tokens < 200:
        return 2
    if input_tokens < 800:
        return 3
    if input_tokens < 3000:
        return 4
    return 5


def build_feature_row(
    input_tokens: int,
    task_type: Optional[str] = None,
    model: Optional[str] = None,
    complexity: Optional[int] = None,
    prompt_text: Optional[str] = None,
    word_count: Optional[int] = None,
    sentence_count: Optional[int] = None,
) -> pd.DataFrame:
    if prompt_text is not None:
        word_count = word_count if word_count is not None else count_words(prompt_text)
        sentence_count = sentence_count if sentence_count is not None else count_sentences(prompt_text)
        task_type = task_type or classify_task(prompt_text)
    word_count = word_count if word_count is not None else int(round(input_tokens * 0.75))
    sentence_count = sentence_count if sentence_count is not None else max(1, int(word_count / 18))
    complexity = complexity if complexity is not None else estimate_complexity(input_tokens, sentence_count)
    return pd.DataFrame([{
        "input_tokens": input_tokens,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "complexity": complexity,
        "task_type": task_type or "unknown",
        "model": model or "unknown",
    }])


# --------------------------------------------------------------------------
# Training
# --------------------------------------------------------------------------
def _pipeline(estimator) -> Pipeline:
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ("num", "passthrough", NUMERIC_FEATURES),
    ])
    return Pipeline([("pre", pre), ("est", estimator)])


def _candidates() -> dict:
    rs = config.RANDOM_STATE
    return {
        "linear_regression": _pipeline(LinearRegression()),
        "random_forest": _pipeline(RandomForestRegressor(n_estimators=150, min_samples_leaf=3, n_jobs=-1, random_state=rs)),
        "gradient_boosting": _pipeline(GradientBoostingRegressor(random_state=rs)),
    }


def _metrics(y_true, y_pred) -> dict:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def train(df: Optional[pd.DataFrame] = None, data_source: Optional[str] = None) -> dict:
    """Train, compare, persist the best model and a metrics report."""
    if df is None:
        path = config.REAL_DATASET_FILE if config.REAL_DATASET_FILE.exists() else config.SYNTHETIC_DATASET_FILE
        if not path.exists():
            raise FileNotFoundError(
                f"No dataset at {path}. Run: python -m cost_engine.data.generate_synthetic"
            )
        df = pd.read_csv(path)
        data_source = data_source or ("REAL" if path == config.REAL_DATASET_FILE else "SYNTHETIC")
    data_source = data_source or "UNKNOWN"

    X, y = df[FEATURES], df["output_tokens"]
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=config.TEST_SIZE, random_state=config.RANDOM_STATE
    )

    # Naive baseline: predict the training mean output length
    mean_pred = np.full(len(y_te), y_tr.mean())
    report = {"data_source": data_source, "n_rows": int(len(df)),
              "n_train": int(len(X_tr)), "n_test": int(len(X_te)),
              "models": {"mean_baseline": {"test": _metrics(y_te, mean_pred)}}}

    cands = _candidates()
    for name, pipe in cands.items():
        cv_rmse = -cross_val_score(pipe, X_tr, y_tr, cv=5, scoring="neg_root_mean_squared_error").mean()
        pipe.fit(X_tr, y_tr)
        report["models"][name] = {"cv_rmse_train": float(cv_rmse), "test": _metrics(y_te, pipe.predict(X_te))}

    best = min(cands, key=lambda n: report["models"][n]["cv_rmse_train"])
    report["selected_model"] = best
    report["selection_rule"] = "lowest 5-fold CV RMSE on the train split"
    if data_source != "REAL":
        report["warning"] = (
            f"Trained on {data_source} data. These metrics do not describe real-world accuracy."
        )

    config.ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": cands[best], "name": best, "data_source": data_source}, config.PREDICTOR_FILE)
    with open(config.METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    global _cached
    _cached = None
    return report


# --------------------------------------------------------------------------
# Inference
# --------------------------------------------------------------------------
_cached = None


def _load():
    global _cached
    if _cached is None and config.PREDICTOR_FILE.exists():
        _cached = joblib.load(config.PREDICTOR_FILE)
    return _cached


def predict_output_tokens(
    input_tokens: int,
    task_type: Optional[str] = None,
    model: Optional[str] = None,
    complexity: Optional[int] = None,
    prompt_text: Optional[str] = None,
    word_count: Optional[int] = None,
    sentence_count: Optional[int] = None,
) -> dict:
    """Predict output tokens for a prompt.

    Returns ``predicted_output_tokens`` plus ``source`` so callers can see
    whether a trained model or the naive fallback produced the number.
    """
    if isinstance(input_tokens, bool) or not isinstance(input_tokens, (int, float)) or input_tokens < 0:
        raise ValueError("input_tokens must be a non-negative number")
    input_tokens = int(input_tokens)

    art = _load()
    if art is None:
        pred = int(round(config.FALLBACK_OUTPUT_RATIO * input_tokens))
        return {
            "predicted_output_tokens": max(config.MIN_PREDICTED_OUTPUT_TOKENS, pred),
            "source": "fallback_ratio",
            "warning": "No trained predictor found; using naive ratio * input_tokens.",
        }
    row = build_feature_row(input_tokens, task_type, model, complexity, prompt_text, word_count, sentence_count)
    pred = float(art["pipeline"].predict(row)[0])
    return {
        "predicted_output_tokens": max(config.MIN_PREDICTED_OUTPUT_TOKENS, int(round(pred))),
        "source": f"trained:{art['name']}",
        "training_data": art["data_source"],
    }


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
