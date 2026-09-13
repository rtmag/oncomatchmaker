"""Only structured age/sex facts are automatically resolved in this POC.

Free-text criteria may contain cohort-specific alternatives or negation, so are
retained for review instead of interpreted by a brittle keyword classifier.
"""

import re

from schemas.match_results import Criterion, Eligibility


def evaluate_eligibility(profile, trial):
    criteria = []
    context = profile.patient_context
    for label, raw, lower in [
        ("Minimum age", trial.minimum_age, True),
        ("Maximum age", trial.maximum_age, False),
    ]:
        if raw and raw != "N/A":
            match = re.fullmatch(r"(\d+(?:\.\d+)?) Years", raw)
            status = "UNKNOWN"
            if match and context.age is not None:
                passes = (
                    context.age >= float(match[1])
                    if lower
                    else context.age <= float(match[1])
                )
                status = "MATCH" if passes else "MISMATCH"
            criteria.append(Criterion(criterion=label, status=status, source_text=raw))
    if trial.sex and trial.sex != "ALL":
        sex = (context.sex or "").upper()
        status = (
            "UNKNOWN"
            if sex not in {"MALE", "FEMALE"}
            else "MATCH"
            if sex == trial.sex
            else "MISMATCH"
        )
        criteria.append(
            Criterion(criterion="Sex criterion", status=status, source_text=trial.sex)
        )
    text = trial.eligibility_text
    for label, pattern in [
        (
            "ECOG and cohort-specific performance requirements",
            r"ECOG|performance status",
        ),
        ("Prior therapy requirements", r"prior|previous|treatment.na.ve"),
        ("CNS disease requirements", r"brain|CNS"),
        ("Organ function requirements", r"organ function|creatinine|bilirubin"),
    ]:
        if re.search(pattern, text, re.I):
            criteria.append(
                Criterion(
                    criterion=label,
                    status="UNKNOWN",
                    source_text=next(
                        (
                            line.strip()
                            for line in text.splitlines()
                            if re.search(pattern, line, re.I)
                        ),
                        text,
                    ),
                )
            )
    criteria.append(
        Criterion(
            criterion="Full molecular, disease, cohort and eligibility review by trial team",
            status="UNKNOWN",
            source_text="Full source eligibility criteria require review.",
        )
    )
    states = [c.status for c in criteria]
    status = (
        "LIKELY_NOT_ELIGIBLE"
        if "MISMATCH" in states
        else "POSSIBLE_MATCH"
        if "MATCH" in states
        else "INSUFFICIENT_INFORMATION"
    )
    return Eligibility(
        status=status,
        criteria=criteria,
        missing_information=[c.criterion for c in criteria if c.status == "UNKNOWN"],
    )
