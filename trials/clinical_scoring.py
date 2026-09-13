"""Shared score arithmetic; coverage is not evidence of eligibility."""

CLINICAL_WEIGHTS = {
    "molecular": 30.0,
    "disease": 15.0,
    "evidence": 15.0,
    "mechanism": 15.0,
    "eligibility": 20.0,
    "safety": 5.0,
}
SCORE_VERSION = "clinical-fit-v2"


def aggregate(components, conflict=False):
    known = sum(
        weight
        for name, weight in CLINICAL_WEIGHTS.items()
        if components.get(name) is not None
    )
    credit = sum(
        CLINICAL_WEIGHTS[name] * value
        for name, value in components.items()
        if value is not None
    )
    return {
        "overall_score": round(100 * credit / known, 1)
        if known and not conflict
        else None,
        "coverage": round(known / 100, 3),
        "components": components,
        "weights": CLINICAL_WEIGHTS,
        "score_version": SCORE_VERSION,
        # Bounds reflect unassessed dimensions, not statistical confidence intervals.
        "uncertainty_bounds": [round(credit, 1), round(credit + 100 - known, 1)]
        if not conflict
        else None,
    }
