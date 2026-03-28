# backend/training/train_classifier.py
#
# Run this script ONCE to train the intent classifier.
# It produces backend/models/intent_classifier.pkl
#
# Usage (from backend/ directory with venv active):
#   python training/train_classifier.py
#
# Outputs:
#   models/intent_classifier.pkl
#   evaluation/results/confusion_matrix.png
#   evaluation/results/classification_report.txt
#   evaluation/results/model_comparison.csv

import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy  as np
import pandas as pd
import seaborn as sns
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model            import LogisticRegression
from sklearn.metrics                 import (
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection         import cross_val_score, train_test_split
from sklearn.naive_bayes             import MultinomialNB

# ── Path setup ────────────────────────────────────────────────────
# Script can be run from any directory — paths are always relative
# to the backend/ folder (parent of training/).
BACKEND_DIR  = Path(__file__).parent.parent
DATASET_PATH = BACKEND_DIR / "training" / "intent_dataset.csv"
MODELS_DIR   = BACKEND_DIR / "models"
RESULTS_DIR  = BACKEND_DIR / "evaluation" / "results"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset() -> tuple[list[str], list[str]]:
    """Load and validate the intent dataset CSV."""
    if not DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        sys.exit(1)

    df = pd.read_csv(DATASET_PATH)

    required_cols = {"query", "intent"}
    if not required_cols.issubset(df.columns):
        print(f"ERROR: CSV must have columns: {required_cols}")
        sys.exit(1)

    print(f"Dataset loaded: {len(df)} examples")
    print(f"Class distribution:\n{df['intent'].value_counts()}\n")

    return df["query"].tolist(), df["intent"].tolist()


def train_and_evaluate() -> None:
    """
    Full training pipeline:
    1. Load dataset
    2. Train/test split (80/20, stratified)
    3. Fit CountVectorizer
    4. Train MultinomialNB + LogisticRegression
    5. 5-fold cross-validation for both
    6. Evaluate on held-out test set
    7. Save best model
    8. Save all evaluation artefacts
    """

    # ── 1. Load data ──────────────────────────────────────────────
    X, y = load_dataset()

    # ── 2. Train/test split ───────────────────────────────────────
    # stratify=y ensures each split has proportional class counts
    # random_state=42 makes the split reproducible
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )
    print(f"Train: {len(X_train)} | Test: {len(X_test)}\n")

    # ── 3. Fit vectorizer on TRAINING data only ───────────────────
    # NEVER fit on test data — that is data leakage.
    # ngram_range=(1,2): unigrams + bigrams
    # Why CountVectorizer and not TfidfVectorizer?
    #   MultinomialNB works with non-negative integer counts.
    #   TF-IDF produces floats scaled differently — counts work better here.
    vectorizer = CountVectorizer(ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec  = vectorizer.transform(X_test)    # transform only, not fit

    # ── 4. Define models ──────────────────────────────────────────
    nb_model = MultinomialNB(alpha=1.0)           # alpha = Laplace smoothing
    lr_model = LogisticRegression(
        max_iter=1000,                            # enough for small datasets
        random_state=42,
        C=1.0,                                    # default regularisation
    )

    # ── 5. Cross-validation (on training set) ────────────────────
    print("=" * 55)
    print("5-FOLD CROSS-VALIDATION (on training set)")
    print("=" * 55)

    for name, model in [("MultinomialNB", nb_model), ("LogisticRegression", lr_model)]:
        cv_scores = cross_val_score(
            model, X_train_vec, y_train,
            cv=5, scoring="f1_weighted"
        )
        print(
            f"{name:25s} | "
            f"CV F1: {cv_scores.mean():.3f} "
            f"(±{cv_scores.std():.3f})"
        )
    print()

    # ── 6. Train both models on full training set ─────────────────
    nb_model.fit(X_train_vec, y_train)
    lr_model.fit(X_train_vec, y_train)

    # ── 7. Evaluate on held-out test set ─────────────────────────
    nb_preds = nb_model.predict(X_test_vec)
    lr_preds = lr_model.predict(X_test_vec)

    nb_f1 = f1_score(y_test, nb_preds, average="weighted")
    lr_f1 = f1_score(y_test, lr_preds, average="weighted")

    print("=" * 55)
    print("TEST SET RESULTS")
    print("=" * 55)
    print(f"\nMultinomialNB       F1 (weighted): {nb_f1:.3f}")
    print(f"LogisticRegression  F1 (weighted): {lr_f1:.3f}\n")

    print("── MultinomialNB Classification Report ──")
    print(classification_report(y_test, nb_preds))

    print("── LogisticRegression Classification Report ──")
    print(classification_report(y_test, lr_preds))

    # ── 8. Select the best model ──────────────────────────────────
    if nb_f1 >= lr_f1:
        best_model      = nb_model
        best_model_name = "MultinomialNB"
        best_preds      = nb_preds
        print(f"Winner: MultinomialNB (F1={nb_f1:.3f})")
    else:
        best_model      = lr_model
        best_model_name = "LogisticRegression"
        best_preds      = lr_preds
        print(f"Winner: LogisticRegression (F1={lr_f1:.3f})")

    # ── 9. Save classifier bundle ─────────────────────────────────
    bundle = {
        "model":      best_model,
        "vectorizer": vectorizer,
        "classes":    list(best_model.classes_),
        "model_type": best_model_name,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    model_path = MODELS_DIR / "intent_classifier.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(bundle, f)
    print(f"\nModel saved → {model_path}")

    # ── 10. Save evaluation artefacts ────────────────────────────

    # Confusion matrix plot
    _save_confusion_matrix(y_test, best_preds, best_model.classes_)

    # Classification report text
    report_text = (
        f"Model: {best_model_name}\n"
        f"Trained at: {bundle['trained_at']}\n\n"
        f"MultinomialNB F1:      {nb_f1:.3f}\n"
        f"LogisticRegression F1: {lr_f1:.3f}\n\n"
        f"── {best_model_name} (Selected) ──\n"
        + classification_report(y_test, best_preds)
    )
    report_path = RESULTS_DIR / "classification_report.txt"
    report_path.write_text(report_text, encoding="utf-8")
    print(f"Report saved → {report_path}")

    # Model comparison CSV
    comparison = pd.DataFrame({
        "model":           ["MultinomialNB", "LogisticRegression"],
        "test_f1_weighted": [round(nb_f1, 4), round(lr_f1, 4)],
        "selected":        [nb_f1 >= lr_f1, lr_f1 > nb_f1],
    })
    comparison_path = RESULTS_DIR / "model_comparison.csv"
    comparison.to_csv(comparison_path, index=False)
    print(f"Comparison saved → {comparison_path}")

    print("\nTraining complete.")


def _save_confusion_matrix(
    y_true, y_pred, classes
) -> None:
    """Save a styled confusion matrix heatmap as PNG."""
    cm = confusion_matrix(y_true, y_pred, labels=classes)

    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=classes,
        yticklabels=classes,
        ax=ax,
    )
    ax.set_xlabel("Predicted Label", fontsize=12)
    ax.set_ylabel("True Label",      fontsize=12)
    ax.set_title("Intent Classifier — Confusion Matrix", fontsize=14)
    plt.tight_layout()

    path = RESULTS_DIR / "confusion_matrix.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Confusion matrix saved → {path}")


if __name__ == "__main__":
    train_and_evaluate()