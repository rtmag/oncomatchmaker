"""Dependency-free validation for ASTRA's shared profile and expert contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


EXPERT_ROLES = (
    "molecular_profile_qc",
    "disease_oncology",
    "actionability_evidence",
    "pathway_resistance",
    "trial_eligibility",
    "safety_critic",
)
ASSESSMENTS = frozenset({"support", "caution", "conflict", "unknown"})
RELATIONSHIPS = frozenset({
    "direct_variant",
    "gene_level",
    "phenotype_biomarker",
    "pathway_mechanism",
    "resistance_strategy",
    "broad_basket",
    "not_applicable",
})


class ContractError(ValueError):
    """Raised when an object violates a shared ASTRA contract."""


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{name} must be an object")
    return value


def _list_of_strings(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ContractError(f"{name} must be a list of strings")
    return value


def validate_molecular_profile(profile: Mapping[str, Any]) -> None:
    """Validate the stable boundary needed by the matching pipeline.

    This intentionally permits additional vendor-neutral fields so Track A can
    evolve through schema versions without silently discarding source detail.
    """
    profile = _mapping(profile, "profile")
    if not isinstance(profile.get("schema_version"), str):
        raise ContractError("profile.schema_version is required")
    report = _mapping(profile.get("report"), "profile.report")
    for field in ("vendor", "assay", "sample_type"):
        if field not in report:
            raise ContractError(f"profile.report.{field} is required")
    disease = _mapping(profile.get("disease"), "profile.disease")
    if not isinstance(disease.get("raw_text"), str) or not disease["raw_text"].strip():
        raise ContractError("profile.disease.raw_text is required")
    normalized = disease.get("normalized")
    if normalized is not None and not isinstance(normalized, str):
        raise ContractError("profile.disease.normalized must be a string or null")
    if "synonyms" in disease:
        _list_of_strings(disease["synonyms"], "profile.disease.synonyms")
    _mapping(profile.get("patient_context"), "profile.patient_context")
    biomarkers = _mapping(profile.get("biomarkers"), "profile.biomarkers")
    for collection in ("snv_indel", "copy_number", "fusions"):
        for index, finding in enumerate(biomarkers.get(collection, [])):
            finding = _mapping(finding, f"profile.biomarkers.{collection}[{index}]")
            gene = finding.get("gene")
            if not isinstance(gene, str) or not gene.strip():
                raise ContractError(f"profile.biomarkers.{collection}[{index}].gene is required")
            if gene != gene.upper():
                raise ContractError(f"canonical gene symbol must be uppercase: {gene}")
            if "gene_synonyms" in finding:
                _list_of_strings(
                    finding["gene_synonyms"],
                    f"profile.biomarkers.{collection}[{index}].gene_synonyms",
                )


@dataclass(frozen=True)
class ExpertAssessment:
    trial_id: str
    expert_role: str
    assessment: str
    confidence: float
    relationships: tuple[str, ...]
    supporting_facts: tuple[str, ...]
    conflicting_facts: tuple[str, ...]
    missing_information: tuple[str, ...]
    evidence_references: tuple[str, ...]
    reasoning_summary: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExpertAssessment":
        value = _mapping(value, "assessment")
        required = {
            "trial_id", "expert_role", "assessment", "confidence", "relationships",
            "supporting_facts", "conflicting_facts", "missing_information",
            "evidence_references", "reasoning_summary",
        }
        missing = sorted(required - value.keys())
        if missing:
            raise ContractError("assessment missing fields: " + ", ".join(missing))
        if value["expert_role"] not in EXPERT_ROLES:
            raise ContractError("unknown expert role: " + str(value["expert_role"]))
        if value["assessment"] not in ASSESSMENTS:
            raise ContractError("unknown assessment: " + str(value["assessment"]))
        if not isinstance(value["confidence"], (int, float)) or not 0 <= value["confidence"] <= 1:
            raise ContractError("assessment.confidence must be between 0 and 1")
        relationships = _list_of_strings(value["relationships"], "assessment.relationships")
        invalid = sorted(set(relationships) - RELATIONSHIPS)
        if invalid:
            raise ContractError("unknown relationships: " + ", ".join(invalid))
        list_fields = {}
        for field in (
            "supporting_facts", "conflicting_facts", "missing_information",
            "evidence_references",
        ):
            list_fields[field] = tuple(_list_of_strings(value[field], "assessment." + field))
        if not isinstance(value["trial_id"], str) or not value["trial_id"].startswith("NCT"):
            raise ContractError("assessment.trial_id must be an NCT identifier")
        if not isinstance(value["reasoning_summary"], str) or not value["reasoning_summary"].strip():
            raise ContractError("assessment.reasoning_summary is required")
        return cls(
            trial_id=value["trial_id"], expert_role=value["expert_role"],
            assessment=value["assessment"], confidence=float(value["confidence"]),
            relationships=tuple(relationships), reasoning_summary=value["reasoning_summary"],
            **list_fields,
        )
