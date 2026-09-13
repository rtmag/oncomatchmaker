"""HTTP API for the web workspace. Run with: uvicorn app.api:app --reload"""

import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ingestion import pipeline as ingestion_pipeline
from ingestion.model_client import ExtractionError
from ingestion.pdf_reader import PDFReadError
from schemas.match_results import MatchResults
from schemas.molecular_profile import MolecularProfile
from trials import pipeline as trial_pipeline

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
WEB_DIST = ROOT / "web" / "dist"
DEMO_CASE_IDS = ("astra_egfr_met", "kras_nsclc", "egfr_nsclc", "negative")
MAX_PDF_BYTES = 20 * 1024 * 1024
PDF_MAGIC = b"%PDF"

app = FastAPI(title="OncoMatchMaker API", version="0.1.0")


class DemoCase(BaseModel):
    id: str
    label: str
    description: str


def _load_case(case_id):
    if case_id not in DEMO_CASE_IDS:
        raise HTTPException(404, f"Unknown demo case: {case_id}")
    return MolecularProfile.model_validate_json(
        (FIXTURES / f"{case_id}.json").read_text()
    )


def _describe_case(case_id):
    profile = _load_case(case_id)
    markers = profile.biomarkers
    findings = (
        [" ".join(filter(None, [v.gene, v.protein_change])) for v in markers.snv_indel]
        + [f"{c.gene} {c.alteration}" for c in markers.copy_number]
        + [f"{f.gene} fusion" for f in markers.fusions]
    )
    return DemoCase(
        id=case_id,
        label=", ".join(findings) or "No reported alterations",
        description=profile.disease.normalized or profile.disease.raw_text,
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/demo-cases", response_model=List[DemoCase])
def demo_cases():
    return [_describe_case(case_id) for case_id in DEMO_CASE_IDS]


@app.get("/api/demo-cases/{case_id}", response_model=MolecularProfile)
def demo_case(case_id: str):
    return _load_case(case_id)


@app.post("/api/profile/validate", response_model=MolecularProfile)
def validate_profile(profile: MolecularProfile):
    # FastAPI rejects schema violations with 422 before this body runs.
    return profile


@app.post("/api/match", response_model=MatchResults)
def match(profile: MolecularProfile):
    return trial_pipeline.match_patient(profile)


@app.post("/api/extract", response_model=MolecularProfile)
def extract(file: UploadFile = File(...)):
    data = file.file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "PDF exceeds the 20 MB limit.")
    if not data.startswith(PDF_MAGIC):
        raise HTTPException(415, "Upload a PDF molecular report.")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "report.pdf"
        path.write_bytes(data)
        try:
            result = ingestion_pipeline.ingest_report(path)
        except (ExtractionError, PDFReadError) as exc:
            raise HTTPException(422, f"Report extraction failed: {exc}") from exc
    return MolecularProfile.model_validate(result.profile)


# Mounted last so /api routes take precedence; serves the built React workspace.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
