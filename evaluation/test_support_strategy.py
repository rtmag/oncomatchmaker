"""Offline counterfactual experiment; does not change application policy.

Run: python -m evaluation.test_support_strategy
Printed JSON contains metrics, not new clinical or expert assessments.
Only v2 arithmetic is frozen here; retrieval/features use the current checkout.
The historical report is not reproduced by running this against a newer parser.
Use evaluation.cohort_scoring_regression for current cohort-policy validation.
"""

import json
import sqlite3
import time
from pathlib import Path

from schemas.molecular_profile import Location
from trials.candidate_retrieval import screen_trials
from trials.clinical_scoring import CLINICAL_WEIGHTS
from trials.clinical_scoring import aggregate as current_aggregate
from trials.pipeline import SNAPSHOT, attach_screening_geography
from trials.registry_features import load

ROOT = Path(__file__).resolve().parents[1]


def aggregate(components, conflict=False):
    """Freeze the v2 arithmetic baseline; do not inherit live policy changes."""
    result = current_aggregate(components, conflict=conflict)
    known = sum(CLINICAL_WEIGHTS[k] for k, v in components.items() if v is not None)
    credit = sum(
        CLINICAL_WEIGHTS[k] * v for k, v in components.items() if v is not None
    )
    result.update(
        overall_score=round(100 * credit / known, 1)
        if known and not conflict
        else None,
        score_version="clinical-fit-v2",
    )
    return result


def fixed_support(assessment):
    if assessment["overall_score"] is None:
        return None
    return round(
        sum(
            CLINICAL_WEIGHTS[k] * v
            for k, v in assessment["components"].items()
            if v is not None
        ),
        1,
    )


def select(rows, budget=20, excluded=()):
    """8 support / 6 access / 6 uncertainty slots; budgets are experimental."""
    pool = [row for row in rows if row["nct_id"] not in excluded]
    clinical = sorted(
        pool,
        key=lambda r: (
            -(r["support"] if r["support"] is not None else -1),
            -len(r["exact"]),
            -r["retrieval"],
            r["nct_id"],
        ),
    )
    # Geographic access cannot rescue a missing molecular/disease signal here.
    plausible = [
        r
        for r in pool
        if r["support"] is not None
        and r["assessment"]["components"].get("disease") is not None
        and (
            r["assessment"]["components"].get("molecular") is not None
            or r["negative_profile"]
        )
    ]
    access = sorted(
        [r for r in plausible if r["geo"] is not None],
        key=lambda r: (-r["geo"], -r["support"], r["nct_id"]),
    )
    uncertain = sorted(
        [
            r
            for r in pool
            if r["exact"] or r["assessment"]["components"].get("molecular") is not None
        ],
        key=lambda r: (
            -(r["assessment"].get("uncertainty_bounds") or [0, 0])[1],
            -len(r["exact"]),
            -r["retrieval"],
            r["nct_id"],
        ),
    )
    chosen, seen = [], set()
    for queue, slots in [
        (clinical, 8),
        (access, 6),
        (uncertain, 6),
        (clinical, budget),
    ]:
        added = 0
        for row in queue:
            if row["nct_id"] not in seen:
                chosen.append(row)
                seen.add(row["nct_id"])
                added += 1
            if added >= slots or len(chosen) >= budget:
                break
        if len(chosen) >= budget:
            break
    return chosen


def invariants():
    disease_only = dict.fromkeys(CLINICAL_WEIGHTS)
    disease_only["disease"] = 0.9
    estimate = aggregate(disease_only)
    assert estimate["overall_score"] == 90
    assert fixed_support(estimate) == 13.5
    assert aggregate(dict.fromkeys(CLINICAL_WEIGHTS))["overall_score"] is None
    assert fixed_support(aggregate(disease_only, conflict=True)) is None
    refined = {key: 0.6 for key in CLINICAL_WEIGHTS}
    assert fixed_support(aggregate(refined)) == 60
    assert fixed_support(aggregate(refined)) > fixed_support(estimate)
    # Learning a worse value can reduce support: no rule forces reviewed wins.
    refined["disease"] = 0
    assert fixed_support(aggregate(refined)) == 51
    return {
        "disease_only_old": 90,
        "disease_only_fixed": 13.5,
        "six_caution_fixed": 60,
        "conflict_score": None,
    }


def run():
    start = time.perf_counter()
    features = load(SNAPSHOT)
    if len(features) != 26423:
        raise RuntimeError(
            "Build the complete local feature snapshot before this experiment"
        )
    profiles = json.loads(
        (ROOT / "evaluation/matching_spike/profiles.json").read_text()
    )["cases"]
    profiles += [
        {
            "case_id": "synthetic-cholangiocarcinoma-kras-g12d",
            "disease": {"raw_text": "cholangiocarcinoma"},
            "biomarkers": {"snv_indel": [{"gene": "KRAS", "protein_change": "G12D"}]},
        },
        {
            "case_id": "synthetic-negative-cholangiocarcinoma",
            "disease": {"raw_text": "cholangiocarcinoma"},
            "biomarkers": {"snv_indel": []},
        },
    ]
    cities = json.loads((ROOT / "evaluation/geography_test_cities.json").read_text())
    cities.insert(
        0,
        dict(city="Daegu", country="South Korea", latitude=35.8714, longitude=128.6014),
    )
    labels = json.loads(
        (ROOT / "evaluation/matching_spike/chatgpt_assessments.json").read_text()
    )["assessments"]
    output = {
        "scope": "4 recorded profiles + 2 synthetic controls, 5 cities; no fresh PDF extraction or LLM calls; earlier model labels are weak regression references, not clinical ground truth",
        "invariants": invariants(),
        "cases": [],
    }
    with sqlite3.connect(SNAPSHOT) as db:
        for profile in profiles:
            t = time.perf_counter()
            screening = screen_trials(db, profile, features)
            lookup = {p["nct_id"]: p for p in screening.landscape}
            candidates = {c.nct_id: c for c in screening.candidates}
            known = [r for r in labels if r["case_id"] == profile["case_id"]]
            positives = {r["nct_id"] for r in known if r["match_class"] == "candidate"}
            conflicts = {r["nct_id"] for r in known if r["match_class"] == "conflict"}
            case = {
                "case_id": profile["case_id"],
                "screen_seconds": round(time.perf_counter() - t, 3),
                "studies": screening.total_screened,
                "candidate_pool": len(candidates),
                "previous_candidate_references": sorted(positives),
                "previous_conflict_references": sorted(conflicts),
                "missing_reference_candidates_at_retrieval": sorted(
                    positives - candidates.keys()
                ),
                "cities": [],
            }
            case["high_score_low_coverage_before"] = sum(
                (p["clinical_score"] or 0) >= 80
                and p["clinical_assessment"]["coverage"] <= 0.45
                for p in screening.landscape
            )
            case["high_score_low_coverage_after"] = sum(
                (fixed_support(p["clinical_assessment"]) or 0) >= 80
                and p["clinical_assessment"]["coverage"] <= 0.45
                for p in screening.landscape
            )
            for city in cities:
                attach_screening_geography(db, screening.landscape, Location(**city))
                rows = [
                    {
                        "nct_id": nct,
                        "assessment": lookup[nct]["clinical_assessment"],
                        "support": fixed_support(lookup[nct]["clinical_assessment"]),
                        "old": lookup[nct]["clinical_score"],
                        "coverage": lookup[nct]["clinical_assessment"]["coverage"],
                        "exact": c.exact_variant_hits,
                        "retrieval": c.preliminary_score,
                        "geo": lookup[nct]["geography_score"],
                        "domestic": lookup[nct]
                        .get("geography_access", {})
                        .get("travel_context")
                        == "domestic",
                        "negative_profile": not any(
                            profile["biomarkers"].get(k)
                            for k in ("snv_indel", "copy_number", "fusions")
                        ),
                    }
                    for nct, c in candidates.items()
                ]
                baseline = sorted(
                    rows,
                    key=lambda r: (
                        -(r["old"] * r["coverage"] if r["old"] is not None else -1),
                        -(r["old"] if r["old"] is not None else -1),
                        -len(r["exact"]),
                        -r["retrieval"],
                        r["nct_id"],
                    ),
                )[:20]
                proposal = select(rows)
                old_ids, new_ids = (
                    {r["nct_id"] for r in baseline},
                    {r["nct_id"] for r in proposal},
                )
                assert len(new_ids) == len(proposal) <= 20
                replacement = select(rows, excluded=new_ids)
                assert not new_ids.intersection(r["nct_id"] for r in replacement)
                remaining = [
                    r
                    for r in rows
                    if r["nct_id"] not in new_ids and r["support"] is not None
                ]
                city_result = {
                    "city": city["city"],
                    "old_ids": sorted(old_ids),
                    "proposed_ids": sorted(new_ids),
                    "old_domestic": sum(r["domestic"] for r in baseline),
                    "proposed_domestic": sum(r["domestic"] for r in proposal),
                    "old_reference_candidates_selected": sorted(positives & old_ids),
                    "proposed_reference_candidates_selected": sorted(
                        positives & new_ids
                    ),
                    "old_reference_conflicts_selected": sorted(conflicts & old_ids),
                    "proposed_reference_conflicts_selected": sorted(
                        conflicts & new_ids
                    ),
                    "reference_candidates_still_unreviewed": sorted(
                        positives - new_ids
                    ),
                    "remaining_scored_candidates": len(remaining),
                    "rmc9805_before": "NCT06040541" in old_ids,
                    "rmc9805_after": "NCT06040541" in new_ids,
                    "refill_without_duplicate_or_excluded": True,
                }
                if (
                    profile["case_id"].startswith("synthetic-cholangiocarcinoma")
                    and city["city"] == "Daegu"
                ):
                    city_result["new_domestic_leads"] = [
                        {
                            "nct_id": r["nct_id"],
                            "title": lookup[r["nct_id"]]["title"],
                            "support": r["support"],
                            "geo": r["geo"],
                        }
                        for r in proposal
                        if r["domestic"] and r["nct_id"] not in old_ids
                    ]
                case["cities"].append(city_result)
            output["cases"].append(case)
    output["elapsed_seconds"] = round(time.perf_counter() - start, 3)
    return output


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
