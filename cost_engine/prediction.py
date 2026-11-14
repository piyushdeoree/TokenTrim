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
import math
import hashlib
import logging
import os
import tempfile
import threading
from collections import OrderedDict
from datetime import datetime, timezone
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
import sklearn

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

_logger = logging.getLogger(__name__)
_model_lock = threading.RLock()
_load_issue: Optional[str] = None
_load_attempted = False
MIN_TRAINING_ROWS = 25
ARTIFACT_SCHEMA_VERSION = 1
_PREDICTION_CACHE_MAXSIZE = 256
_prediction_cache = OrderedDict()
_prediction_cache_lock = threading.RLock()
_prediction_cache_generation = 0


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
    return pd.DataFrame([_build_feature_values(
        input_tokens, task_type, model, complexity, prompt_text, word_count, sentence_count
    )], columns=FEATURES)


def _build_feature_values(
    input_tokens: int,
    task_type: Optional[str] = None,
    model: Optional[str] = None,
    complexity: Optional[int] = None,
    prompt_text: Optional[str] = None,
    word_count: Optional[int] = None,
    sentence_count: Optional[int] = None,
) -> dict:
    if prompt_text is not None:
        word_count = word_count if word_count is not None else count_words(prompt_text)
        sentence_count = sentence_count if sentence_count is not None else count_sentences(prompt_text)
        task_type = task_type or classify_task(prompt_text)
    word_count = word_count if word_count is not None else int(round(input_tokens * 0.75))
    sentence_count = sentence_count if sentence_count is not None else max(1, int(word_count / 18))
    complexity = complexity if complexity is not None else estimate_complexity(input_tokens, sentence_count)
    return {
        "input_tokens": input_tokens,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "complexity": complexity,
        "task_type": task_type or "unknown",
        "model": model or "unknown",
    }


def _clear_prediction_cache() -> None:
    global _prediction_cache_generation
    with _prediction_cache_lock:
        _prediction_cache.clear()
        _prediction_cache_generation += 1


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

    df = _validate_training_data(df)

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
    report["sklearn_version"] = sklearn.__version__
    report["selected_model_metrics"] = report["models"][best]["test"]
    if data_source != "REAL":
        report["warning"] = (
            f"Trained on {data_source} data. These metrics do not describe real-world accuracy."
        )

    config.ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "data_source": data_source,
        "training_rows": int(len(df)),
        "feature_schema": list(FEATURES),
        "selected_model": best,
        "selected_model_metrics": report["selected_model_metrics"],
    }
    artifact = {"pipeline": cands[best], "name": best, "data_source": data_source,
                "metadata": metadata}
    artifact_tmp = config.PREDICTOR_FILE.with_suffix(config.PREDICTOR_FILE.suffix + ".tmp")
    try:
        joblib.dump(artifact, artifact_tmp)
        metadata["artifact_sha256"] = _sha256_file(artifact_tmp)
        os.replace(artifact_tmp, config.PREDICTOR_FILE)
        _atomic_json(config.PREDICTOR_METADATA_FILE, metadata)
        _atomic_json(config.METRICS_FILE, report)
    finally:
        try:
            artifact_tmp.unlink()
        except FileNotFoundError:
            pass
    global _cached, _load_issue, _load_attempted
    with _model_lock:
        _cached = None
        _load_issue = None
        _load_attempted = False
    _clear_prediction_cache()
    return report


def _validate_training_data(df: pd.DataFrame) -> pd.DataFrame:
    """Reject insufficient, incomplete, or non-finite usage data before fitting."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("training data must be a pandas DataFrame")
    missing = [column for column in (*FEATURES, "output_tokens") if column not in df.columns]
    if missing:
        raise ValueError(f"training data is missing required columns: {missing}")
    if len(df) < MIN_TRAINING_ROWS:
        raise ValueError(f"need at least {MIN_TRAINING_ROWS} training rows, got {len(df)}")
    clean = df.loc[:, [*FEATURES, "output_tokens"]].copy()
    numeric_columns = [*NUMERIC_FEATURES, "output_tokens"]
    for column in numeric_columns:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")
        values = clean[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"training column {column!r} contains missing or non-finite values")
        if (values < 0).any():
            raise ValueError(f"training column {column!r} contains negative values")
        if ((clean[column] % 1) != 0).any():
            raise ValueError(f"training column {column!r} must contain whole counts")
    if ((clean["output_tokens"] % 1) != 0).any():
        raise ValueError("output_tokens must contain whole token counts")
    if clean[CATEGORICAL_FEATURES].isna().any().any():
        raise ValueError("categorical training features cannot be missing")
    for column in CATEGORICAL_FEATURES:
        clean[column] = clean[column].astype(str)
        if clean[column].str.strip().eq("").any():
            raise ValueError(f"training column {column!r} contains empty categories")
    return clean


def _sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".predictor-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(payload, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------
# Inference
# --------------------------------------------------------------------------
_cached = None


def _load():
    global _cached, _load_issue, _load_attempted
    with _model_lock:
        if _cached is not None:
            return _cached
        if _load_attempted:
            return None
        if not config.PREDICTOR_FILE.exists():
            return None
        metadata = None
        if config.PREDICTOR_METADATA_FILE.exists():
            try:
                metadata = json.loads(config.PREDICTOR_METADATA_FILE.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                _load_issue = f"Predictor metadata is unreadable: {exc}"
                _logger.error(_load_issue)
                return None
            if metadata.get("artifact_schema_version") != ARTIFACT_SCHEMA_VERSION:
                _load_attempted = True
                _load_issue = "Predictor artifact schema is incompatible; using ratio fallback. Retrain with this cost engine."
                _logger.warning(_load_issue)
                return None
            if metadata.get("sklearn_version") != sklearn.__version__:
                _load_attempted = True
                _load_issue = (f"Predictor was trained with scikit-learn {metadata.get('sklearn_version')}; "
                               f"runtime is {sklearn.__version__}. Using ratio fallback; retrain in this environment.")
                _logger.warning(_load_issue)
                return None
            try:
                actual_hash = _sha256_file(config.PREDICTOR_FILE)
            except OSError as exc:
                _load_attempted = True
                _load_issue = f"Predictor artifact cannot be read: {exc}"
                _logger.error(_load_issue)
                return None
            if metadata.get("artifact_sha256") != actual_hash:
                _load_attempted = True
                _load_issue = "Predictor artifact does not match its metadata; using ratio fallback. Retrain the model."
                _logger.error(_load_issue)
                return None
        else:
            _load_issue = "Predictor has no version metadata; compatibility cannot be checked before loading."
            _logger.warning(_load_issue)
        _load_attempted = True
        try:
            artifact = joblib.load(config.PREDICTOR_FILE)
        except Exception as exc:
            _load_issue = f"Predictor could not be loaded ({type(exc).__name__}: {exc}); using ratio fallback."
            _logger.exception(_load_issue)
            return None
        embedded = artifact.get("metadata") if isinstance(artifact, dict) else None
        if metadata and (not isinstance(embedded, dict)
                         or embedded.get("sklearn_version") != metadata.get("sklearn_version")
                         or embedded.get("artifact_schema_version") != ARTIFACT_SCHEMA_VERSION):
            _load_issue = "Predictor embedded metadata is incompatible; using ratio fallback. Retrain the model."
            _logger.error(_load_issue)
            return None
        if not isinstance(artifact, dict) or "pipeline" not in artifact or "name" not in artifact:
            _load_issue = "Predictor artifact has an invalid structure; using ratio fallback."
            _logger.error(_load_issue)
            return None
        estimator = artifact["pipeline"].named_steps.get("est")
        # Predictions are single-row; joblib worker startup dominates the work
        # and offers no useful parallelism. This is process-local only.
        if hasattr(estimator, "n_jobs"):
            estimator.n_jobs = 1
        _load_issue = None
        _cached = artifact
        return _cached


def reload_prediction_model() -> None:
    """Invalidate the process-local model cache and retry artifact validation."""
    global _cached, _load_issue, _load_attempted
    with _model_lock:
        _cached = None
        _load_issue = None
        _load_attempted = False
    _clear_prediction_cache()


def _prediction_cache_key(art: dict, inputs: tuple) -> Optional[tuple]:
    metadata = art.get("metadata") or {}
    version = metadata.get("artifact_sha256") or metadata.get("trained_at")
    if not version:
        return None
    try:
        hash(inputs)
    except TypeError:
        return None
    return (version, *inputs)


def _predict_features(art: dict, values: dict) -> float:
    """Use the saved encoder's learned categories without allocating a DataFrame.

    The fast path is restricted to the exact training pipeline layout. Anything
    else uses sklearn's pipeline unchanged.
    """
    pipeline = art["pipeline"]
    try:
        preprocessor = pipeline.named_steps["pre"]
        estimator = pipeline.named_steps["est"]
        encoder = preprocessor.named_transformers_["cat"]
        layout_matches = (
            isinstance(preprocessor, ColumnTransformer)
            and isinstance(encoder, OneHotEncoder)
            and list(encoder.feature_names_in_) == CATEGORICAL_FEATURES
            and list(preprocessor.feature_names_in_) == FEATURES
            and len(encoder.categories_) == len(CATEGORICAL_FEATURES)
        )
        if not layout_matches:
            raise TypeError("predictor does not use the supported feature layout")
        width = sum(len(categories) for categories in encoder.categories_) + len(NUMERIC_FEATURES)
        vector = np.zeros((1, width), dtype=encoder.dtype)
        offset = 0
        for column, categories in zip(CATEGORICAL_FEATURES, encoder.categories_):
            value = values[column]
            position = int(np.searchsorted(categories, value))
            if position < len(categories) and categories[position] == value:
                vector[0, offset + position] = 1
            offset += len(categories)
        vector[0, offset:] = [values[column] for column in NUMERIC_FEATURES]
        return float(estimator.predict(vector)[0])
    except (AttributeError, KeyError, TypeError, ValueError):
        row = pd.DataFrame([values], columns=FEATURES)
        return float(pipeline.predict(row)[0])


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
    if (isinstance(input_tokens, bool) or not isinstance(input_tokens, (int, float))
            or not math.isfinite(input_tokens) or input_tokens < 0 or int(input_tokens) != input_tokens):
        raise ValueError("input_tokens must be a non-negative number")
    input_tokens = int(input_tokens)

    art = _load()
    if art is None:
        pred = int(round(config.FALLBACK_OUTPUT_RATIO * input_tokens))
        response = {
            "predicted_output_tokens": max(config.MIN_PREDICTED_OUTPUT_TOKENS, pred),
            "prediction_range": {"lower": max(0, int(pred * 0.5)), "upper": max(config.MIN_PREDICTED_OUTPUT_TOKENS, int(math.ceil(pred * 1.5)))},
            "source": "fallback_ratio",
            "warning": "No trained predictor found; using configurable ratio * input_tokens with a broad heuristic range.",
        }
        if _load_issue:
            response["warning"] = f"{_load_issue} {response['warning']}"
        return response
    cache_inputs = (input_tokens, task_type, model, complexity, prompt_text, word_count, sentence_count)
    cache_key = _prediction_cache_key(art, cache_inputs)
    with _prediction_cache_lock:
        generation = _prediction_cache_generation
        if cache_key is not None and cache_key in _prediction_cache:
            result = _prediction_cache.pop(cache_key)
            _prediction_cache[cache_key] = result
            return {**result, "prediction_range": dict(result["prediction_range"])}

    values = _build_feature_values(input_tokens, task_type, model, complexity, prompt_text, word_count, sentence_count)
    pred = _predict_features(art, values)
    metrics = (art.get("metadata") or {}).get("selected_model_metrics", {})
    if not metrics:
        try:
            report = json.loads(config.METRICS_FILE.read_text(encoding="utf-8"))
            metrics = report.get("selected_model_metrics") or report.get("models", {}).get(art["name"], {}).get("test", {})
        except (OSError, ValueError):
            metrics = {}
    mae=float(metrics.get("MAE",0) or 0)
    err=max(1, int(math.ceil(mae))) if math.isfinite(mae) else max(1,int(pred*0.25))
    center=max(config.MIN_PREDICTED_OUTPUT_TOKENS, int(round(pred)))
    response = {
        "predicted_output_tokens": center,
        "prediction_range": {"lower": max(0, center-err), "upper": center+err},
        "source": f"trained:{art['name']}",
        "training_data": art["data_source"],
        "uncertainty_method": "held_out_MAE" if mae else "heuristic_25_percent",
    }
    if cache_key is not None:
        # Coordinate with reload/train so an in-flight old model cannot repopulate
        # a cache invalidated by a newly loaded artifact.
        with _model_lock:
            if _cached is art:
                with _prediction_cache_lock:
                    if generation == _prediction_cache_generation:
                        _prediction_cache[cache_key] = {**response, "prediction_range": dict(response["prediction_range"])}
                        _prediction_cache.move_to_end(cache_key)
                        while len(_prediction_cache) > _PREDICTION_CACHE_MAXSIZE:
                            _prediction_cache.popitem(last=False)
    return response


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
