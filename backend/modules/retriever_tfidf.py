# backend/modules/retriever_tfidf.py
#
# Path A: TF-IDF based retrieval.
#
# Responsibilities:
#   1. Build a TF-IDF index from a list of chunk dicts (after upload)
#   2. Save the index to disk as pickle files
#   3. Load the index from disk on query
#   4. Query: return top-k chunks by cosine similarity
#   5. Rebuild the index (called after document deletion)
#
# All functions are stateless — they take session_id and derive
# file paths from it. No global state is held in memory.
# This is intentional: for a local single-user app it is safe,
# and it avoids memory leaks between requests.

import pickle
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import settings
from modules.session_manager import load_session, SessionNotFoundError, SessionExpiredError


# ── File path helpers ─────────────────────────────────────────────

def _tfidf_matrix_path(session_id: str) -> Path:
    return settings.sessions_dir / session_id / "tfidf_matrix.pkl"

def _vectorizer_path(session_id: str) -> Path:
    return settings.sessions_dir / session_id / "vectorizer.pkl"

def _chunks_path(session_id: str) -> Path:
    return settings.sessions_dir / session_id / "chunks.pkl"


# ── Pickle helpers ────────────────────────────────────────────────

def _save_pickle(obj: object, path: Path) -> None:
    """Serialize an object to disk using pickle."""
    with open(path, "wb") as f:
        pickle.dump(obj, f)


def _load_pickle(path: Path) -> object:
    """Deserialize an object from disk using pickle."""
    with open(path, "rb") as f:
        return pickle.load(f)


# ── Index Operations ──────────────────────────────────────────────

def build_index(session_id: str, chunks: list[dict]) -> None:
    """
    Fit a TF-IDF vectorizer on all chunk texts and save to disk.

    Called by the upload router after each PDF is processed.
    If this is not the first upload in a session, we load the
    existing chunks, merge with new ones, and re-fit from scratch.

    Why re-fit from scratch?
        TF-IDF vocabulary is corpus-wide. Adding new documents changes
        IDF weights for every term. You cannot incrementally update a
        fitted TfidfVectorizer — you must re-fit on the full corpus.
        This is a known limitation of TF-IDF vs vector databases.

    Args:
        session_id: The session this index belongs to
        chunks:     New chunks to add (from the just-uploaded PDF)
    """
    # Load existing chunks if an index already exists
    existing_chunks = []
    chunks_path     = _chunks_path(session_id)
    if chunks_path.exists():
        existing_chunks = _load_pickle(chunks_path)

    # Merge existing + new chunks
    all_chunks = existing_chunks + chunks

    # Extract text for vectorizer fitting
    texts = [chunk["text"] for chunk in all_chunks]

    # Fit TF-IDF vectorizer
    # ngram_range=(1, 2): unigrams and bigrams
    # Why bigrams? "neural network" as a bigram is more informative
    # than "neural" and "network" separately.
    # min_df=1: include all terms (small corpus — we cannot afford to drop any)
    # max_df=0.95: ignore terms that appear in >95% of chunks (stop-word effect)
    # sublinear_tf=True: apply log normalization to term frequency
    #   → prevents very long chunks from dominating scores
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
    )

    tfidf_matrix = vectorizer.fit_transform(texts)
    # tfidf_matrix shape: (num_chunks, vocab_size) — a sparse matrix

    # Save all three artifacts
    _save_pickle(tfidf_matrix, _tfidf_matrix_path(session_id))
    _save_pickle(vectorizer,   _vectorizer_path(session_id))
    _save_pickle(all_chunks,   _chunks_path(session_id))


def rebuild_index(session_id: str, remaining_chunks: list[dict]) -> None:
    """
    Re-fit TF-IDF on a reduced set of chunks after document deletion.

    Called by the document deletion router with the chunks that
    should remain (i.e., all chunks EXCEPT the deleted document's).

    If remaining_chunks is empty (last document removed),
    all pickle files are deleted — no empty index is saved.
    """
    if not remaining_chunks:
        # Clean up all pickle files
        for path in [
            _tfidf_matrix_path(session_id),
            _vectorizer_path(session_id),
            _chunks_path(session_id),
        ]:
            if path.exists():
                path.unlink()
        return

    # Re-fit from scratch on remaining chunks
    texts      = [c["text"] for c in remaining_chunks]
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    _save_pickle(tfidf_matrix, _tfidf_matrix_path(session_id))
    _save_pickle(vectorizer,   _vectorizer_path(session_id))
    _save_pickle(remaining_chunks, _chunks_path(session_id))


def query_index(
    session_id:  str,
    query_text:  str,
    document_id: str | None = None,
    top_k:       int        = None,
) -> list[dict]:
    """
    Retrieve the top-k most relevant chunks for a query.

    Steps:
        1. Load vectorizer + matrix + chunks from disk
        2. Optionally filter chunks to a specific document
        3. Vectorize the query using the SAME fitted vectorizer
        4. Compute cosine similarity between query and all chunk vectors
        5. Return top_k chunks sorted by descending similarity score

    Args:
        session_id:  The session to query
        query_text:  Raw user question string
        document_id: If provided, restrict results to this document
        top_k:       Number of chunks to return (default: settings.top_k_chunks)

    Returns:
        List of chunk dicts with an added "score" key (float, 0.0–1.0),
        sorted by descending score.

    Raises:
        FileNotFoundError: if pickle files don't exist
                           (no document uploaded yet)
    """
    top_k = top_k or settings.top_k_chunks

    # ── Load index from disk ──────────────────────────────────────
    matrix     = _load_pickle(_tfidf_matrix_path(session_id))
    vectorizer = _load_pickle(_vectorizer_path(session_id))
    all_chunks = _load_pickle(_chunks_path(session_id))

    # ── Document filter ───────────────────────────────────────────
    # If document_id is provided, work only with that document's chunks.
    # We keep track of the original indices so we can slice the matrix.
    if document_id is not None:
        filtered_indices = [
            i for i, c in enumerate(all_chunks)
            if c["document_id"] == document_id
        ]
        if not filtered_indices:
            return []   # document exists in metadata but has no chunks — edge case
        chunks_to_search = [all_chunks[i] for i in filtered_indices]
        matrix_to_search = matrix[filtered_indices]
    else:
        chunks_to_search = all_chunks
        matrix_to_search = matrix

    # ── Vectorize query ───────────────────────────────────────────
    # IMPORTANT: transform(), not fit_transform().
    # The vectorizer vocabulary was set during build_index().
    # Using fit_transform() here would create a new vocabulary
    # and produce meaningless similarity scores.
    query_vector = vectorizer.transform([query_text])

    # ── Cosine similarity ─────────────────────────────────────────
    # Returns shape (1, num_chunks) — one score per chunk
    scores = cosine_similarity(query_vector, matrix_to_search)[0]

    # ── Rank and select top_k ─────────────────────────────────────
    # argsort returns ascending order — we reverse with [::-1]
    ranked_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in ranked_indices:
        chunk = dict(chunks_to_search[idx])  # copy, don't mutate original
        chunk["score"] = float(round(scores[idx], 4))
        results.append(chunk)

    return results