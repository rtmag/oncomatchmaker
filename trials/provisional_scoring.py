"""Fresh patient-to-registry evidence support; no cached patient match."""

from trials.clinical_scoring import CLINICAL_WEIGHTS, aggregate
from trials.cohort_matching import assess_cohorts, disease_fit


def provisional_score(profile, features):
    components = dict.fromkeys(CLINICAL_WEIGHTS)
    if features is None or features["status"] not in {
        "RECRUITING",
        "NOT_YET_RECRUITING",
    }:
        return {
            **aggregate(components),
            "status": "unscored",
            "references": [],
            "rationale": ["Features missing/stale or study not active/upcoming."],
        }
    assessment = assess_cohorts(profile, features)
    references = list(assessment["references"])
    reasons = []
    if assessment["supported"]:
        molecular, disease, mention = max(
            assessment["supported"], key=lambda s: s[0] * 30 + s[1] * 15
        )
        components.update(molecular=molecular, disease=disease)
        references.append(mention)
        reasons.append(
            "Molecular finding and disease context supported within the same registry clause/context; full eligibility remains unconfirmed."
        )
    elif not assessment["restricted"]:
        components["disease"] = disease_fit(
            features["title"] + " " + " ".join(features["conditions"]), profile
        )
        if components["disease"] is not None:
            references.append(
                {
                    "source_field": "title/conditions",
                    "text": features["title"] + " " + " ".join(features["conditions"]),
                }
            )
    if assessment["restricted"]:
        reasons.append(assessment["reason"])
    reasons.append(
        "Fixed-denominator evidence support, not probability of eligibility or benefit. Unknown dimensions add no supported points; inspect coverage and bounds. Unparsed requirements need expert review."
    )
    result = aggregate(components)
    return {
        **result,
        "rationale": reasons,
        "references": references,
        "status": "cohort_unconfirmed"
        if assessment["restricted"]
        else "provisional"
        if result["overall_score"] is not None
        else "unscored",
    }
