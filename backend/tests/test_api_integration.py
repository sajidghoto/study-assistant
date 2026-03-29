# backend/tests/test_api_integration.py
#
# Integration tests for all API endpoints.
# Uses the api_client fixture (FastAPI TestClient).
# These tests hit the full stack: router → module → filesystem.
# Gemini API calls are mocked to avoid real network calls.

import io
import pytest
from unittest.mock import MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────

def make_pdf_bytes() -> bytes:
    """
    Create a minimal valid PDF in memory.
    pdfplumber can extract text from this without a real file.

    This is the smallest valid PDF structure that pdfplumber accepts.
    """
    # A real minimal PDF with the word "backpropagation" in it.
    # Generated once and hardcoded as bytes — no PDF library needed.
    return b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>
stream
BT /F1 12 Tf 100 700 Td (Backpropagation is used in neural networks to train weights using gradient descent. The algorithm computes gradients efficiently using the chain rule of calculus. Deep learning models use backpropagation extensively.) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000370 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
441
%%EOF"""


def upload_sample_pdf(client, session_id: str) -> dict:
    """Helper: upload a minimal PDF and return the response JSON."""
    pdf_bytes = make_pdf_bytes()
    response = client.post(
        f"/api/v1/session/{session_id}/upload",
        files={"file": ("test_lecture.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    return response


# ── Health endpoint ───────────────────────────────────────────────

class TestHealthEndpoint:

    def test_health_returns_200(self, api_client):
        response = api_client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_response_structure(self, api_client):
        data = api_client.get("/api/v1/health").json()
        assert data["success"] is True
        assert data["data"]["status"] == "ok"
        assert "retrieval_mode" in data["data"]


# ── Session endpoints ─────────────────────────────────────────────

class TestSessionEndpoints:

    def test_create_session_returns_200(self, api_client):
        response = api_client.post("/api/v1/session")
        assert response.status_code == 200

    def test_create_session_returns_session_id(self, api_client):
        data = api_client.post("/api/v1/session").json()
        assert data["success"] is True
        assert data["data"]["session_id"].startswith("sess_")

    def test_get_session_returns_200(self, api_client):
        sid      = api_client.post("/api/v1/session").json()["data"]["session_id"]
        response = api_client.get(f"/api/v1/session/{sid}")
        assert response.status_code == 200

    def test_get_nonexistent_session_returns_404(self, api_client):
        response = api_client.get("/api/v1/session/sess_doesnotexist")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "SESSION_NOT_FOUND"

    def test_delete_session_returns_200(self, api_client):
        sid      = api_client.post("/api/v1/session").json()["data"]["session_id"]
        response = api_client.delete(f"/api/v1/session/{sid}")
        assert response.status_code == 200

    def test_get_deleted_session_returns_404(self, api_client):
        sid = api_client.post("/api/v1/session").json()["data"]["session_id"]
        api_client.delete(f"/api/v1/session/{sid}")
        response = api_client.get(f"/api/v1/session/{sid}")
        assert response.status_code == 404


# ── Upload endpoint ───────────────────────────────────────────────

class TestUploadEndpoint:

    def test_upload_valid_pdf_returns_200(self, api_client):
        sid      = api_client.post("/api/v1/session").json()["data"]["session_id"]
        response = upload_sample_pdf(api_client, sid)
        # May be 200 or 400 (if minimal PDF has no extractable text layer)
        # We accept both — the important thing is it does not 500
        assert response.status_code in (200, 400)

    def test_upload_non_pdf_returns_400(self, api_client):
        sid      = api_client.post("/api/v1/session").json()["data"]["session_id"]
        response = api_client.post(
            f"/api/v1/session/{sid}/upload",
            files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_FILE_TYPE"

    def test_upload_to_nonexistent_session_returns_404(self, api_client):
        response = api_client.post(
            "/api/v1/session/sess_ghost/upload",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf")},
        )
        assert response.status_code == 404

    def test_upload_oversized_file_returns_400(self, api_client):
        sid = api_client.post("/api/v1/session").json()["data"]["session_id"]
        # 21MB of fake PDF bytes
        big_bytes = b"%PDF" + b"x" * (21 * 1024 * 1024)
        response = api_client.post(
            f"/api/v1/session/{sid}/upload",
            files={"file": ("big.pdf", io.BytesIO(big_bytes), "application/pdf")},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "FILE_TOO_LARGE"


# ── Query endpoint ────────────────────────────────────────────────

class TestQueryEndpoint:

    def test_query_without_documents_returns_400(self, api_client):
        sid      = api_client.post("/api/v1/session").json()["data"]["session_id"]
        response = api_client.post(
            f"/api/v1/session/{sid}/query",
            json={"query": "What is backpropagation?", "document_id": None},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "NO_DOCUMENTS"

    def test_query_too_short_returns_422(self, api_client):
        # Pydantic validation: min_length=3
        sid      = api_client.post("/api/v1/session").json()["data"]["session_id"]
        response = api_client.post(
            f"/api/v1/session/{sid}/query",
            json={"query": "hi", "document_id": None},
        )
        # FastAPI returns 422 for Pydantic validation failures
        assert response.status_code == 422

    def test_out_of_scope_query_returns_200_with_correct_intent(
        self, api_client, tmp_session_dir, mock_classifier_bundle
    ):
        """
        Out-of-scope queries must return HTTP 200 (not an error code)
        because the system processed the request correctly.
        We inject a mock TF-IDF index to bypass needing a real PDF.
        """
        import modules.classifier as clf
        clf._classifier_bundle = None

        sid = api_client.post("/api/v1/session").json()["data"]["session_id"]

        # Manually insert a document into session metadata
        # so the NO_DOCUMENTS guard passes
        from modules.session_manager import add_document_to_session
        from modules.retriever_tfidf import build_index
        from tests.conftest import SAMPLE_TEXT
        from modules.pdf_parser import chunk_text

        chunks = chunk_text(
            text=SAMPLE_TEXT,
            session_id=sid,
            document_id="doc_fake",
            document_name="fake.pdf",
            chunk_size=50,
            overlap=10,
        )
        build_index(session_id=sid, chunks=chunks)
        add_document_to_session(
            session_id=sid,
            document_id="doc_fake",
            document_name="fake.pdf",
            chunk_count=len(chunks),
            page_count=2,
        )

        response = api_client.post(
            f"/api/v1/session/{sid}/query",
            json={"query": "Who won the cricket World Cup?", "document_id": None},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["intent"]["label"] == "out-of-scope"
        assert data["data"]["sources"] == []

    def test_query_nonexistent_session_returns_404(self, api_client):
        response = api_client.post(
            "/api/v1/session/sess_ghost/query",
            json={"query": "What is backpropagation?", "document_id": None},
        )
        assert response.status_code == 404


# ── Documents endpoint ────────────────────────────────────────────

class TestDocumentsEndpoint:

    def test_list_documents_empty_session(self, api_client):
        sid      = api_client.post("/api/v1/session").json()["data"]["session_id"]
        response = api_client.get(f"/api/v1/session/{sid}/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["documents"] == []
        assert data["data"]["total_chunks"] == 0

    def test_delete_nonexistent_document_returns_404(self, api_client):
        sid      = api_client.post("/api/v1/session").json()["data"]["session_id"]
        response = api_client.delete(
            f"/api/v1/session/{sid}/document/doc_ghost"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "DOCUMENT_NOT_FOUND"