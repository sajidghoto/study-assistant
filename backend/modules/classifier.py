# backend/modules/classifier.py
#
# Responsibilities:
#   1. Load the trained intent classifier from disk (once, at startup)
#   2. Predict the intent of a user query
#
# The classifier pkl file is produced by training/train_classifier.py.
# This module is read-only at runtime — it never modifies the model.

import pickle
from pathlib import Path

from config import settings


# ── Custom Exceptions ─────────────────────────────────────────────

class ClassifierNotFoundError(Exception):
    """
    Raised when intent_classifier.pkl does not exist.
    This means train_classifier.py has not been run yet.
    """
    pass


# ── Model singleton ───────────────────────────────────────────────
# Same pattern as retriever_semantic.py — load once, reuse always.

_classifier_bundle: dict | None = None


def _load_classifier() -> dict:
    """
    Load the classifier bundle from disk.

    The bundle is a dict with keys:
        "model":      trained sklearn classifier (NB or LR)
        "vectorizer": fitted CountVectorizer
        "classes":    list of intent class names
        "model_type": string name of the model class
        "trained_at": ISO datetime string

    Returns the bundle dict.
    Raises ClassifierNotFoundError if the file does not exist.
    """
    global _classifier_bundle

    if _classifier_bundle is not None:
        return _classifier_bundle

    model_path = settings.models_dir / "intent_classifier.pkl"

    if not model_path.exists():
        raise ClassifierNotFoundError(
            f"Classifier not found at {model_path}. "
            "Run backend/training/train_classifier.py first."
        )

    with open(model_path, "rb") as f:
        _classifier_bundle = pickle.load(f)

    return _classifier_bundle


# ── Public Interface ──────────────────────────────────────────────

def predict_intent(query: str) -> dict:
    """
    Classify the intent of a user query.

    Args:
        query: Raw user question string

    Returns:
        {
            "label":      str,   # "answer" | "summarise" | "out-of-scope"
            "confidence": float  # 0.0 – 1.0, probability of top class
        }

    The confidence is the model's posterior probability for the
    predicted class — directly from predict_proba().
    A confidence below 0.5 indicates the model is uncertain;
    you may choose to log these for dataset improvement.
    """
    bundle     = _load_classifier()
    model      = bundle["model"]
    vectorizer = bundle["vectorizer"]

    # Transform query using the SAME vectorizer fitted during training
    query_vector = vectorizer.transform([query])

    # predict_proba returns shape (1, num_classes)
    probabilities = model.predict_proba(query_vector)[0]

    # Get the class with highest probability
    top_index  = probabilities.argmax()
    top_label  = model.classes_[top_index]
    confidence = float(round(probabilities[top_index], 4))

    return {
        "label":      top_label,
        "confidence": confidence,
    }