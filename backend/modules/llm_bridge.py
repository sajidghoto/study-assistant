# backend/modules/llm_bridge.py
#
# Responsibilities:
#   1. Build intent-specific prompts for all 5 intent types
#   2. Call the Gemini 1.5 Flash API
#   3. For quiz intent: parse structured JSON response
#   4. Handle API errors gracefully

import json
import re
import google.generativeai as genai

from config import settings

# ── Gemini client ─────────────────────────────────────────────────
genai.configure(api_key=settings.gemini_api_key)

_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-lite",
    system_instruction=(
        "You are a study assistant. Your ONLY job is to help students "
        "learn from the context passages provided. "
        "Rules you must follow without exception:\n"
        "1. Base ALL responses strictly on the provided context.\n"
        "2. If the answer is not in the context, say exactly: "
        "'I could not find this in your uploaded notes.'\n"
        "3. Never use knowledge outside of the provided context.\n"
        "4. Do not speculate, infer, or extrapolate beyond what is written.\n"
        "5. For quiz questions, generate content strictly from the context."
    )
)


# ── Custom Exceptions ─────────────────────────────────────────────

class LLMError(Exception):
    """Raised when the Gemini API call fails for any reason."""
    pass


class QuizParseError(Exception):
    """Raised when the quiz JSON response cannot be parsed."""
    pass


# ── Prompt builders ───────────────────────────────────────────────

def _build_context_block(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block."""
    block = ""
    for i, chunk in enumerate(chunks, 1):
        block += (
            f"[Source {i} — {chunk['document_name']}]\n"
            f"{chunk['text']}\n\n"
        )
    return block.strip()


def _build_answer_prompt(query: str, chunks: list[dict]) -> str:
    context = _build_context_block(chunks)
    return (
        f"{context}\n\n"
        f"Answer the following question concisely and directly "
        f"(2-4 sentences maximum):\n{query}"
    )


def _build_explain_prompt(query: str, chunks: list[dict]) -> str:
    context = _build_context_block(chunks)
    return (
        f"{context}\n\n"
        f"Provide a detailed explanation for the following, including "
        f"examples and step-by-step reasoning where relevant. "
        f"Base your explanation entirely on the context above:\n{query}"
    )


def _build_summarise_prompt(query: str, chunks: list[dict]) -> str:
    context = _build_context_block(chunks)
    return (
        f"{context}\n\n"
        f"Provide a structured, comprehensive summary of the following "
        f"based on the context above. Cover all key points. "
        f"Use clear headings or bullet points if helpful:\n{query}"
    )


def _build_compare_prompt(query: str, chunks: list[dict]) -> str:
    context = _build_context_block(chunks)
    return (
        f"{context}\n\n"
        f"Based strictly on the context above, compare and contrast "
        f"the concepts in the following question. Present similarities "
        f"and differences clearly:\n{query}"
    )


def _build_quiz_prompt(query: str, chunks: list[dict]) -> str:
    context = _build_context_block(chunks)
    return (
        f"{context}\n\n"
        f"Based strictly on the context above, generate ONE multiple-choice "
        f"quiz question relevant to: {query}\n\n"
        f"You MUST respond with ONLY a valid JSON object. "
        f"No explanation, no markdown, no code fences. "
        f"The JSON must have exactly this structure:\n"
        f'{{"question": "...", '
        f'"options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, '
        f'"correct_answer": "A", '
        f'"explanation": "..."}}\n\n'
        f"Rules:\n"
        f"- The question must be based on the context above.\n"
        f"- All four options must be plausible but only one correct.\n"
        f"- correct_answer must be exactly one of: A, B, C, or D.\n"
        f"- explanation must explain why the correct answer is right "
        f"using the context.\n"
        f"- Do not include any text outside the JSON object."
    )


# ── Prompt router ─────────────────────────────────────────────────

PROMPT_BUILDERS = {
    "answer":    _build_answer_prompt,
    "explain":   _build_explain_prompt,
    "summarise": _build_summarise_prompt,
    "compare":   _build_compare_prompt,
    "quiz":      _build_quiz_prompt,
}


# ── Quiz response parser ──────────────────────────────────────────

def _parse_quiz_response(raw_text: str) -> dict:
    """
    Parse Gemini's quiz JSON response.

    Gemini sometimes wraps JSON in markdown code fences despite
    instructions not to. We strip those before parsing.

    Returns a validated quiz dict with keys:
        question, options (A/B/C/D), correct_answer, explanation
    """
    # Strip markdown code fences if present
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise QuizParseError(
            f"Could not parse quiz JSON from Gemini response: {exc}\n"
            f"Raw response was: {raw_text[:300]}"
        ) from exc

    # Validate required keys
    required = {"question", "options", "correct_answer", "explanation"}
    missing = required - set(data.keys())
    if missing:
        raise QuizParseError(f"Quiz JSON missing required keys: {missing}")

    required_options = {"A", "B", "C", "D"}
    missing_options = required_options - set(data.get("options", {}).keys())
    if missing_options:
        raise QuizParseError(f"Quiz options missing keys: {missing_options}")

    if data["correct_answer"] not in {"A", "B", "C", "D"}:
        raise QuizParseError(
            f"correct_answer must be A/B/C/D, got: {data['correct_answer']}"
        )

    return {
        "question":      data["question"],
        "options":       data["options"],
        "correct_answer": data["correct_answer"],
        "explanation":   data["explanation"],
    }


# ── Public Interface ──────────────────────────────────────────────

def generate_answer(
    query:  str,
    chunks: list[dict],
    intent: str,
) -> str:
    """
    Generate a text response for answer, explain, summarise, compare intents.

    Args:
        query:  The user's question
        chunks: Retrieved chunks
        intent: One of answer / explain / summarise / compare

    Returns:
        Generated text string.

    Raises:
        LLMError: on any Gemini API failure.
    """
    if not chunks:
        return "I could not find relevant content in your uploaded notes."

    builder = PROMPT_BUILDERS.get(intent, _build_answer_prompt)
    prompt  = builder(query, chunks)

    try:
        response = _model.generate_content(prompt)
        return response.text.strip()
    except Exception as exc:
        print(f"[LLM ERROR] Gemini API call failed: {exc}")
        raise LLMError(f"Gemini API call failed: {type(exc).__name__}") from exc


def generate_quiz(
    query:  str,
    chunks: list[dict],
) -> dict:
    """
    Generate a structured multiple-choice quiz question.

    Args:
        query:  The topic the student wants to be quizzed on
        chunks: Retrieved chunks relevant to the topic

    Returns:
        {
            "question":       str,
            "options":        {"A": str, "B": str, "C": str, "D": str},
            "correct_answer": str,  # "A" | "B" | "C" | "D"
            "explanation":    str,
        }

    Raises:
        LLMError:      on Gemini API failure.
        QuizParseError: if the response cannot be parsed as valid quiz JSON.
    """
    if not chunks:
        raise LLMError("No content available to generate a quiz question.")

    prompt = _build_quiz_prompt(query, chunks)

    try:
        response = _model.generate_content(prompt)
        raw_text = response.text
    except Exception as exc:
        print(f"[LLM ERROR] Quiz generation failed: {exc}")
        raise LLMError(f"Quiz generation failed: {type(exc).__name__}") from exc

    return _parse_quiz_response(raw_text)