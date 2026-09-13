from __future__ import annotations

from typing import Literal

from pydantic import Field

from schemas.molecular_profile import Location, Model, MolecularProfile


class Site(Location):
    name: str = "Unknown facility"
    status: str = "UNKNOWN"
    contacts: list[dict] = Field(default_factory=list)


class TrialCandidate(Model):
    nct_id: str = Field(pattern=r"^NCT\d{8}$")
    title: str
    status: str = "UNKNOWN"
    phase: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    eligibility_text: str = ""
    minimum_age: str | None = None
    maximum_age: str | None = None
    sex: str | None = None
    sites: list[Site] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    retrieved_at: str
    cached: bool = False
    expanded_access: bool | None = None
    registry_updated_at: str | None = None


class Criterion(Model):
    criterion: str
    status: Literal["MATCH", "MISMATCH", "UNKNOWN", "NOT_APPLICABLE"]
    source_text: str = ""


class Eligibility(Model):
    status: Literal[
        "LIKELY_MATCH",
        "POSSIBLE_MATCH",
        "INSUFFICIENT_INFORMATION",
        "LIKELY_NOT_ELIGIBLE",
    ]
    criteria: list[Criterion] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class NearestSite(Model):
    site: Site
    distance_km: float


class TrialScore(Model):
    overall_score: float | None
    coverage: float
    components: dict[str, float | None]
    weights: dict[str, float]
    rationale: list[str]


class RankedTrial(Model):
    trial: TrialCandidate
    match: TrialScore
    eligibility: Eligibility
    nearest_site: NearestSite | None = None
    geography_score: float | None = None
    geography_availability: str = "not_scored"
    expert_assessments: list[dict] = Field(default_factory=list)
    consensus: dict = Field(default_factory=dict)
    retrieval_route: str = "named_disease"
    category: Literal["recruiting", "not_yet_recruiting", "review", "excluded"]


class ApprovedOption(Model):
    biomarker: str
    therapy: str
    disease: str
    context: Literal[
        "same_disease", "tumor_agnostic", "other_disease", "investigational"
    ]
    jurisdiction: str
    evidence_level: str
    restrictions: list[str]
    sources: list[str]
    verified_at: str
    applicability: str = (
        "Biomarker association only; full indication requires clinician review."
    )


class ExploratoryTrial(Model):
    trial: TrialCandidate
    matched_variants: list[str]
    disease_context: str = "Other or unconfirmed tumor type — not an eligibility match"
    expert_reviewed: bool = False


class MatchResults(Model):
    profile: MolecularProfile
    approved_options: list[ApprovedOption] = Field(default_factory=list)
    trials: list[RankedTrial] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    search_status: Literal["complete", "partial", "failed", "not_searched"] = "complete"
    queries: list[dict[str, str]] = Field(default_factory=list)
    screening_summary: dict[str, int] = Field(default_factory=dict)
    screening_landscape: list[dict] = Field(default_factory=list)
    exploratory_trials: list[ExploratoryTrial] = Field(default_factory=list)
