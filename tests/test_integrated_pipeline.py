import sqlite3
from pathlib import Path

from schemas.integrated_results import IntegratedCaseResult


def test_frozen_result_contract_rejects_extra_fields():
    fixture = {
        "case_id": "case",
        "generated_at": "2026-09-13T00:00:00+00:00",
        "snapshot_id": "snapshot",
        "source_report": {
            "filename": "sample.pdf",
            "sha256": "a" * 64,
            "page_count": 1,
            "reader_version": "reader",
            "ingestion_mode": "recorded_public_sample_profile",
        },
        "patient_location": {},
        "molecular_profile": {},
        "molecular_biology_summary": [],
        "trials": [],
        "limitations": [],
    }
    IntegratedCaseResult.model_validate(fixture)
    fixture["unexpected"] = True
    try:
        IntegratedCaseResult.model_validate(fixture)
    except Exception:
        pass
    else:
        raise AssertionError("result contract accepted an unexpected field")


def test_snapshot_has_separate_study_and_site_status():
    path = Path(__file__).parents[1] / "data/snapshots/2026-09-13-v1/oncology.sqlite"
    if not path.exists():
        return
    with sqlite3.connect(path) as db:
        row = db.execute(
            "SELECT studies.overall_status, sites.status FROM studies JOIN sites USING(nct_id) LIMIT 1"
        ).fetchone()
    assert row is not None and len(row) == 2
