from concurrent.futures import ThreadPoolExecutor

import pytest

from cost_engine import prediction


@pytest.fixture(autouse=True)
def clear_prediction_cache():
    prediction._clear_prediction_cache()
    yield
    prediction._clear_prediction_cache()


def _trained_artifact():
    artifact = prediction._load()
    if artifact is None:
        pytest.skip("runtime-compatible trained predictor is not available")
    return artifact


def test_fast_prediction_matches_saved_pipeline_output():
    artifact = _trained_artifact()
    cases = [
        (1_200, "summarization", "gpt-4o", None, None, None, None),
        (301, "unseen-task", "unseen-model", 2, "Summarize this carefully.", None, None),
        (9_000, None, None, 5, "", 50, 4),
    ]
    for args in cases:
        tokens, task, model, complexity, prompt, words, sentences = args
        values = prediction._build_feature_values(tokens, task, model, complexity, prompt, words, sentences)
        expected = float(artifact["pipeline"].predict(prediction.build_feature_row(*args))[0])
        actual = prediction._predict_features(artifact, values)
        assert actual == pytest.approx(expected, abs=1e-10)


def test_public_and_cached_outputs_match_pre_optimization_pipeline():
    artifact = _trained_artifact()
    args = (1_200, "summarization", "gpt-4o", None, "Summarize this text.", None, None)
    legacy_value = float(artifact["pipeline"].predict(prediction.build_feature_row(*args))[0])
    legacy_center = max(prediction.config.MIN_PREDICTED_OUTPUT_TOKENS, int(round(legacy_value)))
    uncached = prediction.predict_output_tokens(*args)
    cached = prediction.predict_output_tokens(*args)
    assert uncached["predicted_output_tokens"] == legacy_center
    assert uncached == cached


def test_identical_valid_predictions_are_cached_and_return_detached_results(monkeypatch):
    _trained_artifact()
    calls = 0
    original = prediction._predict_features

    def counted(*args):
        nonlocal calls
        calls += 1
        return original(*args)

    monkeypatch.setattr(prediction, "_predict_features", counted)
    first = prediction.predict_output_tokens(1_200, task_type="summarization", model="gpt-4o")
    first["prediction_range"]["lower"] = -999
    second = prediction.predict_output_tokens(1_200, task_type="summarization", model="gpt-4o")
    assert calls == 1
    assert second["prediction_range"]["lower"] >= 0


def test_prediction_cache_key_includes_every_prediction_argument(monkeypatch):
    _trained_artifact()
    calls = 0
    original = prediction._predict_features

    def counted(*args):
        nonlocal calls
        calls += 1
        return original(*args)

    monkeypatch.setattr(prediction, "_predict_features", counted)
    prediction.predict_output_tokens(1_200, task_type="summarization", model="gpt-4o")
    prediction.predict_output_tokens(1_201, task_type="summarization", model="gpt-4o")
    prediction.predict_output_tokens(1_200, task_type="analysis", model="gpt-4o")
    prediction.predict_output_tokens(1_200, task_type="summarization", model="gpt-4o", complexity=2)
    prediction.predict_output_tokens(1_200, task_type="summarization", model="gpt-4o", prompt_text="write a summary")
    prediction.predict_output_tokens(1_200, task_type="summarization", model="gpt-4o", word_count=20)
    prediction.predict_output_tokens(1_200, task_type="summarization", model="gpt-4o", sentence_count=2)
    assert calls == 7


def test_prediction_cache_is_bounded_and_invalidated_by_reload():
    _trained_artifact()
    for tokens in range(prediction._PREDICTION_CACHE_MAXSIZE):
        prediction.predict_output_tokens(tokens, task_type="summarization", model="gpt-4o")
    assert len(prediction._prediction_cache) == prediction._PREDICTION_CACHE_MAXSIZE
    artifact = prediction._cached
    oldest_key = prediction._prediction_cache_key(
        artifact, (0, "summarization", "gpt-4o", None, None, None, None)
    )
    next_oldest_key = prediction._prediction_cache_key(
        artifact, (1, "summarization", "gpt-4o", None, None, None, None)
    )
    assert oldest_key in prediction._prediction_cache
    prediction.predict_output_tokens(0, task_type="summarization", model="gpt-4o")
    prediction.predict_output_tokens(99_999, task_type="summarization", model="gpt-4o")
    assert oldest_key in prediction._prediction_cache
    assert next_oldest_key not in prediction._prediction_cache
    changed_version = {**artifact, "metadata": {**artifact["metadata"], "artifact_sha256": "new-model-version"}}
    assert prediction._prediction_cache_key(changed_version, (0, "summarization", "gpt-4o", None, None, None, None)) != oldest_key
    prediction.reload_prediction_model()
    assert not prediction._prediction_cache


def test_invalid_input_is_rejected_before_prediction_cache_lookup():
    with pytest.raises(ValueError, match="input_tokens"):
        prediction.predict_output_tokens(-1)
    with pytest.raises(ValueError, match="input_tokens"):
        prediction.predict_output_tokens(True)
    assert not prediction._prediction_cache


def test_fallback_predictions_are_not_cached(monkeypatch):
    monkeypatch.setattr(prediction, "_load", lambda: None)
    prediction.predict_output_tokens(1_200)
    prediction.predict_output_tokens(1_200)
    assert not prediction._prediction_cache


def test_concurrent_identical_predictions_are_consistent():
    _trained_artifact()
    args = dict(task_type="summarization", model="gpt-4o", prompt_text="Summarize this paragraph.")
    with ThreadPoolExecutor(max_workers=8) as pool:
        outputs = list(pool.map(lambda _: prediction.predict_output_tokens(600, **args), range(64)))
    assert all(output == outputs[0] for output in outputs)
