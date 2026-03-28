# backend/modules/llm_bridge.py
#
# Responsibilities:
#   1. Build a grounded prompt from retrieved chunks + user query
#   2. Call the Gemini 1.5 Flash API
#   3. Return the generated answer string
#   4. Handle API errors gracefully
#
# This module never calls the retriever or classifier.
# It receives already-retrieved chunks and an already-classified intent.
# Single responsibility: LLM call only.

import google.generativeai as genai

from config import settings


# ── Gemini client initialisation ──────────────────────────────────
# Configured once at module import time.
# The API key is read from settings (which reads from .env).
genai.configure(api_key=settings.gemini_api_key)

_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-lite",
    # System instruction is passed at model creation — not per request.
    # This is Gemini SDK's equivalent of a system prompt.
    system_instruction=(
        "You are a study assistant. Your ONLY job is to answer "
        "questions using the context passages provided by the user. "
        "Rules you must follow without exception:\n"
        "1. If the answer exists in the context, answer clearly and directly.\n"
        "2. If the answer is not in the context, say exactly: "
        "'I could not find this in your uploaded notes.'\n"
        "3. Never use knowledge outside of the provided context.\n"
        "4. Do not speculate, infer, or extrapolate beyond what is written.\n"
        "5. When summarising, cover all key points present in the context."
    )
)


# ── Custom Exceptions ─────────────────────────────────────────────

class LLMError(Exception):
    """Raised when the Gemini API call fails for any reason."""
    pass


# ── Prompt Builder ────────────────────────────────────────────────

def _build_user_prompt(
    query:  str,
    chunks: list[dict],
    intent: str,
) -> str:
    """
    Construct the user-turn prompt sent to Gemini.

    Format:
        [Source 1 — document_name.pdf]
        <chunk text>

        [Source 2 — document_name.pdf]
        <chunk text>

        Answer the following question:
        <query>

    The [Source N] label makes it easy for Gemini to reference
    specific passages in its answer, supporting citation-aware responses.
    """
    context_block = ""
    for i, chunk in enumerate(chunks, 1):
        context_block += (
            f"[Source {i} — {chunk['document_name']}]\n"
            f"{chunk['text']}\n\n"
        )

    # Instruction wording differs by intent
    if intent == "summarise":
        instruction = (
            "Provide a comprehensive summary covering all key points "
            "from the following context"
        )
    else:
        instruction = "Answer the following question"

    return f"{context_block.strip()}\n\n{instruction}:\n{query}"


# ── Public Interface ──────────────────────────────────────────────

def generate_answer(
    query:  str,
    chunks: list[dict],
    intent: str,
) -> str:
    """
    Generate a grounded answer using the Gemini 1.5 Flash API.

    Args:
        query:  The user's original question
        chunks: List of retrieved chunk dicts (with "text" and "document_name")
        intent: Classified intent — "answer" or "summarise"
                (never called for "out-of-scope")

    Returns:
        The generated answer as a plain string.

    Raises:
        LLMError: wraps any Gemini SDK exception with a clean message.
                  The router catches this and returns HTTP 500.
    """
    if not chunks:
        # This should not happen in normal flow — the router guards it.
        # Defensive check to prevent sending an empty-context prompt.
        return "I could not find relevant content in your uploaded notes."

    prompt = _build_user_prompt(query, chunks, intent)

    try:
        print("Calling Gemini with model:", _model.model_name)
        response = _model.generate_content(prompt)

        # response.text raises if the response was blocked by safety filters
        answer = response.text

        return answer.strip()

    except Exception as exc:
        # We catch all exceptions here to:
        # 1. Log the real error server-side (visible in uvicorn output)
        # 2. Raise a clean LLMError that the router converts to HTTP 500
        # Never expose raw SDK exceptions to the client.
        print(f"[LLM ERROR] Gemini API call failed: {exc}")
        raise LLMError(
            f"Gemini API call failed: {type(exc).__name__}"
        ) from exc