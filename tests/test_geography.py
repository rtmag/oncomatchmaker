"""Geographic ranking must never treat a closed site as recruiting."""
import json
from pathlib import Path
import sqlite3
import unittest

from trials.geography import PatientLocation, StaticCityResolver, haversine_km, nearest_recruiting_sites


ROOT = Path(__file__).resolve().parents[1]


def schema(db):
    db.executescript("""
        CREATE TABLE studies(
          nct_id TEXT PRIMARY KEY, title TEXT, overall_status TEXT,
          last_update_posted TEXT, retrieved_at TEXT, source_url TEXT);
        CREATE TABLE sites(
          nct_id TEXT, ordinal INTEGER, facility TEXT, status TEXT, city TEXT,
          region TEXT, country TEXT, latitude REAL, longitude REAL);
    """)


def add_study(db, nct_id, overall_status, sites):
    db.execute(
        "INSERT INTO studies VALUES (?,?,?,?,?,?)",
        (nct_id, "Synthetic " + nct_id, overall_status, "2026-09-01", "test-time",
         "https://clinicaltrials.gov/study/" + nct_id),
    )
    for ordinal, site in enumerate(sites):
        db.execute(
            "INSERT INTO sites VALUES (?,?,?,?,?,?,?,?,?)",
            (nct_id, ordinal, *site),
        )


class GeographyTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        schema(self.db)
        add_study(self.db, "NCT00000001", "RECRUITING", [
            ("Nearby closed", "ACTIVE_NOT_RECRUITING", "Sydney", "NSW", "Australia", -33.87, 151.21),
            ("Open Sydney", "RECRUITING", "Sydney", "NSW", "Australia", -33.89, 151.20),
            ("Open Sydney", "RECRUITING", "Sydney", "NSW", "Australia", -33.89, 151.20),
            ("Missing status", None, "Sydney", "NSW", "Australia", -33.88, 151.20),
        ])
        add_study(self.db, "NCT00000002", "NOT_YET_RECRUITING", [
            ("Study not open", "RECRUITING", "Sydney", "NSW", "Australia", -33.86, 151.20),
        ])
        add_study(self.db, "NCT00000003", "RECRUITING", [
            ("Open Canberra", "RECRUITING", "Canberra", "ACT", "Australia", -35.28, 149.13),
        ])

    def tearDown(self):
        self.db.close()

    def test_haversine_is_great_circle_distance(self):
        origin = PatientLocation("Zero", "Test", 0, 0)
        self.assertAlmostEqual(haversine_km(origin, 0, 1), 111.2, places=1)

    def test_only_open_study_and_open_site_survive(self):
        origin = PatientLocation("Sydney", "Australia", -33.8688, 151.2093)
        sites = nearest_recruiting_sites(self.db, origin)
        self.assertEqual([site.facility for site in sites], ["Open Sydney", "Open Canberra"])
        self.assertTrue(all(site.study_status == "RECRUITING" for site in sites))
        self.assertTrue(all(site.site_status == "RECRUITING" for site in sites))

    def test_filter_applies_after_molecular_candidate_selection(self):
        origin = PatientLocation("Sydney", "Australia", -33.8688, 151.2093)
        sites = nearest_recruiting_sites(self.db, origin, trial_ids=["NCT00000003"])
        self.assertEqual([site.nct_id for site in sites], ["NCT00000003"])
        self.assertEqual(nearest_recruiting_sites(self.db, origin, trial_ids=[]), [])

    def test_radius_and_limit_are_enforced(self):
        origin = PatientLocation("Sydney", "Australia", -33.8688, 151.2093)
        self.assertEqual(len(nearest_recruiting_sites(self.db, origin, limit=1)), 1)
        nearby = nearest_recruiting_sites(self.db, origin, max_distance_km=10)
        self.assertEqual([site.facility for site in nearby], ["Open Sydney"])

    def test_text_city_resolution_is_explicit_and_case_insensitive(self):
        cities = json.loads((ROOT / "evaluation/geography_test_cities.json").read_text())
        resolver = StaticCityResolver(cities)
        self.assertEqual(resolver.resolve("  sInGaPoRe ").country, "Singapore")
        with self.assertRaises(ValueError):
            resolver.resolve("Unconfigured City")


if __name__ == "__main__":
    unittest.main()
