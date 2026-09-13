"""HTTP API for the web workspace. Run with: uvicorn app.api:app --reload"""

import tempfile
import hashlib
import os
import sqlite3
import time
from collections import OrderedDict
from threading import Lock
from functools import lru_cache
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ingestion import pipeline as ingestion_pipeline
from ingestion.model_client import ExtractionError
from ingestion.pdf_reader import PDFReadError
from schemas.match_results import MatchResults
from schemas.molecular_profile import MolecularProfile
from trials import pipeline as trial_pipeline
from trials.astra_runner import ExpertTeamError

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
WEB_DIST = ROOT / "web" / "dist"
DEMO_CASE_IDS = ("astra_egfr_met", "kras_nsclc", "egfr_nsclc", "negative")
MAX_PDF_BYTES = 20 * 1024 * 1024
PDF_MAGIC = b"%PDF"

app = FastAPI(title="OncoMatchMaker API", version="0.1.0")
_extraction_cache = OrderedDict()
_cache_lock = Lock()


@lru_cache(maxsize=1)
def _city_directory():
    with sqlite3.connect(trial_pipeline.SNAPSHOT) as db:
        rows = [dict(city=city.strip(), country=country.strip(), latitude=lat, longitude=lon,
                     region=region)
                for city, region, country, lat, lon in db.execute("""
                    SELECT city,region,country,AVG(latitude),AVG(longitude) FROM sites
                    WHERE city IS NOT NULL AND country IS NOT NULL
                    AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180
                    GROUP BY city,region,country ORDER BY city,country
                """)]
    # Vendors sometimes put street addresses in region. Collapse identical city
    # coordinates before suggesting places, retaining geographically distinct names.
    places = {}
    for row in rows:
        key = (row["city"].casefold(), row["country"].casefold(), round(row["latitude"], 1), round(row["longitude"], 1))
        if key not in places or len(row["region"] or "") < len(places[key]["region"] or ""):
            places[key] = row
    options = []
    for row in places.values():
        region = row.pop("region")
        parts = [row["city"]]
        if region and region.casefold() not in {row["city"].casefold(), row["country"].casefold()}:
            parts.append(region)
        parts.append(row["country"])
        options.append({**row, "label": ", ".join(parts)})
    return options


@app.get("/api/cities")
def cities(q: str = Query(min_length=2, max_length=120)):
    query = q.strip().casefold()
    rows = [row for row in _city_directory() if query in row["label"].casefold()]
    return sorted(rows, key=lambda row: (row["city"].casefold() != query,
                  not row["city"].casefold().startswith(query), row["label"]))[:20]


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
    try:
        return trial_pipeline.match_patient(profile)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ExpertTeamError as exc:
        raise HTTPException(
            502, "The complete ASTRA expert team did not return a validated result."
        ) from exc


@app.post("/api/extract", response_model=MolecularProfile)
def extract(file: UploadFile = File(...)):
    data = file.file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "PDF exceeds the 20 MB limit.")
    if not data.startswith(PDF_MAGIC):
        raise HTTPException(415, "Upload a PDF molecular report.")
    key = (hashlib.sha256(data).hexdigest(), os.environ.get("ONCOMATCH_EXTRACTION_MODEL", "gpt-5.6-sol"), "fast-v1")
    with _cache_lock:
        cached = _extraction_cache.get(key)
        if cached and time.monotonic() - cached[0] < 3600:
            profile = cached[1].model_copy(deep=True)
            profile.ingestion_provenance["cache_hit"] = True
            return profile
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "report.pdf"
        path.write_bytes(data)
        try:
            # The interactive demo uses one low-reasoning Sol pass, followed by
            # deterministic source/HGNC checks. The returned profile is explicitly
            # marked for human confirmation before trial matching.
            result = ingestion_pipeline.ingest_report(path, extraction_mode="fast")
        except (ExtractionError, PDFReadError) as exc:
            raise HTTPException(
                422, "Report extraction failed safely; no profile was accepted."
            ) from exc
    profile = MolecularProfile.model_validate(result.profile)
    profile.ingestion_provenance = profile.ingestion_provenance or {}
    profile.ingestion_provenance["cache_hit"] = False
    with _cache_lock:
        _extraction_cache[key] = (time.monotonic(), profile.model_copy(deep=True))
        while len(_extraction_cache) > 16:
            _extraction_cache.popitem(last=False)
    return profile


# Mounted last so /api routes take precedence; serves the built React workspace.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
