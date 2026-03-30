# backend/modules/retriever_semantic.py
#
# Path B: Semantic retrieval using sentence-transformers + ChromaDB.
#
# This module has the IDENTICAL public interface as retriever_tfidf.py:
#   - build_index(session_id, chunks)
#   - rebuild_index(session_id, remaining_chunks)
#   - query_index(session_id, query_text, document_id, top_k)
#
# The classifier.py and routers never import this directly.
# The retriever is selected in modules/retriever.py (a thin router)
# based on settings.retrieval_mode. This keeps all swap logic in
# one place.
#
# IMPORTANT: On first use, sentence-transformers downloads the model
# all-MiniLM-L6-v2 (~90MB) into a local cache (~/.cache/huggingface).
# This happens once. Subsequent calls use the cached model.

import logging

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from config import settings


# ── Model singleton ───────────────────────────────────────────────
# Loading the embedding model is expensive (~2 seconds).
# We load it once at module import time and reuse it.
# For a single-user local app this is correct.
# In a multi-worker production server you would use a model server.

_embedding_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Return the embedding model, loading it on first call."""
    global _embedding_model
    if _embedding_model is None:
        # all-MiniLM-L6-v2:
        #   - 384-dimensional vectors
        #   - Strong performance on sentence similarity tasks
        #   - ~90MB download, runs on CPU
        #   - MIT licensed
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


# ── ChromaDB client ───────────────────────────────────────────────

def _get_chroma_client(session_id: str) -> chromadb.PersistentClient:
    """
    Return a ChromaDB persistent client for the given session.

    Each session gets its own subdirectory under chromadb_dir.
    ChromaDB manages its own internal file format there.
    """
    chroma_path = settings.chromadb_dir / session_id
    chroma_path.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(
        path=str(chroma_path),
        settings=ChromaSettings(anonymized_telemetry=False)
    )


def _get_collection(session_id: str) -> chromadb.Collection:
    """
    Return the ChromaDB collection for this session.
    Creates it if it does not exist.

    One collection per session contains all chunks from all documents.
    Per-document filtering is done via metadata at query time.
    """
    client = _get_chroma_client(session_id)

    # get_or_create_collection is idempotent — safe to call repeatedly
    return client.get_or_create_collection(
        name="chunks",
        # cosine distance = 1 - cosine_similarity
        # ChromaDB returns distance, we convert to similarity in query_index
        metadata={"hnsw:space": "cosine"}
    )


# ── Index Operations ──────────────────────────────────────────────

def build_index(session_id: str, chunks: list[dict]) -> None:
    """
    Embed new chunks and add them to the ChromaDB collection.

    Unlike TF-IDF, ChromaDB supports incremental addition.
    We do NOT need to re-embed existing chunks when a new PDF
    is uploaded — we just add the new ones.

    Args:
        session_id: The session this index belongs to
        chunks:     New chunks to add (from the just-uploaded PDF)
    """
    if not chunks:
        return

    model      = _get_model()
    collection = _get_collection(session_id)

    texts      = [c["text"]     for c in chunks]
    ids        = [c["chunk_id"] for c in chunks]

    # Encode all chunk texts into dense vectors
    # show_progress_bar=False keeps server logs clean
    embeddings = model.encode(texts, show_progress_bar=False).tolist()

    # Metadata stored alongside each vector — used for filtering
    metadatas = [
        {
            "session_id":    c["session_id"],
            "document_id":   c["document_id"],
            "document_name": c["document_name"],
            "chunk_index":   c["chunk_index"],
            "word_count":    c["word_count"],
        }
        for c in chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )


def rebuild_index(session_id: str, remaining_chunks: list[dict]) -> None:
    """
    Delete all vectors for removed document and keep the rest.

    ChromaDB supports deletion by metadata filter, so we only
    delete the removed document's vectors — not the whole collection.

    This is called with the chunks that SHOULD REMAIN.
    We infer which document was removed by comparing chunk IDs
    in the collection against remaining_chunk IDs.
    """
    collection = _get_collection(session_id)

    # Get all IDs currently in the collection
    all_ids_in_db = set(collection.get()["ids"])

    # IDs that should remain
    remaining_ids = {c["chunk_id"] for c in remaining_chunks}

    # IDs to delete = in DB but not in remaining
    ids_to_delete = list(all_ids_in_db - remaining_ids)

    if ids_to_delete:
        collection.delete(ids=ids_to_delete)


def query_index(
    session_id:  str,
    query_text:  str,
    document_id: str | None = None,
    top_k:       int        = None,
) -> list[dict]:
    """
    Retrieve top-k semantically similar chunks.

    Args:
        session_id:  The session to query
        query_text:  Raw user question string
        document_id: If provided, restrict results to this document
        top_k:       Number of chunks to return

    Returns:
        List of chunk dicts with "score" key (float, 0.0–1.0),
        sorted by descending similarity score.
    """
    top_k      = top_k or settings.top_k_chunks
    model      = _get_model()
    collection = _get_collection(session_id)

    # Check collection is not empty
    if collection.count() == 0:
        return []

    # Embed the query with the same model used during build_index
    query_embedding = model.encode([query_text], show_progress_bar=False).tolist()


    # ─── ADD THIS: Log query for analysis ───
    
    logger = logging.getLogger(__name__)
    logger.info(f"[RETRIEVAL] Query: '{query_text}'")
    logger.info(f"[RETRIEVAL] Session: {session_id}, Top-K: {top_k}")

    # Build optional metadata filter
    where_filter = {"session_id": session_id}
    if document_id is not None:
        # ChromaDB requires $and for multiple conditions
        where_filter = {
            "$and": [
                {"session_id":  {"$eq": session_id}},
                {"document_id": {"$eq": document_id}},
            ]
        }

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count()),
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    # ── Format results ────────────────────────────────────────────
    chunks   = []
    ids      = results["ids"][0]
    texts    = results["documents"][0]
    metas    = results["metadatas"][0]
    distances = results["distances"][0]

    for i in range(len(ids)):
        # ChromaDB returns cosine DISTANCE (0 = identical, 2 = opposite)
        # Convert to similarity score (1 = identical, 0 = unrelated)
        similarity = float(round(1 - distances[i], 4))

        chunk = {
            "chunk_id":      ids[i],
            "session_id":    metas[i]["session_id"],
            "document_id":   metas[i]["document_id"],
            "document_name": metas[i]["document_name"],
            "chunk_index":   metas[i]["chunk_index"],
            "text":          texts[i],
            "word_count":    metas[i]["word_count"],
            "score":         similarity,
        }
        chunks.append(chunk)

    return chunks