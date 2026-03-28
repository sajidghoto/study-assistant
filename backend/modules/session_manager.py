# backend/modules/session_manager.py
#
# Responsibilities:
#   1. Create new sessions (generate ID, write metadata.json)
#   2. Load existing sessions (read metadata.json, check TTL)
#   3. Add a document entry to a session after upload
#   4. Remove a document entry from a session
#   5. Delete an entire session from disk
#   6. List all documents in a session
#
# All persistence is filesystem-based.
# metadata.json is the single source of truth for session state.
# This module never touches TF-IDF or ChromaDB — that is the
# retriever's responsibility.

import json
import shutil
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config import settings


# ── Custom Exceptions ─────────────────────────────────────────────

class SessionNotFoundError(Exception):
    """Raised when the requested session_id does not exist on disk."""
    pass


class SessionExpiredError(Exception):
    """Raised when a session exists on disk but its TTL has elapsed."""
    pass


# ── Internal Helpers ──────────────────────────────────────────────

def _session_dir(session_id: str) -> Path:
    """Return the absolute path to a session's directory."""
    return settings.sessions_dir / session_id


def _metadata_path(session_id: str) -> Path:
    """Return the absolute path to a session's metadata.json."""
    return _session_dir(session_id) / "metadata.json"


def _now_utc() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def _serialize_metadata(meta: dict) -> str:
    """
    Serialize metadata dict to JSON string.
    datetime objects are converted to ISO 8601 strings.
    """
    def default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")

    return json.dumps(meta, indent=2, default=default)


def _deserialize_metadata(raw: str) -> dict:
    """
    Deserialize JSON string back to metadata dict.
    ISO 8601 datetime strings are converted back to datetime objects.
    """
    meta = json.loads(raw)

    # Convert datetime strings back to datetime objects
    for key in ("created_at", "expires_at"):
        if key in meta:
            meta[key] = datetime.fromisoformat(meta[key])

    for doc in meta.get("documents", []):
        if "uploaded_at" in doc:
            doc["uploaded_at"] = datetime.fromisoformat(doc["uploaded_at"])

    return meta


# ── Core Operations ───────────────────────────────────────────────

def create_session() -> dict:
    """
    Create a new session on disk and return its metadata dict.

    Generates a unique session_id, creates the session directory,
    and writes the initial metadata.json.

    Returns:
        The full metadata dict for the new session.
    """
    session_id = "sess_" + uuid.uuid4().hex[:8]
    now        = _now_utc()
    expires_at = now + timedelta(hours=settings.session_ttl_hours)

    metadata = {
        "session_id":        session_id,
        "created_at":        now,
        "expires_at":        expires_at,
        "documents":         [],
        "total_chunk_count": 0,
        "retrieval_mode":    settings.retrieval_mode,
    }

    # Create directory and write metadata
    session_path = _session_dir(session_id)
    session_path.mkdir(parents=True, exist_ok=True)
    _metadata_path(session_id).write_text(
        _serialize_metadata(metadata),
        encoding="utf-8"
    )

    return metadata


def load_session(session_id: str) -> dict:
    """
    Load and return session metadata, enforcing TTL.

    Raises:
        SessionNotFoundError: if the session directory or metadata.json
                              does not exist.
        SessionExpiredError:  if the session's expires_at is in the past.
                              The expired session is deleted from disk
                              before this exception is raised.
    """
    meta_path = _metadata_path(session_id)

    if not meta_path.exists():
        raise SessionNotFoundError(
            f"Session '{session_id}' not found."
        )

    metadata = _deserialize_metadata(meta_path.read_text(encoding="utf-8"))

    # ── TTL check (lazy expiry) ───────────────────────────────────
    # We check on every load rather than running a background job.
    # Expired sessions are deleted here to free disk space.
    if _now_utc() > metadata["expires_at"]:
        delete_session(session_id)          # clean up from disk
        raise SessionExpiredError(
            f"Session '{session_id}' expired at {metadata['expires_at'].isoformat()}."
        )

    return metadata


def save_session(session_id: str, metadata: dict) -> None:
    """
    Overwrite metadata.json with updated metadata.

    Called after adding or removing documents, so the metadata
    always reflects the current state of the session.
    """
    _metadata_path(session_id).write_text(
        _serialize_metadata(metadata),
        encoding="utf-8"
    )


def add_document_to_session(
    session_id: str,
    document_id: str,
    document_name: str,
    chunk_count: int,
    page_count: int,
) -> dict:
    """
    Append a new document entry to the session's metadata.

    Called by the upload router after chunking succeeds.

    Returns:
        The updated metadata dict.
    """
    metadata = load_session(session_id)

    new_doc = {
        "document_id":   document_id,
        "document_name": document_name,
        "uploaded_at":   _now_utc(),
        "chunk_count":   chunk_count,
        "page_count":    page_count,
    }

    metadata["documents"].append(new_doc)
    metadata["total_chunk_count"] += chunk_count

    save_session(session_id, metadata)
    return metadata


def remove_document_from_session(session_id: str, document_id: str) -> dict:
    """
    Remove a document entry from the session's metadata.

    Does NOT rebuild the TF-IDF / ChromaDB index — that is the
    retriever's responsibility. This function only updates metadata.

    Returns:
        The updated metadata dict.

    Raises:
        ValueError: if document_id is not found in this session.
    """
    metadata = load_session(session_id)

    # Find the document to remove
    target = next(
        (d for d in metadata["documents"] if d["document_id"] == document_id),
        None
    )

    if target is None:
        raise ValueError(
            f"Document '{document_id}' not found in session '{session_id}'."
        )

    metadata["documents"].remove(target)
    metadata["total_chunk_count"] -= target["chunk_count"]

    save_session(session_id, metadata)
    return metadata


def delete_session(session_id: str) -> None:
    """
    Permanently delete a session's directory and ALL its contents.

    This removes:
    - metadata.json
    - TF-IDF pickle files (if Path A)
    - ChromaDB is stored separately under chromadb_dir/session_id/
      and is also deleted here.

    Safe to call even if the directory does not exist
    (ignore_errors=True prevents FileNotFoundError).
    """
    # Delete TF-IDF session folder
    session_path = _session_dir(session_id)
    shutil.rmtree(session_path, ignore_errors=True)

    # Delete ChromaDB session folder (Path B)
    chroma_path = settings.chromadb_dir / session_id
    shutil.rmtree(chroma_path, ignore_errors=True)


def get_session_documents(session_id: str) -> tuple[list[dict], int]:
    """
    Return the document list and total chunk count for a session.

    Returns:
        (documents_list, total_chunk_count)
    """
    metadata = load_session(session_id)
    return metadata["documents"], metadata["total_chunk_count"]