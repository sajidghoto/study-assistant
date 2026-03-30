# backend/config.py
#
# Single source of truth for all configuration values.
# Every other module imports `settings` from here.
# Values are read from the .env file automatically.
# If a required value is missing, the app crashes at startup
# with a clear error — not silently at runtime.

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


# Absolute path to the backend/ directory.
# __file__ is config.py itself, .parent gives backend/
BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    """
    All application settings. Each field maps to an .env variable.
    Pydantic-settings automatically reads the .env file and casts
    values to the correct Python type.
    """

    # ── LLM ──────────────────────────────────────────────────────
    gemini_api_key: str = Field(
        ...,                          # ... means required — no default
        description="Google Gemini API key"
    )

    # ── Retrieval ─────────────────────────────────────────────────
    retrieval_mode: str = Field(
        # default="tfidf",
        default="semantic",
        description="'tfidf' for Path A, 'semantic' for Path B"
    )

    # ── Session ───────────────────────────────────────────────────
    session_ttl_hours: int = Field(
        default=24,
        description="Hours before a session and its index expire"
    )

    # ── File Upload ───────────────────────────────────────────────
    max_file_size_mb: int = Field(
        default=20,
        description="Maximum PDF upload size in megabytes"
    )

    # ── Chunking ──────────────────────────────────────────────────
    chunk_size_words: int = Field(
        default=300,
        description="Number of words per chunk"
    )
    chunk_overlap_words: int = Field(
        default=50,
        description="Number of words overlapping between consecutive chunks"
    )

    # ── Retrieval ─────────────────────────────────────────────────
    top_k_chunks: int = Field(
        default=3,
        description="Number of chunks returned by the retriever"
    )

    retrieval_confidence_threshold: float = Field(
    default=0.05,
    description=(
        "Minimum cosine similarity score for a retrieved chunk to be "
        "considered relevant. If the top chunk scores below this threshold, "
        "the system returns 'not found in notes' instead of calling the LLM. "
        "Range: 0.0–1.0. Semantic retrieval: use 0.25. TF-IDF: use 0.10."
    )
)

 # ── Derived Paths (computed from BASE_DIR, not from .env) ─────
# These paths are not read from environment variables.
# They are derived relative to BASE_DIR for consistency.
#
# IMPORTANT:
# These must be defined as Pydantic fields (NOT @property),
# so they can be overridden in tests (e.g., via monkeypatch).
#
# Using @property makes them read-only and breaks test isolation.

     
    sessions_dir: Path = BASE_DIR / "data" / "sessions"
    chromadb_dir: Path = BASE_DIR / "data" / "chromadb"
    models_dir: Path = BASE_DIR / "models"

    @property
    def max_file_size_bytes(self) -> int:
        """Convenience: MB → bytes for direct comparison."""
        return self.max_file_size_mb * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# ── Module-level singleton ─────────────────────────────────────────
# Import this object everywhere else:
#   from config import settings
#
# Never instantiate Settings() again in any other file.
settings = Settings()


# ── Ensure runtime directories exist ──────────────────────────────
# Called once at import time. If the directories already exist,
# mkdir(exist_ok=True) does nothing. This prevents FileNotFoundError
# on the very first run when data/ is empty.
def _ensure_dirs() -> None:
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    settings.chromadb_dir.mkdir(parents=True, exist_ok=True)
    settings.models_dir.mkdir(parents=True, exist_ok=True)


_ensure_dirs()