# backend/routers/upload.py
#
# Handles PDF upload and processing:
#   POST /session/{session_id}/upload
#
# This is the most complex router because it orchestrates
# multiple modules in sequence:
#   1. Validate file (type, size)
#   2. Save PDF temporarily to disk
#   3. Extract text and chunk (pdf_parser)
#   4. Build / update the retrieval index (retriever)
#   5. Register document in session metadata (session_manager)
#   6. Clean up temp file
#   7. Return response

import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from config import settings
from modules.pdf_parser import process_pdf, PDFExtractionError
from modules.session_manager import (
    load_session,
    add_document_to_session,
    SessionNotFoundError,
    SessionExpiredError,
)

# ── Import the correct retriever based on config ──────────────────
# This is the ONLY place in the codebase where retrieval_mode is
# checked and the correct retriever is selected.
# All other modules use whichever retriever is injected here.
if settings.retrieval_mode == "semantic":
    from modules.retriever_semantic import build_index
else:
    from modules.retriever_tfidf import build_index


router = APIRouter(tags=["Upload"])


# ── POST /session/{session_id}/upload ─────────────────────────────

@router.post("/session/{session_id}/upload", status_code=200)
async def upload_pdf(
    session_id: str,
    file: UploadFile = File(...),
) -> dict:
    """
    Upload a PDF, process it, and add it to the session index.

    Accepts: multipart/form-data with a 'file' field.
    Returns: document metadata + updated session summary.

    Processing pipeline:
        validate → save temp → extract → chunk → index → register → cleanup
    """

    # ── Step 1: Validate session ──────────────────────────────────
    try:
        load_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code":    "SESSION_NOT_FOUND",
                    "message": "Session not found. Please create a session first.",
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

    # ── Step 2: Validate file type ────────────────────────────────
    # Check both content-type header AND file extension.
    # Why both? Content-type can be spoofed. Extension alone is unreliable.
    # Both must pass.
    is_pdf_content_type = (
        file.content_type in ("application/pdf", "application/x-pdf")
    )
    is_pdf_extension = (
        file.filename is not None and
        file.filename.lower().endswith(".pdf")
    )

    if not (is_pdf_content_type and is_pdf_extension):
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code":    "INVALID_FILE_TYPE",
                    "message": "Only PDF files are accepted.",
                    "detail":  f"received content-type '{file.content_type}', filename '{file.filename}'",
                }
            }
        )

    # ── Step 3: Read file bytes and validate size ─────────────────
    file_bytes = await file.read()
    file_size  = len(file_bytes)

    if file_size > settings.max_file_size_bytes:
        size_mb = round(file_size / (1024 * 1024), 1)
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code":    "FILE_TOO_LARGE",
                    "message": f"File exceeds the {settings.max_file_size_mb}MB limit.",
                    "detail":  f"received {size_mb}MB",
                }
            }
        )

    # ── Step 4: Save to a temporary file ─────────────────────────
    # pdfplumber requires a file path, not bytes in memory.
    # We write to a temp location, process, then delete.
    # temp_dir is the session folder — already exists.
    document_id = "doc_" + uuid.uuid4().hex[:8]
    temp_dir    = settings.sessions_dir / session_id
    temp_path   = temp_dir / f"_temp_{document_id}.pdf"

    try:
        temp_path.write_bytes(file_bytes)

        # ── Step 5: Extract text and chunk ───────────────────────
        try:
            chunks, page_count = process_pdf(
                pdf_path=temp_path,
                session_id=session_id,
                document_id=document_id,
                document_name=file.filename,
            )
        except PDFExtractionError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code":    "PDF_EXTRACTION_FAILED",
                        "message": "No text could be extracted from this PDF. It may be a scanned image.",
                        "detail":  str(exc),
                    }
                }
            )

        # ── Step 6: Build / update retrieval index ────────────────
        # build_index merges new chunks with existing ones internally.
        # If this is the first upload, it creates the index from scratch.
        try:
            build_index(session_id=session_id, chunks=chunks)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": {
                        "code":    "INDEX_BUILD_FAILED",
                        "message": "Failed to build the search index. Please try again.",
                        "detail":  str(exc),
                    }
                }
            )

        # ── Step 7: Register document in session metadata ─────────
        updated_metadata = add_document_to_session(
            session_id=session_id,
            document_id=document_id,
            document_name=file.filename,
            chunk_count=len(chunks),
            page_count=page_count,
        )

    finally:
        # ── Step 8: Always clean up temp file ────────────────────
        # The finally block runs whether or not an exception occurred.
        # We never leave temp PDFs on disk — they are no longer needed
        # once the text has been extracted and indexed.
        if temp_path.exists():
            temp_path.unlink()

    # ── Step 9: Build response ────────────────────────────────────
    return {
        "success": True,
        "data": {
            "document_id":   document_id,
            "document_name": file.filename,
            "page_count":    page_count,
            "chunk_count":   len(chunks),
            "session": {
                "total_chunks":   updated_metadata["total_chunk_count"],
                "document_count": len(updated_metadata["documents"]),
            }
        }
    }