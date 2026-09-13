"""Build a location-free model packet from profiles and a CTGov snapshot."""

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPIKE = ROOT / "matching_spike"


def load_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def build_packet(database, profiles_path, candidate_sets_path):
    profiles = load_json(profiles_path)
    candidate_sets = load_json(candidate_sets_path)
    cases = []
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        for profile in profiles["cases"]:
            identifiers = candidate_sets[profile["case_id"]]
            trials = []
            for nct_id in identifiers:
                row = db.execute(
                    """SELECT nct_id, title, overall_status, study_type,
                              primary_purpose, eligibility_text, conditions_json,
                              last_update_posted, status_verified, retrieved_at,
                              source_url
                       FROM studies WHERE nct_id=?""",
                    (nct_id,),
                ).fetchone()
                if row is None:
                    raise RuntimeError("Trial missing from snapshot: " + nct_id)
                trial = dict(row)
                trial["conditions"] = json.loads(trial.pop("conditions_json"))
                trials.append(trial)
            cases.append({"profile": profile, "trials": trials})
    return {
        "purpose": "Molecular and disease trial prescreening; location excluded",
        "instructions": (SPIKE / "model_instructions.md").read_text(encoding="utf-8"),
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--profiles", type=Path, default=SPIKE / "profiles.json")
    parser.add_argument(
        "--candidate-sets", type=Path, default=SPIKE / "candidate_sets.json"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    packet = build_packet(args.database, args.profiles, args.candidate_sets)
    rendered = json.dumps(packet, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
