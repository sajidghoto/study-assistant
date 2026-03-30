# backend/tests/test_session_manager.py
#
# Tests for modules/session_manager.py
# All tests use the tmp_session_dir fixture to avoid writing
# to the real data/sessions/ directory.

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from modules.session_manager import (
    create_session,
    load_session,
    save_session,
    add_document_to_session,
    remove_document_from_session,
    delete_session,
    get_session_documents,
    SessionNotFoundError,
    SessionExpiredError,
)


class TestCreateSession:

    def test_returns_metadata_dict(self, tmp_session_dir):
        meta = create_session()
        assert isinstance(meta, dict)

    def test_session_id_has_correct_prefix(self, tmp_session_dir):
        meta = create_session()
        assert meta["session_id"].startswith("sess_")

    def test_session_id_is_unique(self, tmp_session_dir):
        ids = {create_session()["session_id"] for _ in range(10)}
        assert len(ids) == 10, "Duplicate session IDs generated"

    def test_metadata_json_written_to_disk(self, tmp_session_dir):
        from config import settings
        meta = create_session()
        meta_path = settings.sessions_dir / meta["session_id"] / "metadata.json"
        assert meta_path.exists()

    def test_expires_at_is_ttl_hours_after_created(self, tmp_session_dir):
        from config import settings
        meta      = create_session()
        created   = meta["created_at"]
        expires   = meta["expires_at"]
        delta     = expires - created
        expected  = timedelta(hours=settings.session_ttl_hours)
        # Allow 5 second tolerance for slow test runners
        assert abs(delta.total_seconds() - expected.total_seconds()) < 5

    def test_documents_list_is_empty_on_creation(self, tmp_session_dir):
        meta = create_session()
        assert meta["documents"] == []

    def test_total_chunk_count_is_zero_on_creation(self, tmp_session_dir):
        meta = create_session()
        assert meta["total_chunk_count"] == 0


class TestLoadSession:

    def test_loads_existing_session(self, tmp_session_dir):
        meta   = create_session()
        loaded = load_session(meta["session_id"])
        assert loaded["session_id"] == meta["session_id"]

    def test_raises_not_found_for_missing_session(self, tmp_session_dir):
        with pytest.raises(SessionNotFoundError):
            load_session("sess_doesnotexist")

    def test_raises_expired_for_expired_session(self, tmp_session_dir):
        from config import settings
        meta = create_session()
        sid  = meta["session_id"]

        # Manually backdate expires_at
        meta["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
        save_session(sid, meta)

        with pytest.raises(SessionExpiredError):
            load_session(sid)

    def test_expired_session_deleted_from_disk(self, tmp_session_dir):
        from config import settings
        meta = create_session()
        sid  = meta["session_id"]

        meta["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
        save_session(sid, meta)

        try:
            load_session(sid)
        except SessionExpiredError:
            pass

        # Session directory should have been deleted
        session_path = settings.sessions_dir / sid
        assert not session_path.exists()


class TestAddDocument:

    def test_document_appears_in_metadata(self, tmp_session_dir):
        meta = create_session()
        sid  = meta["session_id"]

        updated = add_document_to_session(
            session_id=sid,
            document_id="doc_abc",
            document_name="lecture.pdf",
            chunk_count=42,
            page_count=10,
        )

        assert len(updated["documents"]) == 1
        assert updated["documents"][0]["document_id"] == "doc_abc"

    def test_total_chunk_count_increments(self, tmp_session_dir):
        meta = create_session()
        sid  = meta["session_id"]

        add_document_to_session(
            session_id=sid, document_id="doc_1",
            document_name="a.pdf", chunk_count=30, page_count=5,
        )
        updated = add_document_to_session(
            session_id=sid, document_id="doc_2",
            document_name="b.pdf", chunk_count=20, page_count=3,
        )

        assert updated["total_chunk_count"] == 50

    def test_multiple_documents_stored(self, tmp_session_dir):
        meta = create_session()
        sid  = meta["session_id"]

        for i in range(3):
            add_document_to_session(
                session_id=sid, document_id=f"doc_{i}",
                document_name=f"file_{i}.pdf", chunk_count=10, page_count=2,
            )

        final = load_session(sid)
        assert len(final["documents"]) == 3


class TestRemoveDocument:

    def test_document_removed_from_metadata(self, tmp_session_dir):
        meta = create_session()
        sid  = meta["session_id"]

        add_document_to_session(
            session_id=sid, document_id="doc_abc",
            document_name="lecture.pdf", chunk_count=42, page_count=10,
        )
        updated = remove_document_from_session(sid, "doc_abc")

        assert len(updated["documents"]) == 0

    def test_chunk_count_decrements_correctly(self, tmp_session_dir):
        meta = create_session()
        sid  = meta["session_id"]

        add_document_to_session(
            session_id=sid, document_id="doc_1",
            document_name="a.pdf", chunk_count=30, page_count=5,
        )
        add_document_to_session(
            session_id=sid, document_id="doc_2",
            document_name="b.pdf", chunk_count=20, page_count=3,
        )
        updated = remove_document_from_session(sid, "doc_1")

        assert updated["total_chunk_count"] == 20

    def test_raises_value_error_for_missing_document(self, tmp_session_dir):
        meta = create_session()
        sid  = meta["session_id"]

        with pytest.raises(ValueError):
            remove_document_from_session(sid, "doc_nonexistent")


class TestDeleteSession:

    def test_session_directory_removed(self, tmp_session_dir):
        from config import settings
        meta = create_session()
        sid  = meta["session_id"]

        delete_session(sid)

        assert not (settings.sessions_dir / sid).exists()

    def test_delete_nonexistent_session_does_not_raise(self, tmp_session_dir):
        # delete_session uses ignore_errors=True — should not raise
        delete_session("sess_doesnotexist")