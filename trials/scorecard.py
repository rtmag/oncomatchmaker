"""Compute clinical and geographic scores as mathematically independent axes."""

from __future__ import annotations

import math
from typing import Mapping, Optional, Sequence

from schemas.trial_scorecard import (
    CLINICAL_DIMENSIONS,
    ClinicalTrialScore,
    DimensionScore,
    GeographyScore,
    TrialPlotPosition,
)

DEFAULT_CLINICAL_WEIGHTS = {
    "molecular_fit": 30.0,
    "disease_fit": 15.0,
    "mechanistic_fit": 15.0,
    "evidence_strength": 15.0,
    "eligibility_compatibility": 20.0,
    "trial_design_relevance": 5.0,
}


def clinical_trial_score(
    dimensions: Sequence[DimensionScore],
    weights: Optional[Mapping[str, float]] = None,
) -> ClinicalTrialScore:
    """Return a clinical composite that contains no geographic information.

    `observed_score` averages only known dimensions. `coverage` reports how much
    of the configured weight is known. `composite_score` is the conservative
    ranking value: observed score multiplied by coverage.
    """
    configured = dict(DEFAULT_CLINICAL_WEIGHTS if weights is None else weights)
    if set(configured) != set(CLINICAL_DIMENSIONS):
        raise ValueError("weights must contain every clinical dimension exactly once")
    if any(not math.isfinite(value) or value < 0 for value in configured.values()):
        raise ValueError("weights must be finite and nonnegative")
    total_weight = sum(configured.values())
    if total_weight <= 0:
        raise ValueError("at least one clinical weight must be positive")
    indexed = {dimension.dimension: dimension for dimension in dimensions}
    if len(indexed) != len(dimensions) or set(indexed) != set(CLINICAL_DIMENSIONS):
        raise ValueError("provide exactly one score for every clinical dimension")

    conflicts = tuple(
        dimension.dimension
        for dimension in dimensions
        if dimension.status == "conflict"
    )
    known = [dimension for dimension in dimensions if dimension.value is not None]
    known_weight = sum(configured[dimension.dimension] for dimension in known)
    coverage = known_weight / total_weight
    observed = (
        sum(dimension.value * configured[dimension.dimension] for dimension in known)
        / known_weight
        if known_weight
        else None
    )
    composite = observed * coverage if observed is not None and not conflicts else None
    return ClinicalTrialScore(
        observed_score=round(observed, 1) if observed is not None else None,
        composite_score=round(composite, 1) if composite is not None else None,
        coverage=round(coverage, 3),
        rankable=not conflicts and composite is not None,
        weights=configured,
        dimensions=tuple(dimensions),
        hard_conflicts=conflicts,
    )


def geographic_access_score(
    distance_km: Optional[float],
    *,
    study_status: str,
    site_status: Optional[str],
    distance_scale_km: float = 250.0,
) -> GeographyScore:
    """Score distance only when both the study and individual site are open."""
    if not math.isfinite(distance_scale_km) or distance_scale_km <= 0:
        raise ValueError("distance_scale_km must be positive and finite")
    if distance_km is not None and (not math.isfinite(distance_km) or distance_km < 0):
        raise ValueError("distance_km must be finite and nonnegative")
    if study_status != "RECRUITING" or site_status != "RECRUITING":
        return GeographyScore(
            score=None,
            distance_km=distance_km,
            availability="no_confirmed_open_site",
            study_status=study_status,
            site_status=site_status,
            rationale="No geographic score: study and site must both be explicitly recruiting.",
        )
    if distance_km is None:
        return GeographyScore(
            score=None,
            distance_km=None,
            availability="open_site_distance_unknown",
            study_status=study_status,
            site_status=site_status,
            rationale="An open site exists, but its distance cannot be calculated.",
        )
    score = 100 * math.exp(-distance_km / distance_scale_km)
    return GeographyScore(
        score=round(score, 1),
        distance_km=round(distance_km, 1),
        availability="open_site",
        study_status=study_status,
        site_status=site_status,
        rationale="Distance score uses the nearest explicitly recruiting site and Haversine distance.",
    )


def trial_plot_position(
    clinical: ClinicalTrialScore,
    geography: GeographyScore,
    *,
    clinical_threshold: float = 70.0,
    geography_threshold: float = 50.0,
    minimum_coverage: float = 0.6,
) -> TrialPlotPosition:
    """Place a trial on independent clinical (x) and access (y) axes."""
    for value, name in (
        (clinical_threshold, "clinical_threshold"),
        (geography_threshold, "geography_threshold"),
    ):
        if not 0 <= value <= 100:
            raise ValueError(name + " must be between 0 and 100")
    if not 0 <= minimum_coverage <= 1:
        raise ValueError("minimum_coverage must be between 0 and 1")
    if not clinical.rankable or clinical.composite_score is None:
        return TrialPlotPosition(
            "not_plottable",
            None,
            geography.score,
            None,
            clinical_threshold,
            geography_threshold,
            "Clinical hard conflict or no scorable clinical evidence.",
        )
    if clinical.coverage < minimum_coverage:
        return TrialPlotPosition(
            "not_plottable",
            clinical.composite_score,
            geography.score,
            None,
            clinical_threshold,
            geography_threshold,
            "Clinical evidence coverage is below the configured plotting threshold.",
        )
    if geography.score is None:
        return TrialPlotPosition(
            "not_plottable",
            clinical.composite_score,
            None,
            None,
            clinical_threshold,
            geography_threshold,
            "No confirmed open site with a calculable distance.",
        )
    high_clinical = clinical.composite_score >= clinical_threshold
    high_geography = geography.score >= geography_threshold
    quadrant = {
        (True, True): "high_match_high_access",
        (True, False): "high_match_low_access",
        (False, True): "lower_match_high_access",
        (False, False): "lower_match_low_access",
    }[(high_clinical, high_geography)]
    return TrialPlotPosition(
        "plottable",
        clinical.composite_score,
        geography.score,
        quadrant,
        clinical_threshold,
        geography_threshold,
        "Thresholds organize review; they are configurable and not clinically validated cutoffs.",
    )
