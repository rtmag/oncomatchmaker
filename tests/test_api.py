from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from test_matching import FakeClient

from app.api import app
from ingestion.model_client import ExtractionError
from trials.pipeline import match_patient

client = TestClient(app)
PDF_BYTES = b"%PDF-1.4 synthetic"


def upload(content):
    return client.post(
        "/api/extract", files={"file": ("report.pdf", content, "application/pdf")}
    )


def test_demo_cases_are_listed_and_loadable():
    cases = client.get("/api/demo-cases").json()
    assert {case["id"] for case in cases} == {
        "astra_egfr_met",
        "kras_nsclc",
        "egfr_nsclc",
        "negative",
    }
    astra = next(case for case in cases if case["id"] == "astra_egfr_met")
    assert astra["label"] == "EGFR L858R, ATM, DNMT3A R882H, MET amplification"
    kras = next(case for case in cases if case["id"] == "kras_nsclc")
    assert kras["label"] == "KRAS G12C"
    profile = client.get("/api/demo-cases/kras_nsclc").json()
    assert profile["biomarkers"]["snv_indel"][0]["gene"] == "KRAS"


def test_unknown_demo_case_is_rejected():
    assert client.get("/api/demo-cases/conftest").status_code == 404


def test_validate_rejects_unexpected_fields():
    response = client.post(
        "/api/profile/validate",
        json={"disease": {"raw_text": "NSCLC"}, "unexpected": True},
    )
    assert response.status_code == 422


def test_match_returns_ranked_results(profile, record):
    expected = match_patient(profile, client=FakeClient([record]))
    with patch("trials.pipeline.match_patient", return_value=expected) as run:
        response = client.post("/api/match", json=profile.model_dump(mode="json"))
    assert response.status_code == 200
    run.assert_called_once()
    assert response.json()["trials"][0]["trial"]["nct_id"] == "NCT00000001"


def test_extract_rejects_non_pdf_content():
    assert upload(b"not a pdf").status_code == 415


def test_extract_rejects_oversized_upload():
    with patch("app.api.MAX_PDF_BYTES", 8):
        assert upload(PDF_BYTES).status_code == 413


def test_extract_returns_profile_for_review(profile):
    ingested = SimpleNamespace(profile=profile.model_dump())
    with patch("ingestion.pipeline.ingest_report", return_value=ingested):
        response = upload(PDF_BYTES)
    assert response.status_code == 200
    assert response.json()["disease"]["normalized"] == "non-small cell lung cancer"


def test_extract_reports_extraction_failure():
    failure = ExtractionError("Report has unreadable pages")
    with patch("ingestion.pipeline.ingest_report", side_effect=failure):
        response = upload(PDF_BYTES)
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Report extraction failed safely; no profile was accepted."
    )
