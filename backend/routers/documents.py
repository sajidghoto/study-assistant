# backend/routers/documents.py
#
# Handles document listing and deletion:
#   GET    /session/{session_id}/documents
#   DELETE /session/{session_id}/document/{document_id}

from fastapi import APIRouter, HTTPException

from config import settings
from modules.session_manager import (
    load_session,
    remove_document_from_session,
    get_session_documents,
    SessionNotFoundError,
    SessionExpiredError,
)

# ── Import correct retriever for rebuild after deletion ───────────
if settings.retrieval_mode == "semantic":
    from modules.retriever_semantic import rebuild_index
    from modules.retriever_semantic import query_index  # used to load all chunks
else:
    from modules.retriever_tfidf import rebuild_index
    from modules.retriever_tfidf import _load_pickle, _chunks_path  # type: ignore


router = APIRouter(tags=["Documents"])


# ── Shared session guard ──────────────────────────────────────────
# DRY helper used by both endpoints below.

def _guard_session(session_id: str) -> dict:
    """Load session or raise appropriate HTTPException."""
    try:
        return load_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code":    "SESSION_NOT_FOUND",
                    "message": "Session not found.",
                    "detail":  f"session_id '{session_id}'",
                }
            }
        )
    except SessionExpiredError:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code":    "SESSION_EXPIRED",
                    "message": "Your session has expired. Please start a new session.",
                    "detail":  f"session_id '{session_id}'",
                }
            }
        )


# ── GET /session/{session_id}/documents ───────────────────────────

@router.get("/session/{session_id}/documents", status_code=200)
def list_documents(session_id: str) -> dict:
    """
    List all documents uploaded in a session.

    Used by the frontend to populate the document filter dropdown
    and the uploaded documents sidebar.
    """
    _guard_session(session_id)

    documents, total_chunks = get_session_documents(session_id)

    serialized_docs = [
        {
            "document_id":   doc["document_id"],
            "document_name": doc["document_name"],
            "uploaded_at":   doc["uploaded_at"].isoformat(),
            "chunk_count":   doc["chunk_count"],
            "page_count":    doc["page_count"],
        }
        for doc in documents
    ]

    return {
        "success": True,
        "data": {
            "documents":    serialized_docs,
            "total_chunks": total_chunks,
        }
    }


# ── DELETE /session/{session_id}/document/{document_id} ───────────

@router.delete(
    "/session/{session_id}/document/{document_id}",
    status_code=200
)
def delete_document(session_id: str, document_id: str) -> dict:
    """
    Remove a single document from the session.

    Steps:
        1. Validate session exists
        2. Remove document from metadata
        3. Rebuild retrieval index without the removed document
        4. Return updated session summary

    Why rebuild the index on deletion?
        Path A (TF-IDF): The TF-IDF matrix cannot be updated
        incrementally. We must re-fit on remaining chunks.

        Path B (ChromaDB): Deletion by ID is supported natively —
        no full rebuild required (handled inside rebuild_index).
    """
    metadata = _guard_session(session_id)

    # ── Verify document belongs to this session ───────────────────
    doc_ids = [d["document_id"] for d in metadata["documents"]]
    if document_id not in doc_ids:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code":    "DOCUMENT_NOT_FOUND",
                    "message": "Document not found in this session.",
                    "detail":  f"document_id '{document_id}' not in session '{session_id}'",
                }
            }
        )

    # Get name before removing (needed for response message)
    doc_name = next(
        d["document_name"] for d in metadata["documents"]
        if d["document_id"] == document_id
    )

    # ── Remove from metadata ──────────────────────────────────────
    try:
        updated_metadata = remove_document_from_session(session_id, document_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code":    "DOCUMENT_NOT_FOUND",
                    "message": "Document not found.",
                    "detail":  str(exc),
                }
            }
        )

    # ── Rebuild retrieval index ───────────────────────────────────
    # Get all remaining chunks EXCEPT the deleted document's.
    # For TF-IDF: load chunks.pkl, filter by document_id.
    # For Semantic: rebuild_index handles deletion internally.
    try:
        if settings.retrieval_mode == "tfidf":
            chunks_path = _chunks_path(session_id)
            if chunks_path.exists():
                all_chunks = _load_pickle(chunks_path)
                remaining  = [
                    c for c in all_chunks
                    if c["document_id"] != document_id
                ]
                rebuild_index(session_id, remaining)
        else:
            # For semantic: pass remaining chunk IDs
            # rebuild_index derives what to delete internally
            remaining_docs = updated_metadata["documents"]
            remaining_ids  = {d["document_id"] for d in remaining_docs}
            # Pass empty remaining_chunks — rebuild_index for semantic
            # uses the collection directly to find what to delete
            rebuild_index(session_id, [])

    except Exception as exc:
        # Index rebuild failure is logged but does not fail the request.
        # The metadata has already been updated. The index is stale but
        # recoverable — the next upload will trigger a full rebuild.
        print(f"[WARN] Index rebuild failed after document deletion: {exc}")

    return {
        "success": True,
        "data": {
            "removed_document": doc_name,
            "session": {
                "total_chunks":   updated_metadata["total_chunk_count"],
                "document_count": len(updated_metadata["documents"]),
            }
        }
    }