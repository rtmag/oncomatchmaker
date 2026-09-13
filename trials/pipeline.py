import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pydantic import ValidationError

from evidence.actionability import find_approved_options
from schemas.match_results import ExploratoryTrial, MatchResults, RankedTrial
from trials.astra_runner import AstraExpertRunner, ExpertTeamError
from trials.candidate_retrieval import _terms, screen_trials
from trials.client import ClinicalTrialsClient, TrialServiceError
from trials.clinical_scoring import aggregate
from trials.eligibility import evaluate_eligibility
from trials.geography import (
    find_accessible_site,
    find_nearest_site,
    geographic_access,
    haversine_distance,
    resolve_city_location,
)
from trials.integrated_pipeline import _trial
from trials.ranking import score_trial
from trials.registry_features import load as load_features
from trials.review_selection import select_for_review
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
ASSESSMENT_FRACTIONS = {"support": 0.9, "caution": 0.6}


def attach_screening_geography(db, landscape, location):
    """One pass over explicitly open sites, preserving missing access as unknown."""
    access_sites = {}
    for nct_id, lat, lon, country in db.execute("""
        SELECT s.nct_id,s.latitude,s.longitude,s.country FROM sites s
        JOIN studies t ON t.nct_id=s.nct_id
        WHERE s.status='RECRUITING' AND t.overall_status='RECRUITING'
        AND s.latitude BETWEEN -90 AND 90 AND s.longitude BETWEEN -180 AND 180
    """):
        distance = haversine_distance(location.latitude, location.longitude, lat, lon)
        distance = round(distance, 1)
        access = geographic_access(distance, location.country, country)
        key = (-access["score"], distance)
        if nct_id not in access_sites or key < access_sites[nct_id][0]:
            access_sites[nct_id] = (key, distance, access)
    for point in landscape:
        selected = access_sites.get(point["nct_id"])
        if selected is not None:
            _, distance, access = selected
            point.update(
                distance_km=round(distance, 1),
                geography_score=access["score"],
                geography_access=access,
            )


def _clinical_score(team):
    components = {
        ROLE_COMPONENTS[row["expert_role"]]: ASSESSMENT_FRACTIONS.get(row["assessment"])
        for row in team["assessments"]
    }
    hard_conflict = bool(team["consensus"]["safety_gate_triggered_by"])
    from schemas.match_results import TrialScore

    return TrialScore(
        **aggregate(components, conflict=hard_conflict),
        rationale=[row["reasoning_summary"] for row in team["assessments"]],
    )


def _evaluated_trial(profile, location, candidate, record, team):
    raw = json.loads(record["raw_json"])
    raw["_retrieved_at"] = record["retrieved_at"]
    raw["_cached"] = True
    trial = parse_trial(raw)
    eligibility = evaluate_eligibility(profile, trial)
    nearest = (
        find_nearest_site(location, trial.sites)
        if trial.status == "RECRUITING"
        else None
    )
    accessible, access = (
        find_accessible_site(location, trial.sites)
        if trial.status == "RECRUITING"
        else (None, None)
    )
    geography_score = access["score"] if access else None
    match = _clinical_score(team)
    match.rationale.insert(
        0, f"Preliminary local screening score: {candidate.preliminary_score:.1f}."
    )
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
    return RankedTrial(
        trial=trial,
        match=match,
        eligibility=eligibility,
        nearest_site=nearest,
        geography_score=geography_score,
        accessible_site=accessible,
        geography_access=access or {},
        geography_availability=(
            "confirmed_recruiting_site" if nearest else "no_confirmed_open_site"
        ),
        expert_assessments=team["assessments"],
        consensus=team["consensus"],
        category=category,
        retrieval_route=candidate.retrieval_route,
    )


def _match_snapshot(
    profile,
    *,
    database,
    astra_runner,
    minimum_reviews,
    maximum_reviews,
    target_candidates,
    team_concurrency,
):
    if not 1 <= minimum_reviews <= maximum_reviews <= 20:
        raise ValueError(
            "ASTRA review limits must satisfy 1 <= minimum <= maximum <= 20."
        )
    if not 1 <= target_candidates <= maximum_reviews:
        raise ValueError("Target candidates must be between 1 and the review maximum.")
    if not 1 <= team_concurrency <= 3:
        raise ValueError("Team concurrency must be between 1 and 3.")
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
            "Geographic access uses a same-country travel heuristic, not actual journey time, language compatibility, visa eligibility or cost. The highest-access site may not be the nearest site.",
        ]
    )
    with sqlite3.connect(database) as db:
        features = load_features(database)
        screening = screen_trials(db, result.profile.model_dump(mode="json"), features)
        result.screening_landscape = [dict(row) for row in screening.landscape]
        attach_screening_geography(db, result.screening_landscape, location)
        candidates = select_for_review(
            screening.candidates,
            result.screening_landscape,
            maximum_reviews,
            molecular_required=bool(_terms(result.profile.model_dump(mode="json"))[1]),
        )
        result.warnings.append(
            "Clinical-fit v3 sums supported dimension points on a fixed 100-point scale. Unknown dimensions add no supported points; inspect coverage and bounds. Provisional and expert scores share arithmetic, not validated reliability. Review allocation considers clinical support and geographic access separately."
        )
        if not features:
            result.warnings.append(
                "Registry features unavailable: unreviewed trials remain unscored. Rebuild snapshot features before provisional scoring."
            )
        result.screening_summary = {
            "total_snapshot_trials_screened": screening.total_screened,
            "status_eligible": screening.status_eligible,
            "disease_eligible": screening.disease_eligible,
            "preliminary_ranked_pool": len(screening.candidates),
        }
        result.queries = [
            {
                "nct_id": candidate.nct_id,
                "disease": ", ".join(candidate.matched_disease_terms),
                "term": ", ".join(candidate.matched_molecular_terms),
            }
            for candidate in candidates
        ]
        records = [
            (candidate, _trial(db, candidate.nct_id)) for candidate in candidates
        ]
        # Unreviewed cross-disease text leads are never scored or plotted as matches.
        for lead in screening.exploratory[:12]:
            record = _trial(db, lead.nct_id)
            raw = json.loads(record["raw_json"])
            raw.update(_retrieved_at=record["retrieved_at"], _cached=True)
            result.exploratory_trials.append(
                ExploratoryTrial(
                    trial=parse_trial(raw),
                    matched_variants=list(lead.exact_variant_hits),
                )
            )
        result.screening_summary["exploratory_other_disease_leads"] = len(
            screening.exploratory
        )

    profile_payload = result.profile.model_dump(mode="json")
    points_by_id = {point["nct_id"]: point for point in result.screening_landscape}
    reviewed = accepted = 0
    for start in range(0, len(records), team_concurrency):
        batch = records[start : start + team_concurrency]
        with ThreadPoolExecutor(max_workers=len(batch)) as pool:
            futures = {
                pool.submit(astra_runner.run_team, profile_payload, record, []): (
                    candidate,
                    record,
                )
                for candidate, record in batch
            }
            for future in as_completed(futures):
                candidate, record = futures[future]
                reviewed += 1
                try:
                    team = future.result()
                except ExpertTeamError:
                    point = points_by_id[candidate.nct_id]
                    point["provisional_clinical_assessment"] = point[
                        "clinical_assessment"
                    ]
                    point["clinical_score"] = None
                    point["clinical_assessment"] = {
                        **point["clinical_assessment"],
                        "overall_score": None,
                        "status": "review_failed",
                    }
                    result.warnings.append(
                        f"{candidate.nct_id}: ASTRA team failed validation; no partial assessment was accepted."
                    )
                    continue
                row = _evaluated_trial(
                    result.profile, location, candidate, record, team
                )
                result.trials.append(row)
                point = points_by_id[candidate.nct_id]
                point["provisional_clinical_assessment"] = point["clinical_assessment"]
                point["clinical_score"] = row.match.overall_score
                point["clinical_assessment"] = {
                    **row.match.model_dump(mode="json"),
                    "status": "excluded"
                    if row.category == "excluded"
                    else "expert_reviewed",
                }
                if row.category != "excluded" and row.match.overall_score is not None:
                    accepted += 1
        if reviewed >= minimum_reviews and accepted >= target_candidates:
            break
    result.screening_summary["astra_reviewed"] = reviewed
    result.screening_summary["non_conflicting_candidates"] = accepted
    result.trials.sort(
        key=lambda row: (
            row.category == "excluded",
            -(row.match.overall_score or -1),
            -(row.geography_score or -1),
            row.trial.nct_id,
        )
    )
    result.search_status = "complete" if accepted >= target_candidates else "partial"
    if candidates and accepted < target_candidates:
        result.warnings.append(
            f"ASTRA found {accepted} non-conflicting candidate(s) after reviewing {reviewed}; no additional recommendation was manufactured."
        )
    if not result.trials:
        result.warnings.append(
            "No local molecular-and-disease candidates were retrieved; this is not evidence that no appropriate trial exists."
        )
    return result


def match_patient(
    profile,
    *,
    client=None,
    database=None,
    astra_runner=None,
    max_candidates=None,
    minimum_reviews=None,
    target_candidates=None,
    team_concurrency=None,
):
    if client is None:
        owned_runner = astra_runner is None
        runner = astra_runner or AstraExpertRunner()
        try:
            return _match_snapshot(
                profile,
                database=Path(database or SNAPSHOT),
                astra_runner=runner,
                minimum_reviews=(
                    max_candidates
                    if max_candidates is not None
                    else minimum_reviews
                    or int(os.environ.get("ONCOMATCH_ASTRA_MIN_REVIEWS", "12"))
                ),
                maximum_reviews=(
                    max_candidates
                    if max_candidates is not None
                    else int(os.environ.get("ONCOMATCH_ASTRA_MAX_REVIEWS", "20"))
                ),
                target_candidates=target_candidates
                or int(os.environ.get("ONCOMATCH_TARGET_CANDIDATES", "5")),
                team_concurrency=team_concurrency
                or int(os.environ.get("ONCOMATCH_TEAM_CONCURRENCY", "3")),
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
