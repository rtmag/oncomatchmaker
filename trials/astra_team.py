"""Role packets and deterministic consensus safeguards for the ASTRA team."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from schemas.astra_contracts import (
    EXPERT_ROLES,
    ContractError,
    ExpertAssessment,
    validate_molecular_profile,
)


@dataclass(frozen=True)
class ExpertRole:
    name: str
    mandate: str
    required_focus: tuple[str, ...]


ROLE_DEFINITIONS = {
    "molecular_profile_qc": ExpertRole(
        "molecular_profile_qc",
        "Verify normalized molecular facts without adding facts absent from the report.",
        (
            "canonical symbols",
            "alteration specificity",
            "somatic versus germline",
            "assay limitations",
        ),
    ),
    "disease_oncology": ExpertRole(
        "disease_oncology",
        "Assess disease, histology, stage, and treatment-setting compatibility.",
        ("disease context", "histology", "stage", "treatment setting"),
    ),
    "actionability_evidence": ExpertRole(
        "actionability_evidence",
        "Grade sourced biomarker-disease-intervention evidence and its transferability.",
        (
            "same-disease evidence",
            "cross-disease evidence",
            "evidence level",
            "provenance",
        ),
    ),
    "pathway_resistance": ExpertRole(
        "pathway_resistance",
        "Evaluate pathway, co-alteration, synthetic-lethal, and resistance rationale.",
        ("mechanism", "co-alterations", "resistance", "biological extrapolation"),
    ),
    "trial_eligibility": ExpertRole(
        "trial_eligibility",
        "Assess the applicable cohort, separating inclusion, exclusion, and unknown criteria.",
        (
            "cohort",
            "inclusions",
            "exclusions",
            "prior therapy",
            "missing clinical facts",
        ),
    ),
    "safety_critic": ExpertRole(
        "safety_critic",
        "Challenge unsupported claims, contradictions, and unsafe eligibility conclusions.",
        (
            "contradictions",
            "unsupported assumptions",
            "citation support",
            "uncertainty",
        ),
    ),
}

ALLOWED_TRIAL_FIELDS = {
    "nct_id",
    "title",
    "overall_status",
    "study_type",
    "primary_purpose",
    "conditions",
    "eligibility_text",
    "last_update_posted",
    "status_verified",
    "retrieved_at",
    "source_url",
    "raw_json",
}
SAFETY_GATE_ROLES = {
    "molecular_profile_qc",
    "disease_oncology",
    "trial_eligibility",
    "safety_critic",
}
RELATIONSHIP_PRIORITY = (
    "direct_variant",
    "phenotype_biomarker",
    "gene_level",
    "resistance_strategy",
    "pathway_mechanism",
    "broad_basket",
)


def build_expert_packets(
    profile: Mapping[str, Any],
    trial: Mapping[str, Any],
    evidence: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Create identical evidence-bounded inputs for each independent expert."""
    validate_molecular_profile(profile)
    if not isinstance(trial.get("nct_id"), str):
        raise ContractError("trial.nct_id is required")
    trial_context = {key: trial[key] for key in ALLOWED_TRIAL_FIELDS if key in trial}
    shared = {
        "profile": dict(profile),
        "trial": trial_context,
        "evidence": [dict(item) for item in evidence],
        "constraints": [
            "Use only supplied profile, registry, and evidence facts.",
            "Preserve unknowns; do not infer eligibility.",
            "Do not use or imply site-level recruitment or geography.",
            "Return the ExpertAssessment contract only.",
        ],
    }
    return [
        {
            "expert_role": role.name,
            "mandate": role.mandate,
            "required_focus": list(role.required_focus),
            **copy.deepcopy(shared),
        }
        for role in ROLE_DEFINITIONS.values()
    ]


def reach_consensus(values: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Combine expert outputs while making safety conflicts non-overridable."""
    assessments = [ExpertAssessment.from_dict(value) for value in values]
    if len(assessments) != len(EXPERT_ROLES):
        raise ContractError(
            "consensus requires exactly one assessment from every expert role"
        )
    roles = [item.expert_role for item in assessments]
    if set(roles) != set(EXPERT_ROLES) or len(roles) != len(set(roles)):
        raise ContractError(
            "consensus requires exactly one assessment from every expert role"
        )
    trial_ids = {item.trial_id for item in assessments}
    if len(trial_ids) != 1:
        raise ContractError("all expert assessments must concern the same trial")

    hard_conflicts = [
        item
        for item in assessments
        if item.expert_role in SAFETY_GATE_ROLES and item.assessment == "conflict"
    ]
    relationships = {
        relationship
        for item in assessments
        for relationship in item.relationships
        if relationship != "not_applicable"
    }
    primary_relationship = next(
        (
            relationship
            for relationship in RELATIONSHIP_PRIORITY
            if relationship in relationships
        ),
        None,
    )
    missing = sorted(
        {fact for item in assessments for fact in item.missing_information}
    )
    conflicts = sorted(
        {fact for item in assessments for fact in item.conflicting_facts}
    )

    if hard_conflicts:
        match_tier = "not_matched"
        disposition = "conflict"
    elif any(item.assessment == "unknown" for item in assessments):
        match_tier = "needs_review"
        disposition = "insufficient_information"
    elif primary_relationship in {
        "direct_variant",
        "phenotype_biomarker",
        "gene_level",
    }:
        has_caution = any(item.assessment == "caution" for item in assessments)
        match_tier = "tier_2" if missing or has_caution else "tier_1"
        disposition = "candidate"
    elif primary_relationship in {"resistance_strategy", "pathway_mechanism"}:
        match_tier = "tier_3"
        disposition = "mechanistic_candidate"
    elif primary_relationship == "broad_basket":
        match_tier = "tier_4"
        disposition = "exploratory_candidate"
    else:
        match_tier = "needs_review"
        disposition = "insufficient_information"

    return {
        "trial_id": assessments[0].trial_id,
        "disposition": disposition,
        "match_tier": match_tier,
        "primary_relationship": primary_relationship,
        "known_conflicts": conflicts,
        "missing_information": missing,
        "eligibility_state": "not_determined",
        "expert_assessments": [item.expert_role for item in assessments],
        "safety_gate_triggered_by": [item.expert_role for item in hard_conflicts],
    }
