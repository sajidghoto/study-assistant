# backend/modules/pdf_parser.py
#
# Responsibilities:
#   1. Extract raw text from a PDF file using pdfplumber
#   2. Clean the extracted text
#   3. Split text into overlapping chunks
#
# This module is pure data transformation — no I/O side effects
# beyond reading the PDF file. It does not write any files.
# It does not know about sessions, databases, or the web framework.

import re
import uuid
from pathlib import Path

import pdfplumber

from config import settings


# ── Custom Exceptions ─────────────────────────────────────────────
class PDFExtractionError(Exception):
    """Raised when no text can be extracted from the PDF."""
    pass


# ── Text Extraction ───────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: Path) -> tuple[str, int]:
    """
    Open a PDF and extract all text from every page.

    Returns:
        (full_text, page_count)

    Raises:
        PDFExtractionError: if the PDF yields zero extractable characters.
                            This happens with scanned/image-only PDFs.
    """
    full_text = ""
    page_count = 0

    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)

        for page in pdf.pages:
            # extract_text() returns None if the page has no text layer
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"

    if len(full_text.strip()) == 0:
        raise PDFExtractionError(
            f"No text could be extracted from {pdf_path.name}. "
            f"The PDF may contain only scanned images with no text layer. "
            f"({page_count} pages checked)"
        )

    return full_text, page_count


# ── Text Cleaning ─────────────────────────────────────────────────

def clean_text(raw_text: str) -> str:
    """
    Normalise extracted PDF text before chunking.

    What we remove / fix:
    - Multiple consecutive blank lines → single newline
    - Multiple consecutive spaces     → single space
    - Hyphenated line breaks          → rejoined word
      (PDFs often break "back-\npropagation" across lines)
    - Leading/trailing whitespace

    What we deliberately keep:
    - Single newlines (paragraph breaks — meaningful for context)
    - Punctuation (needed by TF-IDF and sentence transformers)
    """
    # Rejoin hyphenated words split across lines
    text = re.sub(r"-\n", "", raw_text)

    # Collapse multiple spaces into one
    text = re.sub(r" {2,}", " ", text)

    # Collapse more than 2 consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading and trailing whitespace
    text = text.strip()

    return text


# ── Chunking ──────────────────────────────────────────────────────

def chunk_text(
    text: str,
    session_id: str,
    document_id: str,
    document_name: str,
    chunk_size: int   = None,
    overlap: int      = None,
) -> list[dict]:
    """
    Split cleaned text into overlapping word-based chunks.

    Args:
        text:          Cleaned full document text
        session_id:    Parent session identifier
        document_id:   Parent document identifier
        document_name: Human-readable PDF filename
        chunk_size:    Words per chunk (default: from settings)
        overlap:       Words of overlap between chunks (default: from settings)

    Returns:
        List of chunk dicts. Each dict has the shape defined in Step 2
        (Section 2.3) — the canonical chunk format used by both
        retriever_tfidf.py and retriever_semantic.py.

    Why word-based and not character-based?
        Character count varies by language and encoding. Word count is
        a stable proxy for semantic density — a 300-word chunk always
        contains roughly one coherent topic regardless of avg word length.
    """
    # Fall back to settings if not explicitly passed
    # (allows tests to override without touching global config)
    chunk_size = settings.chunk_size_words if chunk_size is None else chunk_size
    overlap    = settings.chunk_overlap_words if overlap is None else overlap

    # Tokenise into words. split() handles multiple spaces and newlines.
    words = text.split()

    # Minimum meaningful threshold (based on tests)
    MIN_WORDS = 20

    if len(words) < MIN_WORDS:
        return []

    if len(words) == 0:
        return []

    step   = chunk_size - overlap   # how many words we advance per chunk
    chunks = []
    index  = 0                      # chunk sequence number within document

    for start in range(0, len(words), step):
        end        = start + chunk_size
        chunk_words = words[start:end]

        # Skip chunks that are too short to be meaningful.
        # This avoids noise at the end of a document (e.g., a 5-word tail).
        if not chunk_words:
            break

        # ✅ Allow short text to produce ONE chunk
        if len(chunk_words) < MIN_WORDS and index > 0:
            break

        chunk_text_str = " ".join(chunk_words)

        chunk = {
            # Globally unique ID — collision-free without a database
            "chunk_id":      f"{session_id}_{document_id}_{index:04d}",
            "session_id":    session_id,
            "document_id":   document_id,
            "document_name": document_name,
            "chunk_index":   index,
            "text":          chunk_text_str,
            "word_count":    len(chunk_words),
        }

        chunks.append(chunk)
        index += 1

        # If the end of this chunk reaches the end of the document, stop.
        if end >= len(words):
            break

    return chunks


# ── Public Interface ──────────────────────────────────────────────

def process_pdf(
    pdf_path: Path,
    session_id: str,
    document_id: str,
    document_name: str,
) -> tuple[list[dict], int]:
    """
    Full pipeline: PDF file → list of chunk dicts.

    This is the single function called by the upload router.
    It orchestrates extract → clean → chunk in one call.

    Returns:
        (chunks, page_count)

    Raises:
        PDFExtractionError: propagated from extract_text_from_pdf()
    """
    raw_text, page_count = extract_text_from_pdf(pdf_path)
    clean                = clean_text(raw_text)
    chunks               = chunk_text(
                               text=clean,
                               session_id=session_id,
                               document_id=document_id,
                               document_name=document_name,
                           )

    return chunks, page_count