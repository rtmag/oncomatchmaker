"""Run selected public reports through the integrated local POC."""

import argparse
import json
from pathlib import Path

from trials.geography import PatientLocation
from trials.integrated_pipeline import run_recorded_case

ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "evaluation" / "matching_spike"
LOCATIONS = {
    "fmi-lung-egfr-l858r": PatientLocation("Singapore", "Singapore", 1.3521, 103.8198),
    "fmi-nsclc-met-exon14": PatientLocation(
        "New York", "United States", 40.7128, -74.0060
    ),
    "fmi-prostate-brca2-loss": PatientLocation(
        "Sydney", "Australia", -33.8688, 151.2093
    ),
    "tempus-metastatic-colon-msih": PatientLocation("Paris", "France", 48.8566, 2.3522),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture-dir", type=Path)
    args = parser.parse_args()
    profiles = json.loads((SPIKE / "profiles.json").read_text())["cases"]
    assessments = json.loads((SPIKE / "chatgpt_assessments.json").read_text())[
        "assessments"
    ]
    output = []
    for profile in profiles:
        case_id = profile["case_id"]
        if case_id not in LOCATIONS:
            continue
        reviews = [row for row in assessments if row["case_id"] == case_id]
        output.append(
            run_recorded_case(
                pdf_path=ROOT / "evaluation" / "corpus" / profile["source_pdf"],
                profile=profile,
                reviews=reviews,
                database=args.database,
                location=LOCATIONS[case_id],
                snapshot_id="oncology-snapshot-2026-09-13-v1",
            ).model_dump(mode="json")
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"cases": output}, indent=2) + "\n")
    if args.fixture_dir:
        args.fixture_dir.mkdir(parents=True, exist_ok=True)
        for case in output:
            (args.fixture_dir / f"{case['case_id']}.json").write_text(
                json.dumps(case, indent=2) + "\n"
            )
    print(
        json.dumps(
            {
                "cases": len(output),
                "trials": sum(len(case["trials"]) for case in output),
                "plottable": sum(
                    t["plot_position"]["plot_status"] == "plottable"
                    for case in output
                    for t in case["trials"]
                ),
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
