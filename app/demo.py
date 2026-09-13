"""Cached-first hackathon demo. Run: streamlit run app/demo.py"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import streamlit as st

from ingestion.model_client import ExtractionError
from ingestion.pipeline import parse_report
from schemas.integrated_results import IntegratedCaseResult
from trials.astra_runner import AstraExpertRunner, ExpertTeamError
from trials.integrated_pipeline import _trial

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evaluation" / "demo_fixtures"
DATABASE = ROOT / "data" / "snapshots" / "2026-09-13-v1" / "oncology.sqlite"
DISPLAY_NAMES = {
    "fmi-lung-egfr-l858r": "EGFR L858R lung - Singapore",
    "fmi-nsclc-met-exon14": "MET exon 14 NSCLC - New York",
    "fmi-prostate-brca2-loss": "BRCA2-loss prostate - Sydney",
    "tempus-metastatic-colon-msih": "MSI-high colon - Paris",
}


def load_cases():
    cases = {}
    for path in FIXTURES.glob("*.json"):
        if path.name == "negative-report-safety.json":
            continue
        case = IntegratedCaseResult.model_validate_json(path.read_text())
        cases[case.case_id] = case
    return cases


def render_plot(case):
    points = [
        {
            "trial": trial.nct_id,
            "clinical": trial.plot_position.clinical_x,
            "geography": trial.plot_position.geography_y,
            "quadrant": trial.plot_position.quadrant,
        }
        for trial in case.trials
        if trial.plot_position.plot_status == "plottable"
    ]
    if not points:
        st.info(
            "No trials have both a rankable clinical score and confirmed open-site distance."
        )
        return
    st.vega_lite_chart(
        {"values": points},
        {
            "mark": {"type": "circle", "size": 180, "tooltip": True},
            "encoding": {
                "x": {
                    "field": "clinical",
                    "type": "quantitative",
                    "scale": {"domain": [0, 100]},
                    "title": "Clinical match",
                },
                "y": {
                    "field": "geography",
                    "type": "quantitative",
                    "scale": {"domain": [0, 100]},
                    "title": "Geographic access",
                },
                "color": {"field": "quadrant", "type": "nominal"},
                "tooltip": ["trial", "clinical", "geography", "quadrant"],
            },
        },
        use_container_width=True,
    )


def render_case(case):
    st.success("PRECOMPUTED PUBLIC-SAMPLE RESULT - presentation-safe fallback")
    st.subheader("Molecular profile")
    st.write(case.molecular_profile["disease"]["raw_text"])
    st.write(" · ".join(case.molecular_biology_summary))
    st.caption(
        f"{case.source_report.filename} · reader {case.source_report.reader_version} · snapshot {case.snapshot_id}"
    )

    st.subheader("Approved therapies")
    st.info(
        "Not included in this cached trial-matching demo. Approved therapies remain intentionally separate from experimental trials."
    )

    st.subheader("Clinical match vs geographic access")
    st.caption("Independent axes: geography never changes the clinical composite.")
    render_plot(case)

    st.subheader("ASTRA expert team")
    top_trial = next(
        (trial for trial in case.trials if trial.consensus.disposition == "candidate"),
        case.trials[0],
    )
    live_key = f"live_astra_{case.case_id}_{top_trial.nct_id}"
    if os.environ.get("OPENAI_API_KEY"):
        if st.button(f"Run six ASTRA experts live for {top_trial.nct_id}"):
            try:
                with st.spinner(
                    "Running six isolated GPT-6 Astra experts concurrently..."
                ):
                    with sqlite3.connect(DATABASE) as db:
                        record = _trial(db, top_trial.nct_id)
                    runner = AstraExpertRunner()
                    try:
                        st.session_state[live_key] = runner.run_team(
                            case.molecular_profile, record, []
                        )
                    finally:
                        runner.close()
                st.success("Six independent live ASTRA assessments completed.")
            except ExpertTeamError:
                st.error(
                    "An ASTRA expert failed validation. No partial team result was accepted."
                )
    else:
        st.caption(
            "Live ASTRA disabled until OPENAI_API_KEY is configured server-side."
        )
    live_team = st.session_state.get(live_key)
    team = live_team["assessments"] if live_team else top_trial.expert_assessments
    if not live_team and not all(expert.execution for expert in team):
        st.warning(
            "Cached expert rows are legacy integration placeholders, not genuine independent ASTRA calls. Regenerate fixtures before presenting them as multi-agent output."
        )
    columns = st.columns(3)
    for index, expert in enumerate(team):
        value = expert if isinstance(expert, dict) else expert.model_dump()
        with columns[index % 3].container(border=True):
            st.markdown(f"**{value['expert_role'].replace('_', ' ').title()}**")
            st.write(value["assessment"].upper())
            st.caption(value["reasoning_summary"])
            execution = value.get("execution")
            if execution:
                st.caption(
                    f"{execution['model']} · {execution['reasoning_effort']} · {execution['status']} · {execution['latency_ms']} ms"
                )

    st.subheader("Experimental clinical trials")
    for trial in case.trials:
        conflict = trial.consensus.disposition == "conflict"
        title = f"{trial.nct_id} · {trial.title}"
        with st.expander(title, expanded=not conflict):
            if conflict:
                st.error("Molecular/disease conflict - unrankable")
            left, right = st.columns(2)
            left.metric(
                "Clinical composite",
                trial.clinical_score.composite_score
                if trial.clinical_score.composite_score is not None
                else "Unrankable",
            )
            right.metric(
                "Geographic access",
                trial.geography_score.score
                if trial.geography_score.score is not None
                else "Unavailable",
            )
            st.caption(
                f"Clinical evidence coverage: {trial.clinical_score.coverage:.0%}"
            )
            st.bar_chart(
                {
                    dimension.dimension: dimension.value or 0
                    for dimension in trial.clinical_score.dimensions
                }
            )
            st.write(trial.rationale)
            if trial.nearest_open_site and not conflict:
                site = trial.nearest_open_site
                st.write(
                    f"Nearest explicitly recruiting site: {site.facility}, {site.city}, {site.country} - {site.distance_km:.1f} km great-circle distance"
                )
                st.caption(f"Study: {site.study_status} · Site: {site.site_status}")
            elif not conflict:
                st.warning(
                    "No explicitly recruiting site with calculable distance in this snapshot."
                )
            if trial.missing_information:
                st.markdown("**Missing eligibility information**")
                for item in trial.missing_information:
                    st.write("- " + item)
            if trial.discussion_questions:
                st.markdown("**Questions for the oncologist or trial coordinator**")
                for question in trial.discussion_questions:
                    st.write("- " + question)
            st.link_button("ClinicalTrials.gov source", trial.source_url)
            st.caption(
                f"Registry updated {trial.registry_last_update} · Eligibility not determined"
            )
    st.warning(case.disclaimer)


def render_negative():
    result = json.loads((FIXTURES / "negative-report-safety.json").read_text())
    st.success("PRECOMPUTED PUBLIC-SAMPLE SAFETY RESULT")
    st.subheader("No reportable pathogenic molecular target extracted")
    for message in result["messages"]:
        st.write("- " + message)
    st.info("Complete trial matching: not yet evaluated")
    st.warning(result["disclaimer"])


def render_live_extraction():
    st.warning("LIVE EXTRACTION - optional; cached demo remains available")
    if not os.environ.get("OPENAI_API_KEY"):
        st.error(
            "Live extraction is disabled. Configure OPENAI_API_KEY in the server secret manager; never place it in frontend code."
        )
        return
    upload = st.file_uploader("Upload a molecular oncology PDF", type=["pdf"])
    if upload and st.button("Run live extraction"):
        try:
            with (
                tempfile.TemporaryDirectory() as folder,
                st.spinner(
                    "Extracting with fast reader and structured model output..."
                ),
            ):
                path = Path(folder) / "report.pdf"
                path.write_bytes(upload.getvalue())
                profile = parse_report(path, reader_mode="fast")
            st.success(
                "Live extraction completed. Trial matching remains on the cached demo path."
            )
            st.json(profile.model_dump(mode="json"))
        except (ExtractionError, ValueError, OSError):
            st.error(
                "Extraction failed safely. No profile was accepted; report details and provider errors were not exposed."
            )


st.set_page_config(page_title="OncoMatchmaker", page_icon="🧬", layout="wide")
st.title("OncoMatchmaker")
st.markdown("**From molecular report to matched therapies and clinical trials.**")
mode = st.sidebar.radio("Demo mode", ["Cached results", "Optional live extraction"])
if mode == "Optional live extraction":
    render_live_extraction()
else:
    cases = load_cases()
    options = [*DISPLAY_NAMES, "negative-report-safety"]
    selected = st.sidebar.selectbox(
        "Public sample",
        options,
        format_func=lambda value: DISPLAY_NAMES.get(
            value, "Negative report safety case"
        ),
    )
    if selected == "negative-report-safety":
        render_negative()
    else:
        render_case(cases[selected])
