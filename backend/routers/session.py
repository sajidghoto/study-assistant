# backend/routers/session.py
#
# Handles session lifecycle:
#   POST   /session                → create new session
#   GET    /session/{session_id}   → get session state
#   DELETE /session/{session_id}   → manually delete session

from fastapi import APIRouter, HTTPException

from modules.session_manager import (
    create_session,
    load_session,
    delete_session,
    SessionNotFoundError,
    SessionExpiredError,
)

router = APIRouter(tags=["Session"])


# ── POST /session ─────────────────────────────────────────────────

@router.post("/session", status_code=200)
def create_new_session() -> dict:
    """
    Create a new session.

    Called by the frontend on first load (or when the student
    clicks 'Start New Session'). Returns a session_id that must
    be included in every subsequent request.

    No request body required.
    """
    metadata = create_session()

    return {
        "success": True,
        "data": {
            "session_id":   metadata["session_id"],
            "created_at":   metadata["created_at"].isoformat(),
            "expires_at":   metadata["expires_at"].isoformat(),
            "documents":    [],
            "total_chunks": 0,
        }
    }


# ── GET /session/{session_id} ─────────────────────────────────────

@router.get("/session/{session_id}", status_code=200)
def get_session(session_id: str) -> dict:
    """
    Retrieve current session state.

    Used by the frontend on page reload to restore the document
    list without re-uploading PDFs.

    Returns full session metadata including all uploaded documents.
    """
    try:
        metadata = load_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code":    "SESSION_NOT_FOUND",
                    "message": "Session not found or has expired.",
                    "detail":  f"session_id '{session_id}' does not exist on disk",
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
                    "detail":  f"session_id '{session_id}' TTL has elapsed",
                }
            }
        )

    # Serialize documents (convert datetimes to ISO strings)
    documents = [
        {
            "document_id":   doc["document_id"],
            "document_name": doc["document_name"],
            "uploaded_at":   doc["uploaded_at"].isoformat(),
            "chunk_count":   doc["chunk_count"],
            "page_count":    doc["page_count"],
        }
        for doc in metadata["documents"]
    ]

    return {
        "success": True,
        "data": {
            "session_id":   metadata["session_id"],
            "created_at":   metadata["created_at"].isoformat(),
            "expires_at":   metadata["expires_at"].isoformat(),
            "documents":    documents,
            "total_chunks": metadata["total_chunk_count"],
        }
    }


# ── DELETE /session/{session_id} ──────────────────────────────────

@router.delete("/session/{session_id}", status_code=200)
def delete_existing_session(session_id: str) -> dict:
    """
    Permanently delete a session and all its data.

    Called when the student clicks 'Start Over'.
    Removes: metadata.json, all pickle files, ChromaDB vectors.
    This action is irreversible.
    """
    # Verify session exists before deleting
    # (gives a clear error rather than silent success on wrong ID)
    try:
        load_session(session_id)
    except (SessionNotFoundError, SessionExpiredError):
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code":    "SESSION_NOT_FOUND",
                    "message": "Session not found or already deleted.",
                    "detail":  f"session_id '{session_id}'",
                }
            }
        )

    delete_session(session_id)

    return {
        "success": True,
        "data": {
            "message":    "Session deleted successfully.",
            "session_id": session_id,
        }
    }