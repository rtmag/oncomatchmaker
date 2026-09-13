import json
import math
import os
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from evidence.actionability import find_approved_options
from schemas.match_results import MatchResults, RankedTrial
from trials.astra_runner import AstraExpertRunner
from trials.candidate_retrieval import retrieve_candidates
from trials.client import ClinicalTrialsClient, TrialServiceError
from trials.eligibility import evaluate_eligibility
from trials.geography import find_nearest_site, resolve_city_location
from trials.integrated_pipeline import _trial
from trials.ranking import score_trial
from trials.search import generate_queries
from trials.trial_parser import parse_trial

SNAPSHOT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "snapshots"
    / "2026-09-13-v1"
    / "oncology.sqlite"
)
ROLE_COMPONENTS = {
    "molecular_profile_qc": "molecular",
    "disease_oncology": "disease",
    "actionability_evidence": "evidence",
    "pathway_resistance": "mechanism",
    "trial_eligibility": "eligibility",
    "safety_critic": "safety",
}
CLINICAL_WEIGHTS = {
    "molecular": 30.0,
    "disease": 15.0,
    "evidence": 15.0,
    "mechanism": 15.0,
    "eligibility": 20.0,
    "safety": 5.0,
}
ASSESSMENT_FRACTIONS = {"support": 0.9, "caution": 0.6}


def _clinical_score(team):
    components = {
        ROLE_COMPONENTS[row["expert_role"]]: ASSESSMENT_FRACTIONS.get(row["assessment"])
        for row in team["assessments"]
    }
    known_weight = sum(
        CLINICAL_WEIGHTS[name]
        for name, value in components.items()
        if value is not None
    )
    hard_conflict = bool(team["consensus"]["safety_gate_triggered_by"])
    overall = (
        0.0
        if hard_conflict
        else sum(
            (value or 0) * CLINICAL_WEIGHTS[name] for name, value in components.items()
        )
    )
    from schemas.match_results import TrialScore

    return TrialScore(
        overall_score=round(overall, 1),
        coverage=round(known_weight / 100, 3),
        components=components,
        weights=CLINICAL_WEIGHTS,
        rationale=[row["reasoning_summary"] for row in team["assessments"]],
    )


def _match_snapshot(profile, *, database, astra_runner, max_candidates):
    result = MatchResults(
        profile=profile.model_copy(deep=True),
        approved_options=find_approved_options(profile),
    )
    location = result.profile.patient_context.location
    if location.latitude is None or location.longitude is None:
        resolved = resolve_city_location(location.city or "", location.country or "")
        result.profile.patient_context.location = resolved
        location = resolved
    result.warnings.extend(
        [
            "ASTRA ranks evidence for professional review; it does not determine eligibility or therapeutic benefit.",
            "Geography is scored separately and uses only sites explicitly marked RECRUITING in the registry snapshot.",
        ]
    )
    with sqlite3.connect(database) as db:
        candidates = retrieve_candidates(db, result.profile.model_dump(mode="json"))[
            :max_candidates
        ]
        result.queries = [
            {
                "nct_id": candidate.nct_id,
                "disease": ", ".join(candidate.matched_disease_terms),
                "term": ", ".join(candidate.matched_molecular_terms),
            }
            for candidate in candidates
        ]
        for candidate in candidates:
            record = _trial(db, candidate.nct_id)
            raw = json.loads(record["raw_json"])
            raw["_retrieved_at"] = record["retrieved_at"]
            raw["_cached"] = True
            trial = parse_trial(raw)
            team = astra_runner.run_team(
                result.profile.model_dump(mode="json"), record, []
            )
            eligibility = evaluate_eligibility(result.profile, trial)
            nearest = (
                find_nearest_site(location, trial.sites)
                if trial.status == "RECRUITING"
                else None
            )
            geography_score = (
                round(100 * math.exp(-nearest.distance_km / 250), 1)
                if nearest
                else None
            )
            match = _clinical_score(team)
            disposition = team["consensus"]["disposition"]
            category = (
                "excluded"
                if disposition == "conflict"
                else "recruiting"
                if trial.status == "RECRUITING"
                else "not_yet_recruiting"
                if trial.status == "NOT_YET_RECRUITING"
                else "review"
            )
            result.trials.append(
                RankedTrial(
                    trial=trial,
                    match=match,
                    eligibility=eligibility,
                    nearest_site=nearest,
                    geography_score=geography_score,
                    geography_availability=(
                        "confirmed_recruiting_site"
                        if nearest
                        else "no_confirmed_open_site"
                    ),
                    expert_assessments=team["assessments"],
                    consensus=team["consensus"],
                    category=category,
                )
            )
    result.trials.sort(
        key=lambda row: (
            row.category == "excluded",
            -row.match.overall_score,
            -(row.geography_score or -1),
            row.trial.nct_id,
        )
    )
    result.search_status = "complete"
    if not result.trials:
        result.warnings.append(
            "No local molecular-and-disease candidates were retrieved; this is not evidence that no appropriate trial exists."
        )
    return result


def match_patient(
    profile, *, client=None, database=None, astra_runner=None, max_candidates=None
):
    if client is None:
        owned_runner = astra_runner is None
        runner = astra_runner or AstraExpertRunner()
        try:
            return _match_snapshot(
                profile,
                database=Path(database or SNAPSHOT),
                astra_runner=runner,
                max_candidates=max_candidates
                or int(os.environ.get("ONCOMATCH_MAX_CANDIDATES", "3")),
            )
        finally:
            if owned_runner:
                runner.close()

    owned = client is None
    client = client or ClinicalTrialsClient()
    result = MatchResults(
        profile=profile,
        approved_options=find_approved_options(profile),
        queries=generate_queries(profile),
    )
    result.warnings.append(
        "Evidence coverage is limited to curated demo biomarkers; absent evidence does not mean no treatment exists."
    )
    seen, failures = set(), 0
    warning_start = len(client.warnings)
    try:
        for query in result.queries:
            try:
                records = client.search_trials(**query)
            except TrialServiceError as exc:
                failures += 1
                result.warnings.append(
                    f"Search failed ({query['disease']}, {query['term']}): {exc}"
                )
                continue
            for record in records:
                try:
                    trial = parse_trial(record)
                except (
                    AttributeError,
                    KeyError,
                    TypeError,
                    ValueError,
                    ValidationError,
                ):
                    result.warnings.append(
                        "Skipped malformed trial record; results are incomplete."
                    )
                    continue
                if trial.nct_id in seen:
                    continue
                seen.add(trial.nct_id)
                eligibility = evaluate_eligibility(profile, trial)
                nearest = find_nearest_site(
                    profile.patient_context.location, trial.sites
                )
                score = score_trial(profile, trial, eligibility, nearest)
                category = "review"
                if eligibility.status == "LIKELY_NOT_ELIGIBLE":
                    category = "excluded"
                elif score.components["disease"] is not None:
                    if trial.status == "RECRUITING":
                        category = "recruiting"
                    elif trial.status == "NOT_YET_RECRUITING":
                        category = "not_yet_recruiting"
                result.trials.append(
                    RankedTrial(
                        trial=trial,
                        match=score,
                        eligibility=eligibility,
                        nearest_site=nearest,
                        category=category,
                    )
                )
        result.warnings.extend(client.warnings[warning_start:])
    finally:
        if owned:
            client.close()
    result.trials.sort(
        key=lambda r: (
            {"recruiting": 0, "not_yet_recruiting": 1, "review": 2, "excluded": 3}[
                r.category
            ],
            -r.match.overall_score,
            r.trial.nct_id,
        )
    )
    result.search_status = (
        "not_searched"
        if not result.queries
        else "failed"
        if failures == len(result.queries)
        else "partial"
        if failures or len(result.warnings) > 1
        else "complete"
    )
    if not result.queries:
        result.warnings.append("Confirm a diagnosis before searching.")
    return result
