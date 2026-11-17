import sys
from types import SimpleNamespace

import numpy as np
import pytest

from nlp_engine import semantic_similarity as semantic


@pytest.fixture(autouse=True)
def reset_semantic_state(monkeypatch):
    semantic._cached_model = None
    semantic._model_load_attempted = False

    monkeypatch.delenv(semantic.ENABLE_ENV, raising=False)
    monkeypatch.delenv(semantic.MODEL_ENV, raising=False)
    monkeypatch.delenv(semantic.DEVICE_ENV, raising=False)

    yield

    semantic._cached_model = None
    semantic._model_load_attempted = False


class FakeModel:
    def __init__(self, embeddings=None, error=None):
        self.embeddings = embeddings
        self.error = error
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((texts, kwargs))

        if self.error:
            raise self.error

        return self.embeddings


def install_fake_sentence_transformers(monkeypatch, model=None, error=None):
    class FakeSentenceTransformer:
        def __init__(self, model_name, device):
            if error:
                raise error

            self.model_name = model_name
            self.device = device

    fake_module = SimpleNamespace(
        SentenceTransformer=FakeSentenceTransformer
    )

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        fake_module,
    )

    return fake_module


def test_model_is_disabled_by_default():
    assert semantic.semantic_model_enabled() is False
    assert semantic.get_semantic_model() is None


def test_disabled_model_does_not_prevent_later_enablement(monkeypatch):
    assert semantic.get_semantic_model() is None

    monkeypatch.setenv(semantic.ENABLE_ENV, "true")
    install_fake_sentence_transformers(monkeypatch)

    model = semantic.get_semantic_model()

    assert model is not None
    assert model.device == "cpu"


def test_model_loads_only_once(monkeypatch):
    monkeypatch.setenv(semantic.ENABLE_ENV, "true")
    install_fake_sentence_transformers(monkeypatch)

    first = semantic.get_semantic_model()
    second = semantic.get_semantic_model()

    assert first is second


def test_custom_model_and_device_are_used(monkeypatch):
    monkeypatch.setenv(semantic.ENABLE_ENV, "true")
    monkeypatch.setenv(semantic.MODEL_ENV, "custom-test-model")
    monkeypatch.setenv(semantic.DEVICE_ENV, "cuda")

    install_fake_sentence_transformers(monkeypatch)

    model = semantic.get_semantic_model()

    assert model is not None
    assert model.model_name == "custom-test-model"
    assert model.device == "cuda"


def test_model_load_failure_returns_none(monkeypatch):
    monkeypatch.setenv(semantic.ENABLE_ENV, "true")

    install_fake_sentence_transformers(
        monkeypatch,
        error=RuntimeError("model load failed"),
    )

    assert semantic.get_semantic_model() is None


def test_missing_optional_dependency_returns_none(monkeypatch):
    monkeypatch.setenv(semantic.ENABLE_ENV, "true")
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)

    assert semantic.get_semantic_model() is None


def test_injected_model_returns_cosine_similarity():
    model = FakeModel(
        embeddings=[
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
        ]
    )

    result = semantic.semantic_similarity_matrix(
        ["first sentence", "second sentence", "third sentence"],
        model=model,
    )

    assert result is not None
    assert result.shape == (3, 3)
    assert np.allclose(np.diag(result), 1.0)
    assert result[0, 1] == pytest.approx(0.0)
    assert result[0, 2] == pytest.approx(1 / np.sqrt(2))


def test_injected_model_bypasses_environment_flag():
    model = FakeModel(
        embeddings=[
            [1.0, 0.0],
            [0.0, 1.0],
        ]
    )

    result = semantic.semantic_similarity_matrix(
        ["first", "second"],
        model=model,
    )

    assert result is not None


def test_encode_failure_returns_none():
    model = FakeModel(error=RuntimeError("encoding failed"))

    result = semantic.semantic_similarity_matrix(
        ["first", "second"],
        model=model,
    )

    assert result is None


@pytest.mark.parametrize(
    "embeddings",
    [
        [1.0, 0.0],
        [[1.0, 0.0]],
        [[float("nan"), 0.0], [0.0, 1.0]],
        [[0.0, 0.0], [0.0, 1.0]],
        [[1.0, 0.0], [1.0]],
    ],
)
def test_invalid_embeddings_return_none(embeddings):
    model = FakeModel(embeddings=embeddings)

    result = semantic.semantic_similarity_matrix(
        ["first", "second"],
        model=model,
    )

    assert result is None


@pytest.mark.parametrize(
    "texts",
    [
        [],
        ["only one"],
        ["first", "   "],
        ["first", None],
    ],
)
def test_invalid_text_inputs_return_none(texts):
    model = FakeModel(
        embeddings=[
            [1.0, 0.0],
            [0.0, 1.0],
        ]
    )

    result = semantic.semantic_similarity_matrix(
        texts,
        model=model,
    )

    assert result is None
