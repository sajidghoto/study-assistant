# backend/evaluation/precision_at_3.py
#
# Precision@3 Retrieval Evaluation Script
#
# Purpose:
#   Evaluate the quality of the retrieval system by:
#   1. Loading 20 manually prepared test questions
#   2. Retrieving top-3 chunks for each using the active retriever
#   3. Saving results to CSV for manual relevance annotation
#   4. Computing Precision@3 (if manual annotations are provided)
#
# Usage (retrieval phase):
#   python evaluation/precision_at_3.py --session <session_id>
#   python evaluation/precision_at_3.py --list-sessions
#
# Usage (computation phase — after manual annotation):
#   python evaluation/precision_at_3.py --compute
#
# Output:
#   evaluation/results/precision_at_3_results.csv
#     - Columns: query_id, query, chunk_rank (1-3), chunk_id,
#       document_name, score, chunk_text_preview, is_relevant (manual annotation)
#   evaluation/results/precision_at_3_scores.txt
#     - Precision@3 per query and overall statistics

import sys
import csv
import argparse
from pathlib import Path
from datetime import datetime

import pandas as pd

# Add backend to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from modules.session_manager import (
    load_session,
    SessionNotFoundError,
    SessionExpiredError,
)

# Select retriever based on config
if settings.retrieval_mode == "semantic":
    from modules.retriever_semantic import query_index
else:
    from modules.retriever_tfidf import query_index


# ── Configuration ─────────────────────────────────────────────────

TEST_QUERIES_PATH = Path(__file__).parent / "test_queries.csv"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_CSV = RESULTS_DIR / "precision_at_3_results.csv"
SCORES_TXT = RESULTS_DIR / "precision_at_3_scores.txt"

# Color codes for console output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
END = "\033[0m"


def _ensure_results_dir() -> None:
    """Create results directory if it doesn't exist."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_test_queries() -> list[str]:
    """
    Load test queries from test_queries.csv.

    Expected format: One query per line (single column, no header).
    Blank lines are skipped.

    Returns:
        List of non-empty query strings
    """
    if not TEST_QUERIES_PATH.exists():
        raise FileNotFoundError(
            f"Test queries file not found: {TEST_QUERIES_PATH}\n"
            "Create backend/evaluation/test_queries.csv with one query per line."
        )

    queries = []
    with open(TEST_QUERIES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            query = line.strip()
            if query:  # Skip blank lines
                queries.append(query)

    return queries


def list_available_sessions(with_documents_only: bool = False) -> list[str]:
    """
    List all available session IDs from data/sessions/ directory.

    Args:
        with_documents_only: If True, only return sessions that have ≥1 documents

    Returns:
        List of session IDs (sorted by creation time, newest first)
    """
    if not settings.sessions_dir.exists():
        return []

    sessions_with_meta = []

    for d in settings.sessions_dir.iterdir():
        if not d.is_dir() or d.name == ".gitkeep":
            continue

        # Try to load metadata to get creation time and document count
        try:
            metadata = load_session(d.name)
            doc_count = len(metadata.get("documents", []))

            # Skip empty sessions if filter is enabled
            if with_documents_only and doc_count == 0:
                continue

            created_at = metadata.get("created_at")
            sessions_with_meta.append((d.name, created_at, doc_count))

        except (SessionNotFoundError, SessionExpiredError):
            # Skip expired or invalid sessions
            continue

    # Sort by creation time (newest first)
    sessions_with_meta.sort(key=lambda x: x[1], reverse=True)

    return [sid for sid, _, _ in sessions_with_meta]


def validate_session(session_id: str) -> dict:
    """
    Validate that a session exists and has documents.

    Args:
        session_id: Session ID to validate

    Returns:
        Session metadata dict

    Raises:
        SessionNotFoundError: If session doesn't exist
        SessionExpiredError: If session has expired
        ValueError: If session has no documents
    """
    try:
        metadata = load_session(session_id)
    except SessionNotFoundError:
        raise SessionNotFoundError(f"Session '{session_id}' not found.")
    except SessionExpiredError:
        raise SessionExpiredError(f"Session '{session_id}' has expired.")

    if len(metadata.get("documents", [])) == 0:
        raise ValueError(
            f"Session '{session_id}' has no documents. "
            "Upload PDFs to this session before running evaluation."
        )

    return metadata


def evaluate_retrieval(session_id: str) -> None:
    """
    Main evaluation workflow:
    1. Load test queries
    2. Retrieve top-3 chunks for each query
    3. Save results to CSV for manual annotation
    4. Display summary statistics

    Args:
        session_id: Session ID containing indexed documents
    """
    print(f"\n{BLUE}{'='*75}")
    print(f"Precision@3 Retrieval Evaluation")
    print(f"{'='*75}{END}\n")

    # ── Load and validate ─────────────────────────────────────────
    print(f"Loading test queries from {TEST_QUERIES_PATH.name}...")
    queries = load_test_queries()
    print(f"{GREEN}✓{END} Loaded {len(queries)} test queries\n")

    print(f"Validating session '{session_id}'...")
    metadata = validate_session(session_id)
    doc_count = len(metadata["documents"])
    chunk_count = metadata.get("chunk_count", 0)
    print(f"{GREEN}✓{END} Session valid. Documents: {doc_count}, Chunks: {chunk_count}\n")

    # ── Retrieve for each query ───────────────────────────────────
    print(f"Retrieving top-{settings.top_k_chunks} chunks for each query...")
    print(f"Retrieval mode: {settings.retrieval_mode.upper()}")
    print(f"Confidence threshold: {settings.retrieval_confidence_threshold}\n")

    results = []
    errors = 0

    for query_id, query in enumerate(queries, 1):
        try:
            chunks = query_index(
                session_id=session_id,
                query_text=query,
                document_id=None,  # Search all documents
                top_k=settings.top_k_chunks,
            )

            # Format chunks for CSV
            for rank, chunk in enumerate(chunks, 1):
                # Truncate chunk text for readability
                chunk_preview = chunk["text"][:250].replace("\n", " ")

                results.append({
                    "query_id": query_id,
                    "query": query,
                    "chunk_rank": rank,
                    "chunk_id": chunk["chunk_id"],
                    "document_name": chunk["document_name"],
                    "score": round(chunk["score"], 4),
                    "chunk_text_preview": chunk_preview,
                    "is_relevant": "",  # Empty — for manual annotation
                })

            # Progress indicator
            if query_id % 5 == 0:
                print(f"  {query_id:2d}/{len(queries)} {GREEN}✓{END}")

        except Exception as e:
            errors += 1
            print(f"  {query_id:2d}/{len(queries)} {RED}✗ {str(e)[:50]}{END}")
            # Still add a result row for tracking
            results.append({
                "query_id": query_id,
                "query": query,
                "chunk_rank": 1,
                "chunk_id": "ERROR",
                "document_name": "",
                "score": 0.0,
                "chunk_text_preview": f"Retrieval failed: {str(e)[:100]}",
                "is_relevant": "N/A",
            })

    print(f"  {len(queries):2d}/{len(queries)} {GREEN}✓{END}\n")

    if errors > 0:
        print(f"{YELLOW}⚠ {errors} query retrieval(s) failed{END}\n")

    # ── Save results to CSV ───────────────────────────────────────
    print(f"Saving results to {RESULTS_CSV.name}...")
    _ensure_results_dir()

    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "query_id",
                "query",
                "chunk_rank",
                "chunk_id",
                "document_name",
                "score",
                "chunk_text_preview",
                "is_relevant",
            ]
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"{GREEN}✓{END} Results saved to {RESULTS_CSV.name}\n")

    # ── Summary statistics ────────────────────────────────────────
    print(f"Summary Statistics")
    print(f"-" * 75)

    df = pd.DataFrame(results)
    valid_scores = df[df["score"] > 0]["score"]

    print(f"Total queries: {len(queries)}")
    print(f"Total chunks retrieved: {len(results)}")
    print(f"Retrieval success rate: {((len(queries) - errors) / len(queries) * 100):.1f}%")

    if len(valid_scores) > 0:
        print(f"Average score across all chunks: {valid_scores.mean():.4f}")
        print(f"Score range: {valid_scores.min():.4f} — {valid_scores.max():.4f}")
        print(f"Median score: {valid_scores.median():.4f}")

    # Average scores per query
    per_query_avg = df[df["score"] > 0].groupby("query_id")["score"].mean()
    if len(per_query_avg) > 0:
        print(f"Average score per query: {per_query_avg.mean():.4f}")

    print(f"\n")

    # ── Instructions for annotation ───────────────────────────────
    print(f"Next Steps for Manual Annotation")
    print(f"-" * 75)
    print(f"1. {BLUE}Open{END} {RESULTS_CSV.name} in a spreadsheet editor (Excel, Sheets, etc.)")
    print(f"2. {BLUE}Review{END} each chunk's relevance to its query")
    print(f"3. {BLUE}Fill{END} the 'is_relevant' column for each row:")
    print(f"   • Y / yes / 1 / true → chunk is relevant to the query")
    print(f"   • N / no / 0 / false → chunk is NOT relevant")
    print(f"   • Leave blank for error rows")
    print(f"4. {BLUE}Save{END} the annotated CSV")
    print(f"5. {BLUE}Run{END} computation: python evaluation/precision_at_3.py --compute\n")


def compute_precision_at_3(
    results_csv: Path = RESULTS_CSV,
) -> tuple[float, dict]:
    """
    Compute Precision@3 from manually annotated results.

    Precision@3 = (# of relevant chunks in top-3) / 3
    Per query, then averaged across all queries.

    Args:
        results_csv: Path to annotated results CSV

    Returns:
        (overall_precision, per_query_dict)
    """
    if not results_csv.exists():
        raise FileNotFoundError(
            f"Results file not found: {results_csv}\n"
            "Run retrieval phase first: python evaluation/precision_at_3.py"
        )

    df = pd.read_csv(results_csv)

    # Parse relevance: case-insensitive matching
    df["is_relevant_bool"] = df["is_relevant"].fillna("").str.lower().isin(
        ["y", "yes", "1", "true"]
    )

    # Group by query and calculate Precision@3
    per_query_scores = {}

    for query_id in sorted(df["query_id"].unique()):
        query_chunks = df[df["query_id"] == query_id]

        # Should have exactly 3 chunks
        if len(query_chunks) < 3:
            print(f"{YELLOW}Warning: Query {query_id} has {len(query_chunks)} chunks (expected 3){END}")
            continue

        relevant_count = query_chunks["is_relevant_bool"].sum()
        precision_at_3 = relevant_count / 3.0
        per_query_scores[query_id] = precision_at_3

    # Overall Precision@3
    overall_precision = (
        sum(per_query_scores.values()) / len(per_query_scores)
        if per_query_scores else 0.0
    )

    return overall_precision, per_query_scores


def save_scores(overall_precision: float, per_query_scores: dict) -> None:
    """Save computed Precision@3 scores to results file."""
    _ensure_results_dir()

    with open(SCORES_TXT, "w", encoding="utf-8") as f:
        f.write("Precision@3 Evaluation Results\n")
        f.write("=" * 75 + "\n")
        f.write(f"Computed at: {datetime.now().isoformat()}\n")
        f.write(f"Retrieval mode: {settings.retrieval_mode.upper()}\n\n")

        f.write("Per-Query Scores\n")
        f.write("-" * 75 + "\n")
        for query_id in sorted(per_query_scores.keys()):
            score = per_query_scores[query_id]
            relevant_count = int(score * 3)
            f.write(f"Query {query_id:2d}: {score:.2%}  ({relevant_count}/3 relevant)\n")

        f.write("\n")
        f.write("Overall Statistics\n")
        f.write("-" * 75 + "\n")
        f.write(f"Overall Precision@3: {overall_precision:.4f} ({overall_precision:.2%})\n")
        f.write(f"Total queries evaluated: {len(per_query_scores)}\n")
        f.write(f"Target benchmark: ≥ 0.67 (at least 2/3 chunks relevant)\n")


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate retrieval system Precision@3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  Retrieve & prepare for annotation:\n"
            "    python precision_at_3.py --session sess_fe76ec91\n"
            "    python precision_at_3.py  # uses first available session\n"
            "\n"
            "  List available sessions:\n"
            "    python precision_at_3.py --list-sessions\n"
            "\n"
            "  Compute scores from annotated CSV:\n"
            "    python precision_at_3.py --compute\n"
        )
    )

    parser.add_argument(
        "--session",
        type=str,
        help="Session ID to evaluate (default: first available)"
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List available sessions and exit"
    )
    parser.add_argument(
        "--compute",
        action="store_true",
        help="Compute Precision@3 from annotated results (requires prior annotation)"
    )

    args = parser.parse_args()

    # ── List sessions ─────────────────────────────────────────────
    if args.list_sessions:
        sessions = list_available_sessions()
        if not sessions:
            print("No sessions found.")
            return

        print(f"\n{BLUE}Available Sessions{END}\n")
        for sid in sessions:
            try:
                metadata = validate_session(sid)
                doc_count = len(metadata["documents"])
                chunk_count = metadata.get("chunk_count", "?")
                print(f"  {GREEN}{sid}{END:20s}  {doc_count} doc(s), {chunk_count} chunk(s)")
            except Exception as e:
                print(f"  {RED}{sid}{END:20s}  error: {str(e)[:50]}")
        print()
        return

    # ── Compute mode ──────────────────────────────────────────────
    if args.compute:
        print(f"\n{BLUE}{'='*75}")
        print(f"Computing Precision@3 from Annotated Results")
        print(f"{'='*75}{END}\n")

        try:
            overall, per_query = compute_precision_at_3()

            if len(per_query) == 0:
                print(f"{RED}No annotated data found. Please annotate the CSV first.{END}\n")
                return

            save_scores(overall, per_query)

            print(f"Precision@3 Computation Complete")
            print(f"-" * 75)
            print(f"{GREEN}Overall Precision@3: {overall:.4f} ({overall:.2%}){END}")
            print(f"Queries evaluated: {len(per_query)}")

            if overall >= 0.67:
                print(f"{GREEN}✓ Target benchmark achieved (≥ 0.67){END}")
            else:
                print(f"{YELLOW}⚠ Below target benchmark (< 0.67){END}")

            print(f"\nScores saved to {SCORES_TXT}\n")

        except Exception as e:
            print(f"{RED}Error: {e}{END}\n")
            sys.exit(1)
        return

    # ── Retrieval evaluation mode ─────────────────────────────────
    # Select session
    if args.session:
        session_id = args.session
    else:
        sessions = list_available_sessions()
        if not sessions:
            print(f"{RED}Error: No sessions found.{END}")
            print(f"Create a session and upload documents first.\n")
            sys.exit(1)

        # Use first available session
        session_id = sessions[0]
        print(f"Using first available session: {BLUE}{session_id}{END}\n")

    try:
        evaluate_retrieval(session_id)
    except Exception as e:
        print(f"{RED}Error: {e}{END}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()