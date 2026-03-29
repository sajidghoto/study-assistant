# backend/tests/test_llm_bridge.py
#
# Tests for modules/llm_bridge.py
#
# We do NOT call the real Gemini API in tests.
# Reasons:
#   1. Tests would be slow (network latency)
#   2. Tests would consume real API quota
#   3. Tests would fail in CI without credentials
#   4. Responses are non-deterministic
#
# Instead we MOCK the Gemini SDK call and verify that our
# code calls it correctly and handles its responses/errors properly.
# This is standard practice for testing code that calls external APIs.

import pytest
from unittest.mock import MagicMock, patch
from modules.llm_bridge import _build_user_prompt, generate_answer, LLMError


# ── Sample data ───────────────────────────────────────────────────

SAMPLE_CHUNKS = [
    {
        "chunk_id":      "sess_x_doc_y_001",
        "document_name": "lecture_3.pdf",
        "text":          "Backpropagation computes the gradient of the loss with respect to each weight.",
        "score":         0.87,
        "chunk_index":   1,
    },
    {
        "chunk_id":      "sess_x_doc_y_002",
        "document_name": "lecture_3.pdf",
        "text":          "The chain rule of calculus is applied repeatedly during backpropagation.",
        "score":         0.81,
        "chunk_index":   2,
    },
]


class TestBuildUserPrompt:

    def test_includes_query_in_output(self):
        prompt = _build_user_prompt(
            query="What is backpropagation?",
            chunks=SAMPLE_CHUNKS,
            intent="answer",
        )
        assert "What is backpropagation?" in prompt

    def test_includes_chunk_text(self):
        prompt = _build_user_prompt(
            query="test query",
            chunks=SAMPLE_CHUNKS,
            intent="answer",
        )
        assert "gradient of the loss" in prompt
        assert "chain rule" in prompt

    def test_includes_source_labels(self):
        prompt = _build_user_prompt(
            query="test",
            chunks=SAMPLE_CHUNKS,
            intent="answer",
        )
        assert "[Source 1" in prompt
        assert "[Source 2" in prompt

    def test_includes_document_name_in_source_label(self):
        prompt = _build_user_prompt(
            query="test",
            chunks=SAMPLE_CHUNKS,
            intent="answer",
        )
        assert "lecture_3.pdf" in prompt

    def test_answer_intent_uses_answer_instruction(self):
        prompt = _build_user_prompt(
            query="What is X?",
            chunks=SAMPLE_CHUNKS,
            intent="answer",
        )
        assert "Answer the following question" in prompt

    def test_summarise_intent_uses_summary_instruction(self):
        prompt = _build_user_prompt(
            query="Summarize this",
            chunks=SAMPLE_CHUNKS,
            intent="summarise",
        )
        assert "summary" in prompt.lower()

    def test_empty_chunks_does_not_crash(self):
        # Edge case: called with empty list (defensive)
        prompt = _build_user_prompt(
            query="test",
            chunks=[],
            intent="answer",
        )
        assert "test" in prompt


class TestGenerateAnswer:

    def test_returns_string_on_success(self):
        """Mock a successful Gemini response and verify we get a string back."""
        mock_response      = MagicMock()
        mock_response.text = "Backpropagation is an algorithm for training neural networks."

        with patch("modules.llm_bridge._model") as mock_model:
            mock_model.generate_content.return_value = mock_response
            result = generate_answer(
                query="What is backpropagation?",
                chunks=SAMPLE_CHUNKS,
                intent="answer",
            )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_correct_content(self):
        """Verify the returned string matches the mocked response text."""
        expected_answer    = "The gradient is computed using the chain rule."
        mock_response      = MagicMock()
        mock_response.text = expected_answer

        with patch("modules.llm_bridge._model") as mock_model:
            mock_model.generate_content.return_value = mock_response
            result = generate_answer(
                query="Explain gradient computation",
                chunks=SAMPLE_CHUNKS,
                intent="answer",
            )

        assert result == expected_answer

    def test_strips_leading_trailing_whitespace(self):
        mock_response      = MagicMock()
        mock_response.text = "  \n answer with whitespace \n  "

        with patch("modules.llm_bridge._model") as mock_model:
            mock_model.generate_content.return_value = mock_response
            result = generate_answer("query", SAMPLE_CHUNKS, "answer")

        assert result == "answer with whitespace"

    def test_raises_llm_error_on_api_failure(self):
        """When Gemini raises an exception, we must raise LLMError — not crash."""
        with patch("modules.llm_bridge._model") as mock_model:
            mock_model.generate_content.side_effect = Exception("API quota exceeded")

            with pytest.raises(LLMError):
                generate_answer(
                    query="test",
                    chunks=SAMPLE_CHUNKS,
                    intent="answer",
                )

    def test_empty_chunks_returns_fallback_string(self):
        """Empty chunks should return a fallback without calling Gemini."""
        with patch("modules.llm_bridge._model") as mock_model:
            result = generate_answer(
                query="test",
                chunks=[],
                intent="answer",
            )
            # Gemini should NOT have been called
            mock_model.generate_content.assert_not_called()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_content_called_once(self):
        mock_response      = MagicMock()
        mock_response.text = "An answer."

        with patch("modules.llm_bridge._model") as mock_model:
            mock_model.generate_content.return_value = mock_response
            generate_answer("query", SAMPLE_CHUNKS, "answer")
            mock_model.generate_content.assert_called_once()