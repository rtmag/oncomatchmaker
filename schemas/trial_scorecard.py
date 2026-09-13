"""Contracts for independent clinical-match and geographic-access scores."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


CLINICAL_DIMENSIONS = (
    "molecular_fit",
    "disease_fit",
    "mechanistic_fit",
    "evidence_strength",
    "eligibility_compatibility",
    "trial_design_relevance",
)
DIMENSION_STATES = frozenset({"supported", "partial", "unknown", "conflict"})


@dataclass(frozen=True)
class DimensionScore:
    dimension: str
    value: Optional[float]
    status: str
    confidence: Optional[float]
    rationale: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()

    def __post_init__(self):
        if self.dimension not in CLINICAL_DIMENSIONS:
            raise ValueError("unknown clinical dimension: " + self.dimension)
        if self.status not in DIMENSION_STATES:
            raise ValueError("unknown dimension status: " + self.status)
        if self.value is not None and not 0 <= self.value <= 100:
            raise ValueError("dimension value must be between 0 and 100")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.status in {"unknown", "conflict"} and self.value is not None:
            raise ValueError("unknown or conflicting dimensions cannot have a numeric value")
        if self.status in {"supported", "partial"} and self.value is None:
            raise ValueError("supported or partial dimensions require a numeric value")


@dataclass(frozen=True)
class ClinicalTrialScore:
    observed_score: Optional[float]
    composite_score: Optional[float]
    coverage: float
    rankable: bool
    weights: dict[str, float]
    dimensions: tuple[DimensionScore, ...]
    hard_conflicts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeographyScore:
    score: Optional[float]
    distance_km: Optional[float]
    availability: str
    study_status: str
    site_status: Optional[str]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrialPlotPosition:
    plot_status: str
    clinical_x: Optional[float]
    geography_y: Optional[float]
    quadrant: Optional[str]
    clinical_threshold: float
    geography_threshold: float
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
