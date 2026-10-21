from modules import retriever_semantic


class FakeCollection:
    def __init__(self, ids, metadatas):
        self.ids = ids
        self.metadatas = metadatas
        self.deleted_ids = []

    def get(self, include):
        assert include == ["metadatas"]
        return {"ids": self.ids, "metadatas": self.metadatas}

    def delete(self, ids):
        self.deleted_ids.extend(ids)


def test_retain_documents_deletes_only_removed_document_chunks(monkeypatch):
    collection = FakeCollection(
        ids=["chunk_a_1", "chunk_b_1", "chunk_a_2"],
        metadatas=[
            {"document_id": "doc_a"},
            {"document_id": "doc_b"},
            {"document_id": "doc_a"},
        ],
    )
    monkeypatch.setattr(
        retriever_semantic,
        "_get_collection",
        lambda session_id: collection,
    )

    retriever_semantic.retain_documents("sess_test", ["doc_b"])

    assert collection.deleted_ids == ["chunk_a_1", "chunk_a_2"]


def test_retain_no_documents_deletes_all_indexed_chunks(monkeypatch):
    collection = FakeCollection(
        ids=["chunk_a_1", "chunk_b_1"],
        metadatas=[
            {"document_id": "doc_a"},
            {"document_id": "doc_b"},
        ],
    )
    monkeypatch.setattr(
        retriever_semantic,
        "_get_collection",
        lambda session_id: collection,
    )

    retriever_semantic.retain_documents("sess_test", [])

    assert collection.deleted_ids == ["chunk_a_1", "chunk_b_1"]


def test_retain_all_documents_does_not_delete_chunks(monkeypatch):
    collection = FakeCollection(
        ids=["chunk_a_1"],
        metadatas=[{"document_id": "doc_a"}],
    )
    monkeypatch.setattr(
        retriever_semantic,
        "_get_collection",
        lambda session_id: collection,
    )

    retriever_semantic.retain_documents("sess_test", ["doc_a"])

    assert collection.deleted_ids == []
