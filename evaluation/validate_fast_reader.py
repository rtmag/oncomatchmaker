"""Validate fast-reader source landmarks without performing model inference."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from ingestion.pdf_reader import read_document

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "evaluation" / "corpus"
LANDMARKS = ROOT / "evaluation" / "ingestion_landmarks.json"


def compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def validate_case(path: Path, landmark: dict) -> dict:
    started = time.perf_counter()
    document = read_document(path, mode="fast")
    seconds = time.perf_counter() - started
    text = compact(document.text)
    checks = {
        "disease": compact(landmark["disease_contains"]) in text,
        "expected_findings": all(
            compact(finding["gene"]) in text
            and compact(finding.get("alteration_contains", "")) in text
            and compact(finding.get("partner", "")) in text
            for finding in landmark["expected"]
        ),
    }
    if landmark.get("negative"):
        checks["negative_report"] = "noreportablepathogenicvariants" in text
    if landmark.get("msi"):
        checks["msi"] = compact(landmark["msi"]) in text
    prefix = landmark["prefix"]
    if prefix == "03_":
        checks["ch_context"] = "clonalhematopoiesis" in text
    if prefix == "10_":
        checks["paired_normal_germline_context"] = "germline" in text and (
            "pairednormal" in text
            or "tumornormalpairedanalysis" in text
            or "matchednormalsample" in text
        )
    if prefix == "13_":
        checks["ch_context"] = (
            "clonalhematopoiesis" in text and "dnmt3a" in text and "kdm6a" in text
        )
    if prefix == "14_":
        checks["mmr_proficient"] = (
            "mismatchrepairstatus" in text and "proficientintact" in text
        )
        checks["not_msi_high"] = "msistable" in text
    return {
        "filename": path.name,
        "pages": len(document.pages),
        "fast_reader_seconds": round(seconds, 3),
        "reader_version": document.reader_version,
        "source_sha256": document.sha256,
        "checks": checks,
        "passed": all(checks.values()),
        "warnings": document.warnings,
    }


def run() -> list[dict]:
    landmarks = json.loads(LANDMARKS.read_text())["cases"]
    rows = []
    for landmark in landmarks:
        matches = list(CORPUS.glob(landmark["prefix"] + "*.pdf"))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one PDF for {landmark['prefix']}")
        rows.append(validate_case(matches[0], landmark))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"reports": rows}, indent=2) + "\n")
    print(
        json.dumps(
            {
                "reports": len(rows),
                "passed": sum(row["passed"] for row in rows),
                "total_seconds": round(
                    sum(row["fast_reader_seconds"] for row in rows), 3
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
