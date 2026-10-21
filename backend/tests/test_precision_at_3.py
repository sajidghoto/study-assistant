import csv

import pytest

from evaluation.precision_at_3 import compute_precision_at_3, load_test_queries


def test_load_test_queries_reads_the_evaluation_set():
    queries = load_test_queries()

    assert len(queries) == 20
    assert queries[0] == "What is machine learning?"


@pytest.fixture
def results_csv(tmp_path):
    path = tmp_path / "annotated.csv"
    rows = [
        (1, 1, "a1", "Y"),
        (1, 2, "a2", "N"),
        (1, 3, "a3", "yes"),
        (2, 1, "b1", "0"),
        (2, 2, "b2", "true"),
        (2, 3, "b3", "false"),
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["query_id", "chunk_rank", "chunk_id", "is_relevant"])
        writer.writerows(rows)
    return path


def test_compute_precision_at_3_averages_complete_query_annotations(results_csv):
    overall, per_query = compute_precision_at_3(results_csv)

    assert per_query == {1: 2 / 3, 2: 1 / 3}
    assert overall == pytest.approx(0.5)


def test_compute_precision_at_3_rejects_unannotated_rows(results_csv):
    with results_csv.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    rows[0]["is_relevant"] = ""
    with results_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="not annotated"):
        compute_precision_at_3(results_csv)


def test_compute_precision_at_3_rejects_incomplete_rankings(results_csv):
    with results_csv.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    rows.pop()
    with results_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="exactly ranks 1-3"):
        compute_precision_at_3(results_csv)


def test_compute_precision_at_3_rejects_retrieval_errors(results_csv):
    with results_csv.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    rows[0]["chunk_id"] = "ERROR"
    rows[0]["is_relevant"] = "N/A"
    with results_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="retrieval errors"):
        compute_precision_at_3(results_csv)
