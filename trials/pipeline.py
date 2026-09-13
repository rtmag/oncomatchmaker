from pydantic import ValidationError

from evidence.actionability import find_approved_options
from schemas.match_results import MatchResults, RankedTrial
from trials.client import ClinicalTrialsClient, TrialServiceError
from trials.eligibility import evaluate_eligibility
from trials.geography import find_nearest_site
from trials.ranking import score_trial
from trials.search import generate_queries
from trials.trial_parser import parse_trial


def match_patient(profile, *, client=None):
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
