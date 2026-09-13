"""Run offline city-to-recruiting-site proximity checks against a snapshot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from trials.geography import StaticCityResolver, nearest_recruiting_sites


ROOT = Path(__file__).resolve().parent


def load_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def run(database: Path, cities_path: Path, scenarios_path: Path, limit: int) -> dict:
    cities = load_json(cities_path)
    scenarios = load_json(scenarios_path)
    resolver = StaticCityResolver(cities)
    results = []
    with sqlite3.connect(database) as db:
        for scenario in scenarios:
            origin = resolver.resolve(scenario["city_input"])
            sites = nearest_recruiting_sites(
                db, origin, trial_ids=scenario["candidate_trial_ids"], limit=limit
            )
            results.append({
                "scenario": scenario["scenario"],
                "input": scenario["city_input"],
                "candidate_trial_ids": scenario["candidate_trial_ids"],
                "resolved_location": {
                    "city": origin.city, "country": origin.country,
                    "latitude": origin.latitude, "longitude": origin.longitude,
                },
                "distance_method": "great-circle distance in kilometers",
                "sites": [site.to_dict() for site in sites],
            })
    return {
        "scope": "Geography-only test over preselected molecular candidates",
        "status_rule": "study RECRUITING and site RECRUITING",
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--cities", type=Path, default=ROOT / "geography_test_cities.json")
    parser.add_argument("--scenarios", type=Path, default=ROOT / "geography_test_scenarios.json")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(run(args.database, args.cities, args.scenarios, args.limit), indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
