"""Extract and validate a molecular report with Sol and HGNC."""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

from ingestion.model_client import ExtractionError
from ingestion.pdf_reader import PDFReadError
from ingestion.pipeline import ingest_report


def process_report(path, *, output, ocr=False):
    """Use separate processes because the native PDF library is not thread-safe."""
    try:
        result = ingest_report(path, ocr=ocr)
        target = output / (path.stem + ".json")
        target.write_text(result.model_dump_json(indent=2))
        row = {
            "file": path.name,
            "status": "extracted",
            "proposed": len(result.extracted.findings),
            "held_for_review": len(result.rejected_findings),
            "warnings": len(result.warnings),
        }
    except (ExtractionError, PDFReadError, OSError) as exc:
        row = {"file": path.name, "status": "failed", "error": str(exc)}
    print(json.dumps(row), flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, help="Save full extraction audit JSON")
    parser.add_argument("--ocr", action="store_true", help="Enable local Tesseract OCR")
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process a directory of reports into an output directory (two concurrent reports)",
    )
    args = parser.parse_args()
    if args.batch:
        if not args.output or not args.pdf.is_dir():
            parser.error("--batch requires a PDF directory and --output directory")
        paths = sorted(args.pdf.glob("*.pdf"))
        if not paths:
            parser.error("No PDFs found")
        args.output.mkdir(parents=True, exist_ok=True)

        with ProcessPoolExecutor(max_workers=2) as pool:
            rows = list(
                pool.map(
                    partial(process_report, output=args.output, ocr=args.ocr), paths
                )
            )
        (args.output / "summary.json").write_text(json.dumps(rows, indent=2))
        return 1 if any(row["status"] == "failed" for row in rows) else 0
    try:
        result = ingest_report(args.pdf, ocr=args.ocr)
    except (ExtractionError, PDFReadError, OSError) as exc:
        parser.exit(1, f"Ingestion failed: {exc}\n")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2))
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "proposed_findings": len(result.extracted.findings),
                    "held_for_review": len(result.rejected_findings),
                    "warnings": result.warnings,
                }
            )
        )
    else:
        print(json.dumps(result.profile, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
