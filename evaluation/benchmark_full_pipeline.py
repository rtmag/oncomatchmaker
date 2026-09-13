"""Benchmark PDF ingestion and available downstream stages without network calls."""

from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import sqlite3
import statistics
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pdfplumber
import pymupdf

from ingestion.pdf_reader import read_document
from trials.candidate_retrieval import retrieve_candidates

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "evaluation" / "corpus"
SPIKE = ROOT / "evaluation" / "matching_spike"


def _native_stage(path: Path) -> tuple[int, int]:
    """Exercise PyMuPDF block extraction and return pages/text characters."""
    characters = 0
    with pymupdf.open(path) as document:
        for page in document:
            blocks = page.get_text("blocks", sort=True)
            characters += sum(len(block[4]) for block in blocks if block[6] == 0)
        return len(document), characters


def _row_order_stage(path: Path) -> int:
    """Exercise the secondary pdfplumber de-duplication and row ordering."""
    characters = 0
    with pdfplumber.open(path) as document:
        for page in document.pages:
            characters += len(
                page.dedupe_chars(tolerance=1, extra_attrs=()).extract_text(
                    x_tolerance=2, y_tolerance=3
                )
                or ""
            )
    return characters


def _full_read(path_text: str) -> dict:
    path = Path(path_text)
    started = time.perf_counter()
    document = read_document(path, mode="fast")
    return {
        "filename": path.name,
        "seconds": time.perf_counter() - started,
        "pages": len(document.pages),
        "characters": len(document.text),
        "sha256": document.sha256,
        "native_pages": sum(
            page.extraction_method == "native" for page in document.pages
        ),
    }


def _timed(function, *args):
    started = time.perf_counter()
    value = function(*args)
    return time.perf_counter() - started, value


def benchmark(database: Path, workers: int) -> dict:
    paths = sorted(CORPUS.glob("*.pdf"))
    if len(paths) != 12:
        raise RuntimeError(f"Expected 12 local PDFs, found {len(paths)}")

    per_report = []
    for path in paths:
        native_seconds, (pages, native_characters) = _timed(_native_stage, path)
        row_seconds, row_characters = _timed(_row_order_stage, path)
        per_report.append(
            {
                "filename": path.name,
                "pages": pages,
                "bytes": path.stat().st_size,
                "native_seconds": native_seconds,
                "row_order_seconds": row_seconds,
                "native_characters": native_characters,
                "row_order_characters": row_characters,
            }
        )

    sequential_started = time.perf_counter()
    sequential = [_full_read(str(path)) for path in paths]
    sequential_seconds = time.perf_counter() - sequential_started

    parallel_started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        parallel = list(pool.map(_full_read, map(str, paths)))
    parallel_seconds = time.perf_counter() - parallel_started

    profiles = json.loads((SPIKE / "profiles.json").read_text())["cases"]
    retrieval = []
    with sqlite3.connect(database) as db:
        for profile in profiles:
            seconds, candidates = _timed(retrieve_candidates, db, profile)
            retrieval.append(
                {
                    "case_id": profile["case_id"],
                    "seconds": seconds,
                    "candidate_count": len(candidates),
                }
            )

    profile = cProfile.Profile()
    profile.enable()
    _full_read(str(paths[0]))
    profile.disable()
    report = io.StringIO()
    pstats.Stats(profile, stream=report).strip_dirs().sort_stats(
        "cumulative"
    ).print_stats(20)

    native_total = sum(row["native_seconds"] for row in per_report)
    row_total = sum(row["row_order_seconds"] for row in per_report)
    return {
        "benchmark_version": "0.1",
        "reports": len(paths),
        "workers": workers,
        "stage_totals_seconds": {
            "pymupdf_native": native_total,
            "pdfplumber_row_order": row_total,
            "instrumented_sum": native_total + row_total,
            "full_reader_sequential": sequential_seconds,
            "full_reader_parallel": parallel_seconds,
            "candidate_retrieval_four_profiles": sum(
                row["seconds"] for row in retrieval
            ),
        },
        "parallel_speedup": sequential_seconds / parallel_seconds,
        "per_report": per_report,
        "sequential_full_reader": sequential,
        "parallel_full_reader": parallel,
        "candidate_retrieval": retrieval,
        "median_full_reader_seconds": statistics.median(
            row["seconds"] for row in sequential
        ),
        "profile_first_report": report.getvalue(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = benchmark(args.database, args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in ("reports", "stage_totals_seconds", "parallel_speedup")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
