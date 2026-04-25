# backend/tests/test_retriever_tfidf.py
#
# Tests for modules/retriever_tfidf.py
# Uses trained_session_tfidf fixture which builds a real TF-IDF index.

import pytest
from modules.retriever_tfidf import (
    build_index,
    rebuild_index,
    query_index,
    _chunks_path,
    _load_pickle,
)


class TestBuildIndex:

    def test_pickle_files_created(self, tmp_session_dir, sample_session, sample_chunks):
        from config import settings
        sid = sample_session["session_id"]
        build_index(session_id=sid, chunks=sample_chunks)

        session_dir = settings.sessions_dir / sid
        assert (session_dir / "tfidf_matrix.pkl").exists()
        assert (session_dir / "vectorizer.pkl").exists()
        assert (session_dir / "chunks.pkl").exists()

    def test_chunks_saved_correctly(self, tmp_session_dir, sample_session, sample_chunks):
        sid = sample_session["session_id"]
        build_index(session_id=sid, chunks=sample_chunks)

        loaded = _load_pickle(_chunks_path(sid))
        assert len(loaded) == len(sample_chunks)

    def test_second_upload_merges_chunks(
        self, tmp_session_dir, sample_session, sample_chunks, sample_chunks_2
    ):
        sid = sample_session["session_id"]
        build_index(session_id=sid, chunks=sample_chunks)
        build_index(session_id=sid, chunks=sample_chunks_2)

        loaded = _load_pickle(_chunks_path(sid))
        assert len(loaded) == len(sample_chunks) + len(sample_chunks_2)


class TestQueryIndex:

    def test_returns_list(self, trained_session_tfidf):
        meta, chunks = trained_session_tfidf
        results = query_index(
            session_id=meta["session_id"],
            query_text="What is backpropagation?"
        )
        assert isinstance(results, list)

    def test_returns_correct_number_of_chunks(self, trained_session_tfidf):
        meta, chunks = trained_session_tfidf
        results = query_index(
            session_id=meta["session_id"],
            query_text="neural network training",
            top_k=3,
        )
        assert len(results) <= 3

    def test_each_result_has_score_key(self, trained_session_tfidf):
        meta, _ = trained_session_tfidf
        results = query_index(
            session_id=meta["session_id"],
            query_text="backpropagation gradient"
        )
        for r in results:
            assert "score" in r
            assert 0.0 <= r["score"] <= 1.0

    def test_results_sorted_descending_by_score(self, trained_session_tfidf):
        meta, _ = trained_session_tfidf
        results = query_index(
            session_id=meta["session_id"],
            query_text="backpropagation gradient descent"
        )
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), (
            "Results not sorted by descending score"
        )

    def test_document_filter_returns_only_that_document(
        self, tmp_session_dir, sample_session, sample_chunks, sample_chunks_2
    ):
        sid = sample_session["session_id"]
        build_index(session_id=sid, chunks=sample_chunks)
        build_index(session_id=sid, chunks=sample_chunks_2)

        results = query_index(
            session_id=sid,
            query_text="neural network",
            document_id="doc_test01",
        )
        for r in results:
            assert r["document_id"] == "doc_test01", (
                f"Expected doc_test01 but got {r['document_id']}"
            )

    def test_nonexistent_document_filter_returns_empty(
        self, trained_session_tfidf
    ):
        meta, _ = trained_session_tfidf
        results = query_index(
            session_id=meta["session_id"],
            query_text="backpropagation",
            document_id="doc_doesnotexist",
        )
        assert results == []

    def test_relevant_query_scores_higher_than_irrelevant(
        self, trained_session_tfidf
    ):
        meta, _ = trained_session_tfidf

        # This query contains words that appear in SAMPLE_TEXT
        relevant_results = query_index(
            session_id=meta["session_id"],
            query_text="backpropagation gradient loss",
        )
        # This query contains no words from SAMPLE_TEXT
        irrelevant_results = query_index(
            session_id=meta["session_id"],
            query_text="pizza recipe tomato sauce",
        )

        if relevant_results and irrelevant_results:
            assert relevant_results[0]["score"] >= irrelevant_results[0]["score"]


class TestRebuildIndex:

    def test_rebuild_removes_deleted_document_chunks(
        self, tmp_session_dir, sample_session, sample_chunks, sample_chunks_2
    ):
        sid = sample_session["session_id"]
        build_index(session_id=sid, chunks=sample_chunks)
        build_index(session_id=sid, chunks=sample_chunks_2)

        # Rebuild with only sample_chunks (doc_test01 only)
        rebuild_index(session_id=sid, remaining_chunks=sample_chunks)

        loaded = _load_pickle(_chunks_path(sid))
        doc_ids = {c["document_id"] for c in loaded}

        assert "doc_test01" in doc_ids
        assert "doc_test02" not in doc_ids

    def test_rebuild_with_empty_list_removes_pickle_files(
        self, tmp_session_dir, sample_session, sample_chunks
    ):
        from config import settings
        sid = sample_session["session_id"]
        build_index(session_id=sid, chunks=sample_chunks)

        rebuild_index(session_id=sid, remaining_chunks=[])

        session_dir = settings.sessions_dir / sid
        assert not (session_dir / "tfidf_matrix.pkl").exists()
        assert not (session_dir / "vectorizer.pkl").exists()
        assert not (session_dir / "chunks.pkl").exists()