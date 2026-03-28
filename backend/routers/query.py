# backend/routers/query.py
#
# The core endpoint — the full AI pipeline in one request:
#   POST /session/{session_id}/query
#
# Pipeline:
#   1. Validate session + request body
#   2. Classify intent (NB / LR classifier)
#   3. If out-of-scope → return immediately (no retrieval, no LLM)
#   4. Retrieve top-k chunks (TF-IDF or Semantic)
#   5. Call Gemini with grounded prompt
#   6. Return structured response

from fastapi import APIRouter, HTTPException

from config import settings
from schemas.query import QueryRequest
from modules.session_manager import (
    load_session,
    SessionNotFoundError,
    SessionExpiredError,
)
from modules.classifier import predict_intent, ClassifierNotFoundError
from modules.llm_bridge import generate_answer, LLMError

# ── Import correct retriever ──────────────────────────────────────
if settings.retrieval_mode == "semantic":
    from modules.retriever_semantic import query_index
else:
    from modules.retriever_tfidf import query_index


router = APIRouter(tags=["Query"])


# ── POST /session/{session_id}/query ──────────────────────────────

@router.post("/session/{session_id}/query", status_code=200)
def query_session(session_id: str, body: QueryRequest) -> dict:
    """
    Ask a question against the uploaded documents.

    This endpoint runs the full AI pipeline:
    classify → retrieve → generate.

    For 'out-of-scope' intent, retrieval and LLM are skipped entirely.
    This saves API quota and prevents hallucination on off-topic queries.
    """

    # ── Step 1: Validate session ──────────────────────────────────
    try:
        metadata = load_session(session_id)
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

    # ── Step 2: Verify at least one document exists ───────────────
    if len(metadata["documents"]) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code":    "NO_DOCUMENTS",
                    "message": "Please upload at least one PDF before asking questions.",
                    "detail":  f"session '{session_id}' has 0 documents",
                }
            }
        )

    # ── Step 3: Validate document_id if provided ──────────────────
    if body.document_id is not None:
        valid_doc_ids = [d["document_id"] for d in metadata["documents"]]
        if body.document_id not in valid_doc_ids:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code":    "INVALID_DOCUMENT_ID",
                        "message": "The specified document was not found in this session.",
                        "detail":  f"document_id '{body.document_id}'",
                    }
                }
            )

    # ── Step 4: Classify intent ───────────────────────────────────
    try:
        intent = predict_intent(body.query)
    except ClassifierNotFoundError:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code":    "CLASSIFIER_NOT_FOUND",
                    "message": "The intent classifier is not available. Please train it first.",
                    "detail":  "Run backend/training/train_classifier.py",
                }
            }
        )

    # ── Step 5: Short-circuit for out-of-scope ────────────────────
    # No retrieval. No LLM call. Instant response.
    # This is a key system design feature — not just an optimisation.
    if intent["label"] == "out-of-scope":
        return {
            "success": True,
            "data": {
                "intent": {
                    "label":      "out-of-scope",
                    "confidence": intent["confidence"],
                },
                "answer":               "This topic does not appear in your uploaded notes.",
                "sources":              [],
                "query_document_scope": "all" if body.document_id is None else body.document_id,
            }
        }

    # ── Step 6: Retrieve relevant chunks ─────────────────────────
    try:
        chunks = query_index(
            session_id=session_id,
            query_text=body.query,
            document_id=body.document_id,
            top_k=settings.top_k_chunks,
        )
    except FileNotFoundError:
        # Pickle files missing — index was never built or was corrupted
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code":    "INDEX_NOT_FOUND",
                    "message": "The search index is missing. Please re-upload your documents.",
                    "detail":  f"Pickle files not found for session '{session_id}'",
                }
            }
        )

    # Edge case: retrieval returned zero chunks (e.g., filtered by
    # a document that has no chunks matching the query at all)
    if not chunks:
        return {
            "success": True,
            "data": {
                "intent":  intent,
                "answer":  "I could not find relevant content in the selected document.",
                "sources": [],
                "query_document_scope": body.document_id or "all",
            }
        }

    # ── Step 7: Generate answer via Gemini ────────────────────────
    try:
        answer = generate_answer(
            query=body.query,
            chunks=chunks,
            intent=intent["label"],
        )
    except LLMError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code":    "LLM_UNAVAILABLE",
                    "message": "The AI answer service is temporarily unavailable. Please try again.",
                    "detail":  str(exc),
                }
            }
        )

    # ── Step 8: Format sources for response ──────────────────────
    sources = [
        {
            "chunk_id":      chunk["chunk_id"],
            "document_name": chunk["document_name"],
            "text":          chunk["text"],
            "score":         chunk["score"],
            "chunk_index":   chunk["chunk_index"],
        }
        for chunk in chunks
    ]

    # ── Step 9: Determine scope label ────────────────────────────
    if body.document_id is None:
        scope = "all"
    else:
        scope = next(
            d["document_name"]
            for d in metadata["documents"]
            if d["document_id"] == body.document_id
        )

    return {
        "success": True,
        "data": {
            "intent": {
                "label":      intent["label"],
                "confidence": intent["confidence"],
            },
            "answer":               answer,
            "sources":              sources,
            "query_document_scope": scope,
        }
    }