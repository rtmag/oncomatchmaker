"""Integration POC: report profile -> ASTRA consensus -> scores -> open sites."""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ingestion.pdf_reader import read_document
from schemas.astra_contracts import EXPERT_ROLES, validate_molecular_profile
from schemas.integrated_results import (
    IntegratedCaseResult,
    OpenSite,
    SourceReport,
    TrialResult,
)
from schemas.trial_scorecard import CLINICAL_DIMENSIONS, DimensionScore
from trials.astra_team import build_expert_packets, reach_consensus
from trials.candidate_retrieval import retrieve_candidates
from trials.geography import PatientLocation, nearest_recruiting_sites
from trials.scorecard import (
    clinical_trial_score,
    geographic_access_score,
    trial_plot_position,
)


def _trial(db: sqlite3.Connection, nct_id: str) -> dict[str, Any]:
    db.row_factory = sqlite3.Row
    row = db.execute(
        """SELECT nct_id,title,overall_status,study_type,primary_purpose,
                  eligibility_text,conditions_json,last_update_posted,
                  status_verified,retrieved_at,source_url,raw_json
           FROM studies WHERE nct_id=?""",
        (nct_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Trial absent from snapshot: {nct_id}")
    value = dict(row)
    value["conditions"] = json.loads(value.pop("conditions_json"))
    return value


def _recorded_experts(review: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Adapt the prior model-reviewed spike into the six frozen expert contracts.

    This adapter is deliberately labelled recorded. It validates integration and
    safety gates without pretending that six fresh model calls occurred.
    """
    conflict = review["match_class"] == "conflict"
    uncertain = review["match_class"] == "insufficient_biomarker_evidence"
    relationships = (
        ["direct_variant"] if review["molecular_fit"] == "exact" else ["gene_level"]
    )
    if uncertain:
        relationships = ["gene_level"]
    rows = []
    for role in EXPERT_ROLES:
        decision = "support"
        conflicts: list[str] = []
        if conflict and role in {
            "molecular_profile_qc",
            "disease_oncology",
            "trial_eligibility",
            "safety_critic",
        }:
            decision = "conflict"
            conflicts = [review["rationale"]]
        elif uncertain and role in {"molecular_profile_qc", "trial_eligibility"}:
            decision = "unknown"
        elif uncertain or review["unknown_or_required_review"]:
            decision = "caution"
        rows.append(
            {
                "trial_id": review["nct_id"],
                "expert_role": role,
                "assessment": decision,
                "confidence": 0.75,
                "relationships": relationships,
                "supporting_facts": [] if conflict else [review["rationale"]],
                "conflicting_facts": conflicts,
                "missing_information": list(review["unknown_or_required_review"]),
                "evidence_references": [review["source_url"]],
                "reasoning_summary": review["rationale"],
            }
        )
    return rows


def _dimensions(review: Mapping[str, Any]) -> list[DimensionScore]:
    if review["match_class"] == "conflict":
        return [
            DimensionScore(name, None, "conflict", 0.9, (review["rationale"],))
            if name in {"molecular_fit", "disease_fit"}
            else DimensionScore(
                name,
                None,
                "unknown",
                None,
                missing_information=("Not scored after hard conflict",),
            )
            for name in CLINICAL_DIMENSIONS
        ]
    molecular = {"exact": 95, "compatible": 80, "unproven": 45}.get(
        review["molecular_fit"], 60
    )
    disease = {"exact": 95, "compatible": 82}.get(review["disease_fit"], 60)
    uncertain = review["match_class"] == "insufficient_biomarker_evidence"
    values = {
        "molecular_fit": molecular,
        "disease_fit": disease,
        "mechanistic_fit": 55 if uncertain else 82,
        "evidence_strength": 45 if uncertain else 78,
        "eligibility_compatibility": 50 if review["unknown_or_required_review"] else 80,
        "trial_design_relevance": 60,
    }
    return [
        DimensionScore(
            name,
            value,
            "partial",
            0.7,
            rationale=(review["rationale"],),
            evidence_references=(review["source_url"],),
            missing_information=tuple(review["unknown_or_required_review"]),
        )
        for name, value in values.items()
    ]


def run_recorded_case(
    *,
    pdf_path: Path,
    profile: Mapping[str, Any],
    reviews: list[Mapping[str, Any]],
    database: Path,
    location: PatientLocation,
    snapshot_id: str,
) -> IntegratedCaseResult:
    """Run a public PDF with recorded profile/model review through live local stages."""
    document = read_document(pdf_path, mode="fast")
    if any(page.extraction_method == "unreadable" for page in document.pages):
        raise ValueError(f"Unreadable pages in {pdf_path.name}")
    profile = dict(profile)
    profile.setdefault("schema_version", "0.3")
    profile["patient_context"].setdefault("prior_therapies_known", False)
    validate_molecular_profile(profile)
    molecular_summary = []
    for finding in profile["biomarkers"].get("snv_indel", []) + profile[
        "biomarkers"
    ].get("copy_number", []):
        molecular_summary.append(finding.get("source_text") or finding["gene"])
    msi = profile["biomarkers"].get("msi", {}).get("status")
    if msi:
        molecular_summary.append("MSI: " + msi)

    results = []
    with sqlite3.connect(database) as db:
        retrieved = {
            candidate.nct_id: candidate
            for candidate in retrieve_candidates(db, profile)
        }
        for review in reviews:
            if review["nct_id"] not in retrieved:
                raise ValueError(
                    f"Recorded review {review['nct_id']} was not reproduced by local candidate retrieval"
                )
            retrieval = retrieved[review["nct_id"]]
            trial = _trial(db, review["nct_id"])
            build_expert_packets(
                profile, trial, []
            )  # validate the exact expert input boundary
            experts = _recorded_experts(review)
            consensus = reach_consensus(experts)
            clinical = clinical_trial_score(_dimensions(review))
            sites = nearest_recruiting_sites(db, location, [review["nct_id"]], limit=3)
            nearest = sites[0] if sites else None
            geo = geographic_access_score(
                nearest.distance_km if nearest else None,
                study_status=trial["overall_status"],
                site_status=nearest.site_status if nearest else None,
            )
            position = trial_plot_position(clinical, geo)
            site_models = [
                OpenSite(
                    **{
                        k: v
                        for k, v in site.to_dict().items()
                        if k in OpenSite.model_fields
                    }
                )
                for site in sites
            ]
            results.append(
                TrialResult(
                    nct_id=trial["nct_id"],
                    title=trial["title"],
                    source_url=trial["source_url"],
                    overall_status=trial["overall_status"],
                    registry_last_update=trial["last_update_posted"],
                    retrieval_basis=[
                        *(
                            "disease: " + term
                            for term in retrieval.matched_disease_terms
                        ),
                        *(
                            "molecular: " + term
                            for term in retrieval.matched_molecular_terms
                        ),
                    ],
                    consensus=consensus,
                    expert_assessments=experts,
                    clinical_score=clinical.to_dict(),
                    geography_score=geo.to_dict(),
                    plot_position=position.to_dict(),
                    nearest_open_site=site_models[0] if site_models else None,
                    alternative_open_sites=site_models[1:],
                    rationale=review["rationale"],
                    missing_information=list(review["unknown_or_required_review"]),
                    discussion_questions=[
                        "Can the treating team confirm: " + item + "?"
                        for item in review["unknown_or_required_review"]
                    ],
                )
            )
    return IntegratedCaseResult(
        case_id=profile["case_id"],
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        snapshot_id=snapshot_id,
        source_report=SourceReport(
            filename=pdf_path.name,
            sha256=document.sha256,
            page_count=len(document.pages),
            reader_version=document.reader_version,
            ingestion_mode="recorded_public_sample_profile",
        ),
        patient_location={
            "city": location.city,
            "country": location.country,
            "latitude": location.latitude,
            "longitude": location.longitude,
        },
        molecular_profile=profile,
        molecular_biology_summary=molecular_summary,
        trials=results,
        limitations=[
            "The profile and expert review are recorded from the earlier public-sample POC; no live model call was made.",
            "Candidate trial IDs are a recorded retrieval set, not an exhaustive search.",
            "Eligibility remains undetermined until a trial site reviews the complete clinical record.",
            "Distance is great-circle distance to sites explicitly recruiting in the snapshot, not travel time.",
        ],
    )
