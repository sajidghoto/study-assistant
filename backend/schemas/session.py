# backend/schemas/session.py
#
# Pydantic models for session-related request and response bodies.
# These are the data contracts between frontend and backend for sessions.

from datetime import datetime
from pydantic import BaseModel
from schemas.document import DocumentInfo


class SessionData(BaseModel):
    """Full session state returned by GET /session/{id} and POST /session."""
    session_id:        str
    created_at:        datetime
    expires_at:        datetime
    documents:         list[DocumentInfo]
    total_chunks:      int


class SessionResponse(BaseModel):
    """Standard success envelope wrapping session data."""
    success: bool = True
    data:    SessionData


class DeleteSessionResponse(BaseModel):
    """Response after a session is manually deleted."""
    success: bool = True
    data:    dict  # {"message": "...", "session_id": "..."}