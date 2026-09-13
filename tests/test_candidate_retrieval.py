import sqlite3

from schemas.molecular_profile import Location
from trials.candidate_retrieval import retrieve_candidates, screen_trials
from trials.pipeline import attach_screening_geography


def test_landscape_uses_only_open_studies_and_open_sites():
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE studies(nct_id TEXT, overall_status TEXT);
        CREATE TABLE sites(nct_id TEXT,status TEXT,latitude REAL,longitude REAL);
        INSERT INTO studies VALUES ('A','RECRUITING'),('B','NOT_YET_RECRUITING'),('C','RECRUITING');
        INSERT INTO sites VALUES ('A','ACTIVE_NOT_RECRUITING',0,0),('A','RECRUITING',0,1),
        ('B','RECRUITING',0,0),('C','UNKNOWN',0,0),('C','RECRUITING',NULL,NULL);
    """)
    points = [dict(nct_id=n, distance_km=None, geography_score=None) for n in "ABC"]
    attach_screening_geography(db, points, Location(latitude=0, longitude=0))
    assert 111 < points[0]["distance_km"] < 112
    assert 0 < points[0]["geography_score"] < 100
    assert all(
        row["distance_km"] is None and row["geography_score"] is None
        for row in points[1:]
    )


def test_retrieval_requires_disease_and_molecular_hit():
    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE studies(nct_id TEXT,title TEXT,eligibility_text TEXT,conditions_json TEXT,overall_status TEXT)"
    )
    db.executemany(
        "INSERT INTO studies VALUES(?,?,?,?,?)",
        [
            ("NCT00000001", "EGFR study", "Requires L858R", '["NSCLC"]', "RECRUITING"),
            (
                "NCT00000002",
                "EGFR study",
                "Requires L858R",
                '["Melanoma"]',
                "RECRUITING",
            ),
            ("NCT00000003", "EGFR study", "Requires L858R", '["NSCLC"]', "COMPLETED"),
        ],
    )
    profile = {
        "disease": {"raw_text": "NSCLC", "normalized": "NSCLC", "synonyms": []},
        "biomarkers": {"snv_indel": [{"gene": "EGFR", "protein_change": "L858R"}]},
    }
    assert [row.nct_id for row in retrieve_candidates(db, profile)] == ["NCT00000001"]
    screened = screen_trials(db, profile)
    assert screened.total_screened == 3
    assert screened.status_eligible == 2
    assert len(screened.candidates) == 1
    assert screened.candidates[0].preliminary_score > 0
    assert len(screened.landscape) == 3
    assert len({row["nct_id"] for row in screened.landscape}) == 3
    assert (
        screened.landscape[0]["preliminary_score"]
        == screened.candidates[0].preliminary_score
    )
    assert screened.landscape[1]["screening_state"] == "disease_not_retrieved"
    assert screened.landscape[2]["preliminary_score"] == 0
    assert all(row["geography_score"] is None for row in screened.landscape)

    profile["biomarkers"] = {"snv_indel": [], "copy_number": [], "fusions": []}
    assert [row.nct_id for row in retrieve_candidates(db, profile)] == ["NCT00000001"]
