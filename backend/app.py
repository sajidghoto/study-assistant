# backend/app.py
#
# FastAPI application entry point.
# Creates the app, adds middleware, registers all routers.
# No business logic lives here — only wiring.

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import session, upload, documents, query

# ── Logger ────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Lifespan: Eager model loading ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the semantic model at startup."""
    # Startup
    logger.info("Loading semantic model... this may take a moment on first run.")
    if settings.retrieval_mode == "semantic":
        from modules.retriever_semantic import load_model
        load_model()
    logger.info("Semantic model ready.")
    yield
    # Shutdown (cleanup if needed in the future)


# ── App instance ──────────────────────────────────────────────────
app = FastAPI(
    title="Intent-Aware Study Assistant API",
    version="1.0.0",
    description=(
        "Upload your lecture notes (PDF) and ask questions. "
        "Every answer is grounded strictly in your uploaded material."
    ),
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)

# ── Routers ───────────────────────────────────────────────────────
# All routes are prefixed with /api/v1 here.
# Individual router files do NOT include this prefix.
app.include_router(session.router,   prefix="/api/v1")
app.include_router(upload.router,    prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(query.router,     prefix="/api/v1")


# ── Health check ──────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["System"])
def health_check() -> dict:
    model_loaded = False
    if settings.retrieval_mode == "semantic":
        from modules.retriever_semantic import _embedding_model
        model_loaded = _embedding_model is not None
    else:
        # TF-IDF doesn't require eager loading
        model_loaded = True
    
    return {
        "success": True,
        "data": {
            "status":         "ok",
            "version":        "1.0.0",
            "retrieval_mode": settings.retrieval_mode,
            "model_loaded":   model_loaded,
        }
    }