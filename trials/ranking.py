"""Transparent retrieval relevance; score is not eligibility or efficacy."""

import math
import re

from schemas.match_results import TrialScore
from trials.search import actionable_findings, disease_name

DEFAULT_WEIGHTS = dict(
    molecular=30, disease=15, eligibility=20, evidence=10, recruitment=10, geography=15
)


def score_trial(profile, trial, eligibility, nearest_site=None, weights=None):
    weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if (
        set(weights) != set(DEFAULT_WEIGHTS)
        or any(not math.isfinite(v) or v < 0 for v in weights.values())
        or sum(weights.values()) <= 0
    ):
        raise ValueError("Supply all six nonnegative finite component weights")
    # Title mentions are relevance signals, never a claim of required biomarkers.
    title = trial.title.upper()
    molecular = None
    reasons = []
    for gene, variant in actionable_findings(profile):
        if re.search(rf"\b{re.escape(gene)}\b", title):
            exact = bool(
                variant and re.search(rf"\b{re.escape(variant.upper())}\b", title)
            )
            molecular = max(molecular or 0, 1 if exact else 2 / 3)
            reasons.append(
                f"Title mentions {gene}{' ' + variant if exact else ''}; cohort eligibility requires verification."
            )
    disease = disease_name(profile.disease.normalized or profile.disease.raw_text)
    conditions = [disease_name(c) for c in trial.conditions]
    disease_score = (
        1
        if disease and disease in conditions
        else 8 / 15
        if any(
            c in {"solid tumor", "solid tumors", "advanced solid tumors"}
            for c in conditions
        )
        else None
    )
    if disease_score is None:
        reasons.append(
            "Disease compatibility is unconfirmed; inspect listed conditions and cohorts."
        )
    criteria = eligibility.criteria
    known = sum(c.status in {"MATCH", "MISMATCH"} for c in criteria)
    eligibility_score = (
        sum(c.status == "MATCH" for c in criteria) / len(criteria) if known else None
    )
    phase_scale = {
        "EARLY_PHASE1": 0.1,
        "PHASE1": 0.25,
        "PHASE2": 0.5,
        "PHASE3": 0.75,
        "PHASE4": 1,
    }
    phases = [phase_scale[p] for p in trial.phase if p in phase_scale]
    recruiting_sites = any(s.status == "RECRUITING" for s in trial.sites)
    recruitment = (
        (1 if recruiting_sites else 0.5)
        if trial.status == "RECRUITING"
        else 0.2
        if trial.status == "NOT_YET_RECRUITING"
        else 0
    )
    fractions = dict(
        molecular=molecular,
        disease=disease_score,
        eligibility=eligibility_score,
        evidence=max(phases) if phases else None,
        recruitment=recruitment,
        geography=math.exp(-nearest_site.distance_km / 250) if nearest_site else None,
    )
    components = {
        k: round(v * weights[k], 2) if v is not None else None
        for k, v in fractions.items()
    }
    reasons.append(
        "Development score uses phase only, not evidence of therapeutic benefit. Unknown components earn no points; totals are not rescaled."
    )
    return TrialScore(
        overall_score=round(sum(v or 0 for v in components.values()), 2),
        coverage=round(
            sum(weights[k] for k, v in components.items() if v is not None)
            / sum(weights.values()),
            3,
        ),
        components=components,
        weights=weights,
        rationale=reasons,
    )
