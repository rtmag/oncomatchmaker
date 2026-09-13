import sqlite3

from trials.candidate_retrieval import retrieve_candidates, screen_trials


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

    profile["biomarkers"] = {"snv_indel": [], "copy_number": [], "fusions": []}
    assert [row.nct_id for row in retrieve_candidates(db, profile)] == ["NCT00000001"]
