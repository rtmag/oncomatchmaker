"""CLI: python -m app.match tests/fixtures/kras_nsclc.json"""

import argparse
from pathlib import Path

from schemas.molecular_profile import MolecularProfile
from trials.pipeline import match_patient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    profile = MolecularProfile.model_validate_json(args.profile.read_text())
    results = match_patient(profile)
    print(results.model_dump_json(indent=2))
    return 1 if results.search_status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
