# backend/routers/query.py
#
# Core query pipeline — now with 5 intent types and
# retrieval-based confidence gating instead of classifier-based
# out-of-scope detection.

from fastapi import APIRouter, HTTPException

from config import settings
from schemas.query import QueryRequest
from modules.session_manager import (
    load_session,
    SessionNotFoundError,
    SessionExpiredError,
)
from modules.classifier import predict_intent, ClassifierNotFoundError
from modules.llm_bridge import (
    generate_answer,
    generate_quiz,
    LLMError,
    QuizParseError,
)

if settings.retrieval_mode == "semantic":
    from modules.retriever_semantic import query_index
else:
    from modules.retriever_tfidf import query_index


router = APIRouter(tags=["Query"])


def _guard_session(session_id: str) -> dict:
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


@router.post("/session/{session_id}/query", status_code=200)
def query_session(session_id: str, body: QueryRequest) -> dict:
    """
    Full AI pipeline:
      classify intent → retrieve → confidence gate → generate response

    Intent types:
      answer    → concise direct answer (2-4 sentences)
      explain   → detailed explanation with examples
      summarise → structured overview of relevant content
      compare   → side-by-side comparison of concepts
      quiz      → structured MCQ with 4 options + explanation

    Out-of-scope detection:
      Handled by the retrieval confidence gate, NOT the classifier.
      If top retrieved chunk scores below RETRIEVAL_CONFIDENCE_THRESHOLD,
      the system returns not_found=True without calling the LLM.
      This is document-aware, unlike a classifier-based approach.
    """

    # ── Step 1: Validate session ──────────────────────────────────
    metadata = _guard_session(session_id)

    # ── Step 2: Require at least one document ─────────────────────
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
        valid_ids = [d["document_id"] for d in metadata["documents"]]
        if body.document_id not in valid_ids:
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
                    "message": "Intent classifier not found. Run train_classifier.py first.",
                    "detail":  "backend/training/train_classifier.py",
                }
            }
        )

    # ── Step 5: Retrieve chunks (ALWAYS — no pre-filter) ──────────
    try:
        chunks = query_index(
            session_id=session_id,
            query_text=body.query,
            document_id=body.document_id,
            top_k=settings.top_k_chunks,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code":    "INDEX_NOT_FOUND",
                    "message": "Search index missing. Please re-upload your documents.",
                    "detail":  f"session '{session_id}'",
                }
            }
        )

    # ── Step 6: Confidence gate ───────────────────────────────────
    # This replaces the old out-of-scope classifier check.
    # The retriever has now seen the actual document — it knows
    # whether relevant content exists. The classifier does not.
    scope = "all" if body.document_id is None else next(
        (d["document_name"] for d in metadata["documents"]
         if d["document_id"] == body.document_id),
        body.document_id
    )

    top_score = chunks[0]["score"] if chunks else 0.0

    if top_score < settings.retrieval_confidence_threshold:
        return {
            "success": True,
            "data": {
                "intent":               intent,
                "answer":               None,
                "quiz":                 None,
                "sources":              [],
                "query_document_scope": scope,
                "not_found":            True,
            }
        }

    # ── Step 7: Format sources ────────────────────────────────────
    sources = [
        {
            "chunk_id":      c["chunk_id"],
            "document_name": c["document_name"],
            "text":          c["text"],
            "score":         c["score"],
            "chunk_index":   c["chunk_index"],
        }
        for c in chunks
    ]

    # ── Step 8: Generate response based on intent ─────────────────
    if intent["label"] == "quiz":
        try:
            quiz_data = generate_quiz(
                query=body.query,
                chunks=chunks,
            )
        except (LLMError, QuizParseError) as exc:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": {
                        "code":    "QUIZ_GENERATION_FAILED",
                        "message": "Failed to generate quiz question. Please try again.",
                        "detail":  str(exc),
                    }
                }
            )

        return {
            "success": True,
            "data": {
                "intent":               intent,
                "answer":               None,
                "quiz":                 quiz_data,
                "sources":              sources,
                "query_document_scope": scope,
                "not_found":            False,
            }
        }

    # All non-quiz intents go through generate_answer
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
                    "message": "AI service temporarily unavailable. Please try again.",
                    "detail":  str(exc),
                }
            }
        )

    return {
        "success": True,
        "data": {
            "intent":               intent,
            "answer":               answer,
            "quiz":                 None,
            "sources":              sources,
            "query_document_scope": scope,
            "not_found":            False,
        }
    }