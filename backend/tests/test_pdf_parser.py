# backend/tests/test_pdf_parser.py
#
# Tests for modules/pdf_parser.py
# We test chunking without real PDFs — extract_text is tested
# separately using a real PDF file if available.

import pytest
from modules.pdf_parser import clean_text, chunk_text, PDFExtractionError


# ── clean_text tests ──────────────────────────────────────────────

class TestCleanText:

    def test_removes_hyphenated_line_breaks(self):
        raw = "back-\npropagation is important"
        result = clean_text(raw)
        assert "backpropagation is important" in result
        assert "-\n" not in result

    def test_collapses_multiple_spaces(self):
        raw = "neural    networks   are   great"
        result = clean_text(raw)
        assert "  " not in result
        assert "neural networks are great" in result

    def test_collapses_excess_newlines(self):
        raw = "line one\n\n\n\n\nline two"
        result = clean_text(raw)
        # Should have at most 2 consecutive newlines
        assert "\n\n\n" not in result

    def test_strips_leading_trailing_whitespace(self):
        raw = "   \n  hello world  \n   "
        result = clean_text(raw)
        assert result == "hello world"

    def test_preserves_single_newlines(self):
        # Single newlines are paragraph breaks — meaningful
        raw = "paragraph one\nparagraph two"
        result = clean_text(raw)
        assert "\n" in result

    def test_empty_string_returns_empty(self):
        result = clean_text("")
        assert result == ""

    def test_preserves_punctuation(self):
        raw = "What is backpropagation? It's an algorithm."
        result = clean_text(raw)
        assert "?" in result
        assert "." in result


# ── chunk_text tests ──────────────────────────────────────────────

class TestChunkText:

    def test_returns_list_of_dicts(self, sample_chunks):
        assert isinstance(sample_chunks, list)
        assert len(sample_chunks) > 0
        assert isinstance(sample_chunks[0], dict)

    def test_each_chunk_has_required_keys(self, sample_chunks):
        required_keys = {
            "chunk_id", "session_id", "document_id",
            "document_name", "chunk_index", "text", "word_count"
        }
        for chunk in sample_chunks:
            assert required_keys.issubset(chunk.keys()), (
                f"Chunk missing keys: {required_keys - chunk.keys()}"
            )

    def test_chunk_ids_are_unique(self, sample_chunks):
        ids = [c["chunk_id"] for c in sample_chunks]
        assert len(ids) == len(set(ids)), "Duplicate chunk IDs detected"

    def test_chunk_index_is_sequential(self, sample_chunks):
        indices = [c["chunk_index"] for c in sample_chunks]
        assert indices == list(range(len(sample_chunks)))

    def test_chunk_word_count_within_bounds(self):
        from modules.pdf_parser import chunk_text
        # Use SAMPLE_TEXT from conftest via direct import
        from tests.conftest import SAMPLE_TEXT
        chunks = chunk_text(
            text=SAMPLE_TEXT,
            session_id="sess_x",
            document_id="doc_x",
            document_name="x.pdf",
            chunk_size=50,
            overlap=10,
        )
        for chunk in chunks:
            # Allow slight variance due to boundary handling
            assert chunk["word_count"] <= 55, (
                f"Chunk {chunk['chunk_index']} too large: {chunk['word_count']} words"
            )

    def test_metadata_correctly_attached(self):
        from modules.pdf_parser import chunk_text
        chunks = chunk_text(
            text="word " * 100,
            session_id="sess_abc",
            document_id="doc_xyz",
            document_name="my_notes.pdf",
            chunk_size=30,
            overlap=5,
        )
        for chunk in chunks:
            assert chunk["session_id"]    == "sess_abc"
            assert chunk["document_id"]   == "doc_xyz"
            assert chunk["document_name"] == "my_notes.pdf"

    def test_short_text_produces_single_chunk(self):
        from modules.pdf_parser import chunk_text
        short_text = "This is a short text with twenty words total here now yes"
        chunks = chunk_text(
            text=short_text,
            session_id="sess_x",
            document_id="doc_x",
            document_name="x.pdf",
            chunk_size=300,
            overlap=50,
        )
        assert len(chunks) == 1

    def test_very_short_text_below_minimum_returns_empty(self):
        from modules.pdf_parser import chunk_text
        # 5 words — below the 20-word minimum chunk size guard
        tiny = "hello world foo bar baz"
        chunks = chunk_text(
            text=tiny,
            session_id="sess_x",
            document_id="doc_x",
            document_name="x.pdf",
            chunk_size=300,
            overlap=50,
        )
        assert len(chunks) == 0

    def test_overlap_creates_more_chunks_than_no_overlap(self):
        from modules.pdf_parser import chunk_text
        text = "word " * 500

        with_overlap = chunk_text(
            text=text, session_id="s", document_id="d",
            document_name="d.pdf", chunk_size=100, overlap=50
        )
        without_overlap = chunk_text(
            text=text, session_id="s", document_id="d",
            document_name="d.pdf", chunk_size=100, overlap=0
        )
        assert len(with_overlap) > len(without_overlap)

    def test_chunk_id_format(self, sample_chunks):
        # chunk_id must be: {session_id}_{document_id}_{index:04d}
        for chunk in sample_chunks:
            assert chunk["chunk_id"].startswith(
                f"{chunk['session_id']}_{chunk['document_id']}_"
            )