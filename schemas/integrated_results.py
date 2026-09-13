"""Frozen v0.1 result contract shared with UI, chart, and report work."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ResultModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SourceReport(ResultModel):
    filename: str
    sha256: str
    page_count: int = Field(ge=1)
    reader_version: str
    ingestion_mode: Literal["live_model", "recorded_public_sample_profile"]


class OpenSite(ResultModel):
    facility: str | None
    city: str | None
    region: str | None
    country: str | None
    distance_km: float
    study_status: str
    site_status: str
    registry_last_update: str | None
    snapshot_retrieved_at: str


class ExpertAssessmentResult(ResultModel):
    trial_id: str
    expert_role: str
    assessment: Literal["support", "caution", "conflict", "unknown"]
    confidence: float = Field(ge=0, le=1)
    relationships: list[str]
    supporting_facts: list[str]
    conflicting_facts: list[str]
    missing_information: list[str]
    evidence_references: list[str]
    reasoning_summary: str


class ConsensusResult(ResultModel):
    trial_id: str
    disposition: str
    match_tier: str
    primary_relationship: str | None
    known_conflicts: list[str]
    missing_information: list[str]
    eligibility_state: Literal["not_determined"]
    expert_assessments: list[str]
    safety_gate_triggered_by: list[str]


class DimensionResult(ResultModel):
    dimension: str
    value: float | None
    status: Literal["supported", "partial", "unknown", "conflict"]
    confidence: float | None
    rationale: list[str]
    evidence_references: list[str]
    missing_information: list[str]


class ClinicalScoreResult(ResultModel):
    observed_score: float | None
    composite_score: float | None
    coverage: float = Field(ge=0, le=1)
    rankable: bool
    weights: dict[str, float]
    dimensions: list[DimensionResult]
    hard_conflicts: list[str]


class GeographyScoreResult(ResultModel):
    score: float | None
    distance_km: float | None
    availability: str
    study_status: str
    site_status: str | None
    rationale: str


class PlotPositionResult(ResultModel):
    plot_status: Literal["plottable", "not_plottable"]
    clinical_x: float | None
    geography_y: float | None
    quadrant: str | None
    clinical_threshold: float
    geography_threshold: float
    rationale: str


class TrialResult(ResultModel):
    nct_id: str
    title: str
    source_url: str
    overall_status: str
    registry_last_update: str | None
    retrieval_basis: list[str]
    consensus: ConsensusResult
    expert_assessments: list[ExpertAssessmentResult]
    clinical_score: ClinicalScoreResult
    geography_score: GeographyScoreResult
    plot_position: PlotPositionResult
    nearest_open_site: OpenSite | None
    alternative_open_sites: list[OpenSite] = Field(default_factory=list)
    rationale: str
    missing_information: list[str] = Field(default_factory=list)
    discussion_questions: list[str] = Field(default_factory=list)


class IntegratedCaseResult(ResultModel):
    result_schema_version: Literal["0.1"] = "0.1"
    case_id: str
    generated_at: str
    snapshot_id: str
    source_report: SourceReport
    patient_location: dict[str, Any]
    molecular_profile: dict[str, Any]
    molecular_biology_summary: list[str]
    trials: list[TrialResult]
    limitations: list[str]
    disclaimer: str = "Clinical decision-support for professional review; not medical advice or a determination of eligibility."
