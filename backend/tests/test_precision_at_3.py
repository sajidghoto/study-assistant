import csv
import json
from pathlib import Path

import pytest

from evaluation.retrieval_eval import (
    compute_precision_at_3,
    load_dataset,
    load_human_eval_ids,
    score_automatic_item,
    write_human_annotation_template,
)


EVALUATION_DIR = Path(__file__).parent.parent / "evaluation"


def test_canonical_dataset_has_answerable_and_unanswerable_questions():
    dataset = load_dataset()

    assert len(dataset) == 72
    assert sum(item["answerable"] for item in dataset) == 63
    assert sum(not item["answerable"] for item in dataset) == 9


def test_human_subset_is_a_twenty_question_answerable_subset():
    dataset = load_dataset()
    human_ids = load_human_eval_ids()
    by_id = {item["id"]: item for item in dataset}

    assert len(human_ids) == 20
    assert set(human_ids) <= by_id.keys()
    assert all(by_id[item_id]["answerable"] for item_id in human_ids)


def test_dataset_loader_rejects_duplicate_ids(tmp_path):
    row = {
        "id": "q001",
        "question": "Question?",
        "answerable": True,
        "evidence_keys": ["answer"],
    }
    path = tmp_path / "duplicate.jsonl"
    path.write_text(f"{json.dumps(row)}\n{json.dumps(row)}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate"):
        load_dataset(path)


def test_automatic_metrics_are_explicitly_evidence_key_based():
    item = {
        "id": "q001",
        "question_type": "factual",
        "source_doc": "test",
        "answerable": True,
        "evidence_keys": ["gold phrase", "second fact"],
    }
    chunks = [
        {"chunk_id": "c1", "score": 0.8, "text": "The GOLD phrase appears here."},
        {"chunk_id": "c2", "score": 0.7, "text": "This has the second fact."},
        {"chunk_id": "c3", "score": 0.6, "text": "Unrelated content."},
        {"chunk_id": "c4", "score": 0.5, "text": "gold phrase"},
    ]

    metrics = score_automatic_item(item, chunks)

    assert metrics["hit@1"] == 1.0
    assert metrics["hit@3"] == 1.0
    assert metrics["hit@5"] == 1.0
    assert metrics["mrr"] == 1.0
    assert metrics["key_recall@3"] == 1.0
    assert metrics["evidence_precision@3"] == pytest.approx(2 / 3)


@pytest.fixture
def annotations_csv(tmp_path):
    path = tmp_path / "annotated.csv"
    rows = [
        ("q001", 1, "a1", "Y"),
        ("q001", 2, "a2", "N"),
        ("q001", 3, "a3", "yes"),
        ("q002", 1, "b1", "0"),
        ("q002", 2, "b2", "true"),
        ("q002", 3, "b3", "false"),
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["query_id", "chunk_rank", "chunk_id", "is_relevant"])
        writer.writerows(rows)
    return path


def test_compute_precision_at_3_averages_complete_annotations(annotations_csv):
    overall, per_query = compute_precision_at_3(annotations_csv)

    assert per_query == {"q001": 2 / 3, "q002": 1 / 3}
    assert overall == pytest.approx(0.5)


def test_compute_precision_at_3_rejects_unannotated_rows(annotations_csv):
    with annotations_csv.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    rows[0]["is_relevant"] = ""
    with annotations_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="not annotated"):
        compute_precision_at_3(annotations_csv)


def test_compute_precision_at_3_rejects_incomplete_rankings(annotations_csv):
    with annotations_csv.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    rows.pop()
    with annotations_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="exactly ranks 1-3"):
        compute_precision_at_3(annotations_csv)


def test_compute_precision_at_3_rejects_retrieval_errors(annotations_csv):
    with annotations_csv.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    rows[0]["chunk_id"] = "ERROR"
    rows[0]["is_relevant"] = "N/A"
    with annotations_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="retrieval errors"):
        compute_precision_at_3(annotations_csv)


def test_compute_precision_at_3_requires_expected_human_subset(annotations_csv):
    with pytest.raises(ValueError, match="do not match the human subset"):
        compute_precision_at_3(annotations_csv, ["q001", "q003"])


def test_annotation_template_contains_three_ranked_chunks_per_human_query(tmp_path):
    dataset = [
        {
            "id": "q001",
            "question": "Question?",
            "answerable": True,
        }
    ]
    output_path = tmp_path / "template.csv"
    write_human_annotation_template(
        dataset,
        {"q001": [{"chunk_id": "c1", "text": "Candidate text."}]},
        ["q001"],
        output_path,
    )

    with output_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert [row["chunk_rank"] for row in rows] == ["1", "2", "3"]
    assert [row["is_relevant"] for row in rows] == ["", "N", "N"]
