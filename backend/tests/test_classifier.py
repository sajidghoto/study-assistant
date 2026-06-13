# backend/tests/test_classifier.py
#
# Tests for modules/classifier.py
# Uses mock_classifier_bundle fixture which trains a real model
# into the temp models directory.

import pytest
from modules.classifier import (
    predict_intent,
    ClassifierNotFoundError,
    _load_classifier,
)


class TestLoadClassifier:

    def test_loads_successfully_when_model_exists(
        self, tmp_session_dir, mock_classifier_bundle
    ):
        import modules.classifier as clf
        clf._classifier_bundle = None  # force reload
        bundle = _load_classifier()
        assert bundle is not None
        assert "model"      in bundle
        assert "vectorizer" in bundle
        assert "classes"    in bundle

    def test_raises_when_model_missing(self, tmp_session_dir):
        import modules.classifier as clf
        clf._classifier_bundle = None  # clear singleton

        # No model file in temp dir
        with pytest.raises(ClassifierNotFoundError):
            _load_classifier()

    def test_singleton_loaded_once(self, tmp_session_dir, mock_classifier_bundle):
        import modules.classifier as clf
        clf._classifier_bundle = None

        b1 = _load_classifier()
        b2 = _load_classifier()
        assert b1 is b2, "Classifier was loaded from disk twice — singleton broken"


class TestPredictIntent:

    # ── Answer intent ──────────────────────────────────────────────

    def test_answer_query_returns_answer_label(
        self, tmp_session_dir, mock_classifier_bundle
    ):
        import modules.classifier as clf
        clf._classifier_bundle = None
        result = predict_intent("What is backpropagation?")
        assert result["label"] == "answer"

    def test_answer_query_confidence_is_float(
        self, tmp_session_dir, mock_classifier_bundle
    ):
        import modules.classifier as clf
        clf._classifier_bundle = None
        result = predict_intent("Define gradient descent")
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0

    # ── Summarise intent ───────────────────────────────────────────

    def test_summarise_query_returns_summarise_label(
        self, tmp_session_dir, mock_classifier_bundle
    ):
        import modules.classifier as clf
        clf._classifier_bundle = None
        result = predict_intent("Give me an overview of this document")
        assert result["label"] == "summarise"

    def test_summarise_variation_classified_correctly(
        self, tmp_session_dir, mock_classifier_bundle
    ):
        import modules.classifier as clf
        clf._classifier_bundle = None
        result = predict_intent("Summarize the chapter on neural networks")
        assert result["label"] == "summarise"

    # ── Response structure ─────────────────────────────────────────

    def test_response_always_has_label_and_confidence(
        self, tmp_session_dir, mock_classifier_bundle
    ):
        import modules.classifier as clf
        clf._classifier_bundle = None
        for query in [
            "What is dropout?",
            "Summarize the notes",
            "What is the weather?",
        ]:
            result = predict_intent(query)
            assert "label"      in result
            assert "confidence" in result

    def test_label_is_always_valid_class(
        self, tmp_session_dir, mock_classifier_bundle
    ):
        import modules.classifier as clf
        clf._classifier_bundle = None
        valid_labels = {"answer", "explain", "summarise", "compare", "quiz"}
        for query in ["What is ReLU?", "Give overview", "Tell me a joke"]:
            result = predict_intent(query)
            assert result["label"] in valid_labels