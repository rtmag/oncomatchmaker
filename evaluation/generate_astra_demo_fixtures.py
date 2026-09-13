"""Replace legacy fixture assessments with genuine six-agent ASTRA API output."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from schemas.integrated_results import IntegratedCaseResult
from trials.astra_runner import AstraExpertRunner
from trials.integrated_pipeline import _trial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("fixture_dir", type=Path)
    args = parser.parse_args()
    paths = sorted(
        path
        for path in args.fixture_dir.glob("*.json")
        if path.name != "negative-report-safety.json"
    )
    runner = AstraExpertRunner()
    try:
        with sqlite3.connect(args.database) as db:
            for path in paths:
                case = IntegratedCaseResult.model_validate_json(path.read_text())
                payload = case.model_dump(mode="json")
                for trial_result in payload["trials"]:
                    record = _trial(db, trial_result["nct_id"])
                    team = runner.run_team(payload["molecular_profile"], record, [])
                    for assessment in team["assessments"]:
                        assessment["execution"]["status"] = "precomputed"
                    trial_result["expert_assessments"] = team["assessments"]
                    trial_result["consensus"] = team["consensus"]
                validated = IntegratedCaseResult.model_validate(payload)
                path.write_text(validated.model_dump_json(indent=2) + "\n")
                print(f"wrote {path.name}", flush=True)
    finally:
        runner.close()


if __name__ == "__main__":
    main()
