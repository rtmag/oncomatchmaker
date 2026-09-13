"""Synthetic registry records test site status boundaries and lossless storage."""

import importlib.util
import json
import sqlite3
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "builder",
    Path(__file__).resolve().parents[1] / "evaluation/build_trial_snapshot.py",
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class SnapshotTests(unittest.TestCase):
    def test_site_status_never_inherits_overall_status(self):
        for overall in ("RECRUITING", "NOT_YET_RECRUITING", "SUSPENDED", "COMPLETED"):
            with self.subTest(overall=overall), sqlite3.connect(":memory:") as db:
                db.executescript(builder.SCHEMA)
                sites = [
                    {
                        "facility": "US open",
                        "country": "United States",
                        "status": "RECRUITING",
                    },
                    {
                        "facility": "Australia closed",
                        "country": "Australia",
                        "status": "ACTIVE_NOT_RECRUITING",
                    },
                    {"facility": "Australia unknown", "country": "Australia"},
                    {
                        "facility": "Australia upcoming",
                        "country": "Australia",
                        "status": "NOT_YET_RECRUITING",
                    },
                ]
                record = {
                    "protocolSection": {
                        "identificationModule": {"nctId": "NCT00000000"},
                        "statusModule": {"overallStatus": overall},
                        "contactsLocationsModule": {"locations": sites},
                    },
                    "futureField": {"preserve": True},
                }
                builder.insert_study(db, record, "test-timestamp")
                names = [
                    r[0] for r in db.execute("SELECT facility FROM recruiting_sites")
                ]
                self.assertEqual(names, ["US open"] if overall == "RECRUITING" else [])
                self.assertEqual(
                    db.execute("SELECT count(*) FROM sites").fetchone()[0], 4
                )
                self.assertEqual(
                    json.loads(
                        db.execute("SELECT raw_json FROM studies").fetchone()[0]
                    ),
                    record,
                )
                self.assertIsNone(
                    db.execute("SELECT status FROM sites WHERE ordinal=2").fetchone()[0]
                )

    def test_all_locations_survive(self):
        with sqlite3.connect(":memory:") as db:
            db.executescript(builder.SCHEMA)
            locations = [
                {
                    "facility": str(i),
                    "status": "RECRUITING",
                    "contacts": [{"name": "Synthetic"}],
                }
                for i in range(418)
            ]
            record = {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT00000001"},
                    "statusModule": {"overallStatus": "RECRUITING"},
                    "contactsLocationsModule": {"locations": locations},
                }
            }
            builder.insert_study(db, record, "test-timestamp")
            self.assertEqual(
                db.execute("SELECT count(*) FROM recruiting_sites").fetchone()[0], 418
            )
            self.assertEqual(
                [
                    json.loads(r[0])
                    for r in db.execute("SELECT raw_json FROM sites ORDER BY ordinal")
                ],
                locations,
            )


if __name__ == "__main__":
    unittest.main()
