# backend/routers/documents.py
#
# Handles document listing and deletion:
#   GET    /session/{session_id}/documents
#   DELETE /session/{session_id}/document/{document_id}

import logging

from fastapi import APIRouter, HTTPException

from config import settings
from modules.session_manager import (
    load_session,
    remove_document_from_session,
    get_session_documents,
    SessionNotFoundError,
    SessionExpiredError,
)

logger = logging.getLogger(__name__)

# ── Import correct retriever for rebuild after deletion ───────────
if settings.retrieval_mode == "semantic":
    from modules.retriever_semantic import retain_documents
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
        retained documents are passed to retain_documents().
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

    # ── Rebuild retrieval index ───────────────────────────────────
    # Update the index before metadata so an index failure is visible and
    # does not report success while leaving the document registered.
    try:
        if settings.retrieval_mode == "tfidf":
            chunks_path = _chunks_path(session_id)
            if not chunks_path.exists():
                raise FileNotFoundError(
                    f"TF-IDF chunks missing for session '{session_id}'."
                )
            all_chunks = _load_pickle(chunks_path)
            remaining = [
                chunk for chunk in all_chunks
                if chunk["document_id"] != document_id
            ]
            rebuild_index(session_id, remaining)
        else:
            remaining_ids = [
                doc["document_id"]
                for doc in metadata["documents"]
                if doc["document_id"] != document_id
            ]
            retain_documents(session_id, remaining_ids)

    except Exception as exc:
        logger.exception(
            "Failed to update retrieval index after deleting document %s "
            "from session %s",
            document_id,
            session_id,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code":    "INDEX_UPDATE_FAILED",
                    "message": "Failed to update the search index. Please try again.",
                    "detail":  str(exc),
                }
            }
        ) from exc

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
        ) from exc

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