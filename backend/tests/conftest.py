# backend/tests/conftest.py
#
# Shared pytest fixtures available to ALL test files automatically.
# pytest discovers this file by name — do not rename it.
#
# A fixture is a reusable setup function. Instead of copy-pasting
# setup code into every test, you declare it here once and inject
# it by name into any test function that needs it.

import pickle
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ── We patch config BEFORE importing app ──────────────────────────
# The app reads settings at import time. We need to point it at
# a temporary directory so tests don't write to real data/.
# This is done via monkeypatching in individual fixtures below.


# ── Minimal sample text for PDF-free testing ──────────────────────
SAMPLE_TEXT = """
Neural networks are computational models inspired by biological brains.
They consist of layers of interconnected nodes called neurons.
Each neuron applies a weighted sum followed by an activation function.
Backpropagation is the algorithm used to train neural networks.
It computes the gradient of the loss function with respect to each weight.
The gradient descent optimizer adjusts weights to minimize the loss.
Deep learning refers to neural networks with many hidden layers.
Convolutional neural networks are used for image recognition tasks.
Recurrent neural networks process sequential data like text and time series.
The vanishing gradient problem occurs when gradients become very small.
Batch normalization helps stabilize training and accelerates convergence.
Dropout is a regularization technique that randomly disables neurons.
Transfer learning reuses a pretrained model for a new but related task.
The softmax function converts logits into a probability distribution.
Cross-entropy loss measures the difference between predicted and true distributions.
""".strip()

SAMPLE_TEXT_2 = """
Machine learning is the study of algorithms that improve through experience.
Supervised learning uses labelled examples to train predictive models.
Classification assigns discrete labels to input examples.
Regression predicts continuous numerical values.
Decision trees split data based on feature thresholds.
Random forests combine many decision trees to reduce overfitting.
Support vector machines find the maximum-margin hyperplane between classes.
K-nearest neighbours classifies based on the most similar training examples.
Feature engineering transforms raw data into informative representations.
Model evaluation uses metrics like accuracy, precision, recall, and F1 score.
""".strip()


# ── Session directory fixture ─────────────────────────────────────

@pytest.fixture
def tmp_session_dir(tmp_path, monkeypatch):
    """
    Redirect all session storage to a temporary directory.
    Automatically cleaned up after each test.

    Monkeypatches:
      config.settings.sessions_dir → tmp_path/sessions
      config.settings.chromadb_dir → tmp_path/chromadb
      config.settings.models_dir   → tmp_path/models
    """
    sessions_dir = tmp_path / "sessions"
    chromadb_dir = tmp_path / "chromadb"
    models_dir   = tmp_path / "models"

    sessions_dir.mkdir()
    chromadb_dir.mkdir()
    models_dir.mkdir()

    # Import after directory creation
    from config import settings
    monkeypatch.setattr(settings, "sessions_dir", sessions_dir)
    monkeypatch.setattr(settings, "chromadb_dir", chromadb_dir)
    monkeypatch.setattr(settings, "models_dir",   models_dir)

    return tmp_path


@pytest.fixture
def sample_session(tmp_session_dir):
    """
    Create a real session on disk and return its metadata.
    Depends on tmp_session_dir to ensure correct paths.
    """
    from modules.session_manager import create_session
    return create_session()


@pytest.fixture
def sample_chunks():
    """
    Return a list of chunk dicts built from SAMPLE_TEXT.
    Does not touch disk — pure in-memory fixture.
    """
    from modules.pdf_parser import chunk_text
    return chunk_text(
        text=SAMPLE_TEXT,
        session_id="sess_test01",
        document_id="doc_test01",
        document_name="test_lecture.pdf",
        chunk_size=50,    # small for fast tests
        overlap=10,
    )


@pytest.fixture
def sample_chunks_2():
    """Second document's chunks — for multi-document tests."""
    from modules.pdf_parser import chunk_text
    return chunk_text(
        text=SAMPLE_TEXT_2,
        session_id="sess_test01",
        document_id="doc_test02",
        document_name="test_ml.pdf",
        chunk_size=50,
        overlap=10,
    )


@pytest.fixture
def trained_session_tfidf(tmp_session_dir, sample_session, sample_chunks):
    """
    A session with a TF-IDF index already built.
    Returns (session_metadata, chunks).
    """
    from modules.retriever_tfidf import build_index
    from modules.session_manager import add_document_to_session

    session_id = sample_session["session_id"]

    build_index(session_id=session_id, chunks=sample_chunks)
    add_document_to_session(
        session_id=session_id,
        document_id="doc_test01",
        document_name="test_lecture.pdf",
        chunk_count=len(sample_chunks),
        page_count=3,
    )

    return sample_session, sample_chunks


@pytest.fixture
def mock_classifier_bundle(tmp_session_dir):
    """
    Train a real (tiny) classifier on the standard 60-example dataset
    and save it to the temp models dir.

    This is a real sklearn model, not a mock. We train it fresh for
    each test run that needs it — the dataset is small enough that
    training takes < 1 second.
    """
    import pandas as pd
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from datetime import datetime, timezone
    from config import settings

    dataset_path = Path(__file__).parent.parent / "training" / "intent_dataset.csv"

    if not dataset_path.exists():
        pytest.skip("intent_dataset.csv not found — skipping classifier tests")

    df = pd.read_csv(dataset_path)
    X, y = df["query"].tolist(), df["intent"].tolist()

    vectorizer = CountVectorizer(ngram_range=(1, 2))
    X_vec = vectorizer.fit_transform(X)

    model = MultinomialNB(alpha=1.0)
    model.fit(X_vec, y)

    bundle = {
        "model":      model,
        "vectorizer": vectorizer,
        "classes":    list(model.classes_),
        "model_type": "MultinomialNB",
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    model_path = settings.models_dir / "intent_classifier.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(bundle, f)

    # Reset the singleton so it reloads from the new temp path
    import modules.classifier as clf_module
    clf_module._classifier_bundle = None

    return bundle


@pytest.fixture
def api_client(tmp_session_dir, mock_classifier_bundle):
    """
    FastAPI TestClient with all storage redirected to tmp_path.
    Use this for integration/API tests.

    Why not use requests against a running server?
    TestClient runs the app in-process — no server needed,
    tests are faster, and failures give full Python tracebacks.
    """
    from app import app
    return TestClient(app)