import pytest
from fastapi import HTTPException

from modules.session_manager import add_document_to_session, create_session, load_session
from routers import documents


@pytest.fixture
def session_with_two_documents(tmp_session_dir):
    metadata = create_session()
    session_id = metadata["session_id"]
    add_document_to_session(
        session_id,
        "doc_removed",
        "removed.pdf",
        chunk_count=2,
        page_count=1,
    )
    add_document_to_session(
        session_id,
        "doc_kept",
        "kept.pdf",
        chunk_count=3,
        page_count=1,
    )
    return session_id


def test_semantic_delete_passes_remaining_document_ids_and_updates_metadata(
    monkeypatch,
    session_with_two_documents,
):
    session_id = session_with_two_documents
    calls = []
    monkeypatch.setattr(documents.settings, "retrieval_mode", "semantic")
    monkeypatch.setattr(
        documents,
        "retain_documents",
        lambda sid, document_ids: calls.append((sid, document_ids)),
        raising=False,
    )

    result = documents.delete_document(session_id, "doc_removed")

    assert calls == [(session_id, ["doc_kept"])]
    updated = load_session(session_id)
    assert [doc["document_id"] for doc in updated["documents"]] == ["doc_kept"]
    assert updated["total_chunk_count"] == 3
    assert result["data"]["removed_document"] == "removed.pdf"


def test_index_update_failure_does_not_remove_document_metadata(
    monkeypatch,
    session_with_two_documents,
):
    session_id = session_with_two_documents

    def fail_index_update(*args):
        raise RuntimeError("simulated ChromaDB failure")

    monkeypatch.setattr(documents.settings, "retrieval_mode", "semantic")
    monkeypatch.setattr(
        documents,
        "retain_documents",
        fail_index_update,
        raising=False,
    )

    with pytest.raises(HTTPException) as exc_info:
        documents.delete_document(session_id, "doc_removed")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail["error"]["code"] == "INDEX_UPDATE_FAILED"
    updated = load_session(session_id)
    assert {doc["document_id"] for doc in updated["documents"]} == {
        "doc_removed",
        "doc_kept",
    }
