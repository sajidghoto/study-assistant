# backend/schemas/document.py
#
# Pydantic models for document-related data.
# DocumentInfo is used inside SessionData — imported by schemas/session.py.

from datetime import datetime
from pydantic import BaseModel


class DocumentInfo(BaseModel):
    """Metadata for a single uploaded document within a session."""
    document_id:   str
    document_name: str
    uploaded_at:   datetime
    chunk_count:   int
    page_count:    int


class UploadResponse(BaseModel):
    """Response returned after a successful PDF upload."""

    class _SessionSummary(BaseModel):
        total_chunks:   int
        document_count: int

    success:       bool = True
    data: dict
    # data shape:
    # {
    #   "document_id":   str,
    #   "document_name": str,
    #   "page_count":    int,
    #   "chunk_count":   int,
    #   "session":       { total_chunks, document_count }
    # }


class DocumentListResponse(BaseModel):
    """Response for GET /session/{id}/documents."""
    success: bool = True
    data:    dict
    # data shape:
    # {
    #   "documents":    list[DocumentInfo],
    #   "total_chunks": int
    # }


class DeleteDocumentResponse(BaseModel):
    """Response after a single document is removed from a session."""
    success: bool = True
    data:    dict
    # data shape:
    # {
    #   "removed_document": str,
    #   "session":          { total_chunks, document_count }
    # }