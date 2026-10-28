"""Automatic evidence-key retrieval evaluation and human Precision@3 scoring."""

import argparse
import csv
import json
import re
from pathlib import Path
from statistics import mean
from typing import Callable


HERE = Path(__file__).parent
DEFAULT_DATASET = HERE / "rag_eval_dataset.jsonl"
DEFAULT_HUMAN_IDS = HERE / "human_eval_ids.json"
RESULTS_DIR = HERE / "results"
ANNOTATION_VALUES = {
    "y": True,
    "yes": True,
    "true": True,
    "1": True,
    "n": False,
    "no": False,
    "false": False,
    "0": False,
}


def load_dataset(path: Path = DEFAULT_DATASET) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        dataset = [json.loads(line) for line in file if line.strip()]

    ids = set()
    for item in dataset:
        required = {"id", "question", "answerable", "evidence_keys"}
        missing = required - item.keys()
        if missing:
            raise ValueError(f"{item.get('id', 'Dataset row')} is missing fields: {sorted(missing)}")
        if item["id"] in ids:
            raise ValueError(f"Duplicate evaluation question id: {item['id']}")
        if not isinstance(item["answerable"], bool):
            raise ValueError(f"{item['id']} must have a boolean answerable value")
        if item["answerable"] and not item["evidence_keys"]:
            raise ValueError(f"Answerable question {item['id']} must have evidence_keys")
        if not item["answerable"] and item["evidence_keys"]:
            raise ValueError(f"Unanswerable question {item['id']} must not have evidence_keys")
        ids.add(item["id"])

    if not dataset:
        raise ValueError("The evaluation dataset is empty")
    return dataset


def load_human_eval_ids(path: Path = DEFAULT_HUMAN_IDS) -> list[str]:
    with path.open(encoding="utf-8") as file:
        ids = json.load(file)
    if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
        raise ValueError("Human evaluation ids must be a non-empty list of unique question ids")
    return ids


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def relevant_keys(chunk_text: str, keys: list[str]) -> set[str]:
    normalized_text = normalize(chunk_text)
    return {key for key in keys if normalize(key) in normalized_text}


def score_automatic_item(item: dict, chunks: list[dict]) -> dict:
    top1_score = float(chunks[0]["score"]) if chunks else 0.0
    result = {
        "id": item["id"],
        "type": item.get("question_type", ""),
        "source_doc": item.get("source_doc", ""),
        "answerable": item["answerable"],
        "top1_score": top1_score,
        "top_chunk_id": chunks[0]["chunk_id"] if chunks else "",
    }
    if not item["answerable"]:
        return result

    flags = [relevant_keys(chunk["text"], item["evidence_keys"]) for chunk in chunks]
    top3 = flags[:3]
    first_relevant = next((rank for rank, keys in enumerate(flags, start=1) if keys), None)
    covered_keys = set().union(*top3) if top3 else set()
    result.update(
        {
            "hit@1": float(bool(flags and flags[0])),
            "hit@3": float(any(top3)),
            "hit@5": float(any(flags[:5])),
            "mrr": 1.0 / first_relevant if first_relevant else 0.0,
            "key_recall@3": len(covered_keys) / len(item["evidence_keys"]),
            "evidence_precision@3": sum(bool(keys) for keys in top3) / 3.0,
        }
    )
    return result


def summarize(label: str, items: list[dict]) -> str:
    if not items:
        return f"{label}: (none)"
    return (
        f"{label:<24} n={len(items):<3} "
        f"Hit@1={mean(item['hit@1'] for item in items):.2f} "
        f"Hit@3={mean(item['hit@3'] for item in items):.2f} "
        f"Hit@5={mean(item['hit@5'] for item in items):.2f} "
        f"MRR={mean(item['mrr'] for item in items):.2f} "
        f"KeyRecall@3={mean(item['key_recall@3'] for item in items):.2f} "
        f"Evidence-P@3={mean(item['evidence_precision@3'] for item in items):.2f}"
    )


def gate_sweep(answerable: list[dict], unanswerable: list[dict], current_threshold: float) -> list[str]:
    lines = [
        "Diagnostic threshold sweep (not a held-out threshold selection):",
        "threshold  answered(answerable)  refused(unanswerable)  balanced",
    ]
    for threshold in (round(step * 0.05, 2) for step in range(1, 13)):
        answered_rate = (
            mean(float(item["top1_score"] >= threshold) for item in answerable) if answerable else 0.0
        )
        refused_rate = (
            mean(float(item["top1_score"] < threshold) for item in unanswerable) if unanswerable else 0.0
        )
        balanced = (answered_rate + refused_rate) / 2
        lines.append(
            f"{threshold:>8.2f}  {answered_rate:>20.2f}  {refused_rate:>21.2f}  {balanced:>8.2f}"
        )
    lines.append(f"\nConfigured threshold: {current_threshold}")
    return lines


def write_human_annotation_template(
    dataset: list[dict],
    chunks_by_id: dict[str, list[dict]],
    human_ids: list[str],
    output_path: Path,
) -> None:
    items_by_id = {item["id"]: item for item in dataset}
    unknown_ids = set(human_ids) - items_by_id.keys()
    if unknown_ids:
        raise ValueError(f"Human evaluation ids are absent from the dataset: {sorted(unknown_ids)}")
    unanswerable_ids = [item_id for item_id in human_ids if not items_by_id[item_id]["answerable"]]
    if unanswerable_ids:
        raise ValueError(f"Human relevance annotation subset must be answerable: {unanswerable_ids}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["query_id", "question", "chunk_rank", "chunk_id", "chunk_text", "is_relevant"]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for item_id in human_ids:
            item = items_by_id[item_id]
            chunks = chunks_by_id[item_id][:3]
            for rank in range(1, 4):
                if rank <= len(chunks):
                    chunk = chunks[rank - 1]
                    chunk_id = chunk["chunk_id"]
                    chunk_text = re.sub(r"\s+", " ", chunk["text"])
                    judgment = ""
                else:
                    chunk_id = "NO_RESULT"
                    chunk_text = ""
                    judgment = "N"
                writer.writerow(
                    {
                        "query_id": item_id,
                        "question": item["question"],
                        "chunk_rank": rank,
                        "chunk_id": chunk_id,
                        "chunk_text": chunk_text,
                        "is_relevant": judgment,
                    }
                )


def compute_precision_at_3(
    annotations_path: Path,
    expected_query_ids: list[str] | None = None,
) -> tuple[float, dict[str, float]]:
    with annotations_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        required_fields = {"query_id", "chunk_rank", "chunk_id", "is_relevant"}
        if not required_fields.issubset(reader.fieldnames or []):
            raise ValueError(f"Annotation CSV must include fields: {sorted(required_fields)}")
        rows = list(reader)

    grouped: dict[str, dict[int, bool]] = {}
    for row in rows:
        query_id = row["query_id"].strip()
        if not query_id:
            raise ValueError("Annotation CSV contains a row without a query_id")
        chunk_id = row["chunk_id"].strip()
        if chunk_id == "ERROR":
            raise ValueError("Annotation CSV contains retrieval errors")
        try:
            rank = int(row["chunk_rank"])
        except (TypeError, ValueError) as error:
            raise ValueError(f"{query_id} has an invalid chunk rank") from error
        if rank not in (1, 2, 3):
            raise ValueError(f"{query_id} must have exactly ranks 1-3")
        if rank in grouped.setdefault(query_id, {}):
            raise ValueError(f"{query_id} has duplicate rank {rank}")
        raw_judgment = row["is_relevant"].strip().lower()
        if raw_judgment not in ANNOTATION_VALUES:
            raise ValueError(f"{query_id} rank {rank} is not annotated")
        judgment = ANNOTATION_VALUES[raw_judgment]
        if not chunk_id:
            raise ValueError(f"{query_id} rank {rank} has no chunk_id")
        if chunk_id == "NO_RESULT" and judgment:
            raise ValueError(f"{query_id} rank {rank} has no retrieved chunk to mark relevant")
        grouped[query_id][rank] = judgment

    for query_id, judgments in grouped.items():
        if set(judgments) != {1, 2, 3}:
            raise ValueError(f"{query_id} must have exactly ranks 1-3")
    if expected_query_ids is not None and set(grouped) != set(expected_query_ids):
        missing = sorted(set(expected_query_ids) - set(grouped))
        unexpected = sorted(set(grouped) - set(expected_query_ids))
        raise ValueError(f"Annotation query ids do not match the human subset; missing={missing}, unexpected={unexpected}")
    if not grouped:
        raise ValueError("Annotation CSV contains no query judgments")

    per_query = {
        query_id: sum(judgments.values()) / 3.0
        for query_id, judgments in grouped.items()
    }
    return mean(per_query.values()), per_query


def _format_automatic_report(
    rows: list[dict],
    current_threshold: float,
    current_mode: str,
) -> str:
    answerable = [row for row in rows if row["answerable"]]
    unanswerable = [row for row in rows if not row["answerable"]]
    lines = [
        f"Retrieval mode: {current_mode}",
        "Automatic evidence-key matching (diagnostic; not human relevance judgments)",
        summarize("ALL answerable", answerable),
        "",
    ]
    for source_doc in sorted({item.get("source_doc", "") for item in answerable}):
        lines.append(
            summarize(
                f"doc={source_doc}",
                [item for item in answerable if item.get("source_doc") == source_doc],
            )
        )
    lines.extend(["", f"Unanswerable questions: {len(unanswerable)}"])
    lines.extend(gate_sweep(answerable, unanswerable, current_threshold))
    lines.extend(
        [
            "",
            "Misses (automatic evidence Hit@3 = 0):",
            *[
                f"  {item['id']} ({item['type']}) top1={item['top1_score']:.4f}"
                for item in answerable
                if item["hit@3"] == 0.0
            ],
        ]
    )
    return "\n".join(lines)


def run_evaluation(
    session_id: str,
    dataset: list[dict],
    human_ids: list[str],
    retrieve: Callable[[str, str, int], list[dict]],
    mode: str,
    current_threshold: float,
    results_dir: Path = RESULTS_DIR,
) -> str:
    chunks_by_id = {
        item["id"]: retrieve(session_id, item["question"], 5)
        for item in dataset
    }
    rows = [score_automatic_item(item, chunks_by_id[item["id"]]) for item in dataset]
    report = _format_automatic_report(rows, current_threshold, mode)

    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"auto_eval_{mode}.txt").write_text(report, encoding="utf-8")
    with (results_dir / f"auto_eval_{mode}_items.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        fields = list(rows[0].keys())
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    write_human_annotation_template(
        dataset,
        chunks_by_id,
        human_ids,
        results_dir / f"human_annotations_{mode}_template.csv",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run automatic retrieval evaluation or score human judgments")
    parser.add_argument("--session", help="Session containing the indexed evaluation PDFs")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--human-ids", type=Path, default=DEFAULT_HUMAN_IDS)
    parser.add_argument("--annotations", type=Path, help="Completed human annotation CSV to score")
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    human_ids = load_human_eval_ids(args.human_ids)
    if args.annotations:
        overall, per_query = compute_precision_at_3(args.annotations, human_ids)
        print(f"Human-annotated Precision@3 (n={len(per_query)}): {overall:.3f}")
        return
    if not args.session:
        parser.error("--session is required unless --annotations is supplied")

    from config import settings
    from modules.session_manager import load_session

    load_session(args.session)
    if settings.retrieval_mode == "semantic":
        from modules.retriever_semantic import query_index
    elif settings.retrieval_mode == "tfidf":
        from modules.retriever_tfidf import query_index
    else:
        raise ValueError(f"Unsupported retrieval mode: {settings.retrieval_mode}")

    def retrieve(session_id: str, question: str, k: int) -> list[dict]:
        return query_index(
            session_id=session_id,
            query_text=question,
            document_id=None,
            top_k=k,
        ) or []

    report = run_evaluation(
        args.session,
        dataset,
        human_ids,
        retrieve,
        settings.retrieval_mode,
        settings.retrieval_confidence_threshold,
    )
    print(report)


if __name__ == "__main__":
    main()
