"""Run with: streamlit run app/main.py"""

import importlib
import json
import tempfile
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from schemas.molecular_profile import MolecularProfile
from trials.pipeline import match_patient
from ui.results import render_results

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="OncoMatchMaker", page_icon="🧬", layout="wide")
st.title("OncoMatchMaker")
st.write(
    "From molecular report to treatment evidence and clinical-trial opportunities."
)
st.caption(
    "Research POC for discussion with clinicians and trial teams. Trials are experimental; this tool does not determine treatment or eligibility."
)
mode = st.radio(
    "Start with",
    ["Synthetic demo profile", "Molecular profile JSON", "PDF report"],
    horizontal=True,
)
profile = None
if mode == "Synthetic demo profile":
    case = st.selectbox("Demo case", ["kras_nsclc", "egfr_nsclc", "negative"])
    profile = MolecularProfile.model_validate_json(
        (ROOT / "tests" / "fixtures" / f"{case}.json").read_text()
    )
    st.info(
        "Synthetic patient data. Trial search uses live ClinicalTrials.gov records."
    )
elif mode == "Molecular profile JSON":
    upload = st.file_uploader("Upload canonical profile", type=["json"])
    if upload:
        try:
            profile = MolecularProfile.model_validate_json(upload.getvalue())
        except ValidationError as exc:
            st.error(f"Invalid profile: {exc}")
else:
    try:
        parse_report = importlib.import_module("ingestion.pipeline").parse_report
    except (ModuleNotFoundError, AttributeError):
        st.info(
            "PDF extraction is awaiting Roberto’s ingestion.pipeline.parse_report integration. Use a profile JSON or demo meanwhile."
        )
    else:
        upload = st.file_uploader("Upload molecular report", type=["pdf"])
        if upload and st.button("Extract profile"):
            try:
                with (
                    st.spinner("Extracting report…"),
                    tempfile.TemporaryDirectory() as folder,
                ):
                    path = Path(folder) / "report.pdf"
                    path.write_bytes(upload.getvalue())
                    parsed = parse_report(str(path))
                    st.session_state["pdf_profile"] = MolecularProfile.model_validate(
                        parsed
                    ).model_dump()
                    st.session_state["pdf_bytes"] = upload.getvalue()
            except Exception as exc:
                st.error(f"Report extraction failed: {exc}")
        if (
            upload
            and st.session_state.get("pdf_bytes") == upload.getvalue()
            and "pdf_profile" in st.session_state
        ):
            profile = MolecularProfile.model_validate(st.session_state["pdf_profile"])

if profile:
    st.subheader("Review molecular profile")
    if profile.ingestion_provenance:
        audit = profile.ingestion_provenance
        st.caption(
            f"Extracted with {audit.get('model', 'configured model')} · gene names checked against HGNC"
        )
        for warning in audit.get("warnings", []):
            st.warning(warning)
        with st.expander("Extraction evidence and findings held for review"):
            st.json(audit)
        st.caption(
            "HGNC validates gene names, not whether a finding is pathogenic or clinically actionable."
        )
    # Keying by source prevents an edited previous case appearing for a new upload.
    import hashlib

    key = hashlib.sha256(profile.model_dump_json().encode()).hexdigest()
    st.write(
        f"Report: {profile.report.vendor or 'Unknown vendor'} · {profile.report.assay or 'Unknown assay'}"
    )
    st.write(
        "Reported findings",
        [v.model_dump(exclude_none=True) for v in profile.biomarkers.snv_indel],
    )
    st.write(
        f"MSI: {profile.biomarkers.msi.status or 'Unknown'} · TMB: {profile.biomarkers.tmb.value if profile.biomarkers.tmb.value is not None else 'Unknown'}"
    )
    diagnosis = st.text_input(
        "Diagnosis",
        profile.disease.normalized or profile.disease.raw_text,
        key=f"diagnosis_{key}",
    )
    location = profile.patient_context.location
    col1, col2 = st.columns(2)
    city = col1.text_input("City (optional)", location.city or "", key=f"city_{key}")
    country = col2.text_input(
        "Country (optional)", location.country or "", key=f"country_{key}"
    )
    latitude = col1.text_input(
        "Latitude (optional)",
        str(location.latitude) if location.latitude is not None else "",
        key=f"lat_{key}",
    )
    longitude = col2.text_input(
        "Longitude (optional)",
        str(location.longitude) if location.longitude is not None else "",
        key=f"lon_{key}",
    )
    age = col1.text_input(
        "Age in years (optional)",
        str(profile.patient_context.age)
        if profile.patient_context.age is not None
        else "",
        key=f"age_{key}",
    )
    ecog = col2.selectbox(
        "ECOG performance status",
        ["Unknown", "0", "1", "2", "3", "4", "5"],
        index=0
        if profile.patient_context.ecog is None
        else profile.patient_context.ecog + 1,
        key=f"ecog_{key}",
    )
    therapies = st.text_input(
        "Previous treatments (comma-separated, optional)",
        ", ".join(profile.patient_context.prior_therapies),
        key=f"therapy_{key}",
    )
    st.caption(
        "City/country alone will not calculate distance. Leave unrecorded clinical information blank."
    )
    with st.expander("Advanced molecular profile review"):
        edited = st.text_area(
            "Molecular profile JSON (diagnosis and context fields above take precedence)",
            json.dumps(profile.model_dump(), indent=2),
            height=320,
            key=f"profile_{key}",
        )
    confirmed = st.checkbox(
        "I reviewed the diagnosis, biomarkers and optional patient context",
        key=f"confirm_{key}",
    )
    fingerprint = hashlib.sha256(
        json.dumps(
            [
                edited,
                diagnosis,
                city,
                country,
                latitude,
                longitude,
                age,
                ecog,
                therapies,
            ]
        ).encode()
    ).hexdigest()
    if st.button("Find evidence and trials", disabled=not confirmed):
        try:
            values = json.loads(edited)
            values["disease"]["normalized"] = diagnosis.strip()
            values.setdefault("patient_context", {}).update(
                age=int(age) if age.strip() else None,
                ecog=None if ecog == "Unknown" else int(ecog),
                prior_therapies=[t.strip() for t in therapies.split(",") if t.strip()],
                location=dict(
                    city=city or None,
                    country=country or None,
                    latitude=float(latitude) if latitude.strip() else None,
                    longitude=float(longitude) if longitude.strip() else None,
                ),
            )
            reviewed = MolecularProfile.model_validate(values)
            with st.spinner("Searching trials and evaluating available information…"):
                results = match_patient(reviewed)
            st.session_state["results"] = results
            st.session_state["results_key"] = (key, fingerprint)
        except (ValueError, TypeError, KeyError) as exc:
            st.error(f"Please correct the profile: {exc}")
    if st.session_state.get("results_key") == (key, fingerprint):
        render_results(st.session_state["results"])
