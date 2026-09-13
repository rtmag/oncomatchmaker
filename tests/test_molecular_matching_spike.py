"""Tests for the location-free matching-spike packet."""

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "matching_spike", ROOT / "evaluation/run_molecular_matching_spike.py"
)
matching_spike = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matching_spike)


class MatchingSpikeTests(unittest.TestCase):
    def test_packet_uses_selected_trials_and_excludes_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            database = base / "snapshot.sqlite"
            with sqlite3.connect(database) as db:
                db.execute(
                    """CREATE TABLE studies(
                    nct_id TEXT PRIMARY KEY, title TEXT, overall_status TEXT,
                    study_type TEXT, primary_purpose TEXT, eligibility_text TEXT,
                    conditions_json TEXT, last_update_posted TEXT,
                    status_verified TEXT, retrieved_at TEXT, source_url TEXT)"""
                )
                db.execute(
                    "INSERT INTO studies VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        "NCT00000001",
                        "Synthetic",
                        "RECRUITING",
                        "INTERVENTIONAL",
                        "TREATMENT",
                        "Requires EGFR L858R",
                        '["NSCLC"]',
                        "2026-01-01",
                        "2026-01",
                        "test-time",
                        "https://example.test/NCT00000001",
                    ),
                )
            profiles = base / "profiles.json"
            candidates = base / "candidates.json"
            profiles.write_text(json.dumps({"cases": [{"case_id": "one"}]}))
            candidates.write_text(json.dumps({"one": ["NCT00000001"]}))
            packet = matching_spike.build_packet(database, profiles, candidates)
            trial = packet["cases"][0]["trials"][0]
            self.assertEqual(trial["nct_id"], "NCT00000001")
            self.assertFalse({"sites", "locations", "facility"} & set(trial))

    def test_every_profile_has_positive_and_negative_pressure_tests(self):
        candidates = matching_spike.load_json(
            matching_spike.SPIKE / "candidate_sets.json"
        )
        self.assertTrue(
            all(len(identifiers) >= 3 for identifiers in candidates.values())
        )
        self.assertEqual(len(candidates), 4)

    def test_assessment_covers_each_pair_once_and_preserves_safety_controls(self):
        candidates = matching_spike.load_json(
            matching_spike.SPIKE / "candidate_sets.json"
        )
        results = matching_spike.load_json(
            matching_spike.SPIKE / "chatgpt_assessments.json"
        )
        assessed = [(row["case_id"], row["nct_id"]) for row in results["assessments"]]
        expected = [
            (case_id, nct_id) for case_id, ids in candidates.items() for nct_id in ids
        ]
        self.assertCountEqual(assessed, expected)
        self.assertEqual(len(assessed), len(set(assessed)))
        classes = {row["nct_id"]: row["match_class"] for row in results["assessments"]}
        self.assertEqual(classes["NCT07291037"], "conflict")
        self.assertEqual(classes["NCT06119581"], "conflict")
        self.assertEqual(classes["NCT07446322"], "conflict")
        self.assertEqual(classes["NCT05806515"], "insufficient_biomarker_evidence")


if __name__ == "__main__":
    unittest.main()
