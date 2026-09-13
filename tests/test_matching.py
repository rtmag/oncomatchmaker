from copy import deepcopy

import pytest
from pydantic import ValidationError

from evidence.actionability import find_approved_options
from schemas.molecular_profile import Location, MolecularProfile
from trials.client import TrialServiceError
from trials.eligibility import evaluate_eligibility
from trials.geography import find_nearest_site, haversine_distance
from trials.pipeline import _clinical_score, match_patient
from trials.ranking import score_trial
from trials.search import generate_queries


def test_profile_contract_and_unknowns(profile):
    assert MolecularProfile.model_validate_json(profile.model_dump_json()) == profile
    assert profile.patient_context.ecog is None
    assert not profile.patient_context.prior_therapies_known
    with pytest.raises(ValidationError):
        Location(latitude=1)
    with pytest.raises(ValidationError):
        Location(latitude=91, longitude=0)
    with pytest.raises(ValidationError):
        Location(latitude=float("nan"), longitude=0)


@pytest.mark.parametrize(
    "field,value",
    [("classification", "VUS"), ("classification", None), ("potential_ch", True)],
)
def test_no_target_from_vus_ch_unknown(profile, field, value):
    setattr(profile.biomarkers.snv_indel[0], field, value)
    assert generate_queries(profile) == [
        {"disease": "non-small cell lung cancer", "term": ""}
    ]
    assert find_approved_options(profile) == []


def test_queries_and_evidence(profile):
    queries = generate_queries(profile)
    assert len(queries) == 3
    option = find_approved_options(profile)[0]
    assert option.context == "same_disease"
    assert option.sources and option.restrictions
    profile.disease.normalized = "colorectal cancer"
    assert find_approved_options(profile)[0].context == "other_disease"


def test_unknown_eligibility_not_filled(profile, trial):
    result = evaluate_eligibility(profile, trial)
    assert result.status == "POSSIBLE_MATCH"
    assert any("ECOG" in c.criterion and c.status == "UNKNOWN" for c in result.criteria)
    assert any(
        "Prior" in c.criterion and c.status == "UNKNOWN" for c in result.criteria
    )
    profile.patient_context.age = 12
    assert evaluate_eligibility(profile, trial).status == "LIKELY_NOT_ELIGIBLE"


def test_unparsed_ages_are_unknown(profile, trial):
    trial.minimum_age = "18 Months"
    assert evaluate_eligibility(profile, trial).criteria[0].status == "UNKNOWN"


def test_geography_recruitment_and_missing(profile, trial):
    nearest = find_nearest_site(profile.patient_context.location, trial.sites)
    assert nearest.site.name == "Synthetic active site"
    assert 0 < nearest.distance_km < 1
    assert find_nearest_site(Location(), trial.sites) is None
    trial.sites[0].status = "UNKNOWN"
    assert find_nearest_site(profile.patient_context.location, trial.sites) is None
    assert haversine_distance(0, 0, 0, 1) == pytest.approx(111.195, abs=0.01)
    assert haversine_distance(0, 0, 0, 0) == 0


def test_score_relevance_and_coverage(profile, trial):
    eligibility = evaluate_eligibility(profile, trial)
    exact = score_trial(profile, trial, eligibility)
    trial.title = "KRAS inhibitor"
    gene = score_trial(profile, trial, eligibility)
    assert exact.components["molecular"] > gene.components["molecular"]
    assert exact.components["geography"] is None
    assert 0 < exact.coverage < 1
    assert exact.overall_score == round(
        sum(v or 0 for v in exact.components.values()), 2
    )
    trial.title = "KRAS G12D"
    assert score_trial(profile, trial, eligibility).components["molecular"] == 20
    with pytest.raises(ValueError):
        score_trial(profile, trial, eligibility, weights={"molecular": -1})


class FakeClient:
    def __init__(self, records=None, fail=False):
        self.records = records or []
        self.warnings = []
        self.fail = fail

    def search_trials(self, **query):
        if self.fail:
            raise TrialServiceError("unavailable")
        return deepcopy(self.records)


def test_pipeline_dedup_exclusions_and_disease_review(profile, record):
    other = deepcopy(record)
    other["protocolSection"]["identificationModule"]["nctId"] = "NCT00000002"
    other["protocolSection"]["conditionsModule"]["conditions"] = ["Melanoma"]
    result = match_patient(profile, client=FakeClient([record, other, record]))
    assert len(result.trials) == 2
    assert [t.category for t in result.trials] == ["recruiting", "review"]
    profile.patient_context.age = 12
    result = match_patient(profile, client=FakeClient([record]))
    assert result.trials[0].category == "excluded"


def test_failures_not_empty_success(profile, record):
    assert match_patient(profile, client=FakeClient()).search_status == "complete"
    assert (
        match_patient(profile, client=FakeClient(fail=True)).search_status == "failed"
    )
    partial = match_patient(
        profile, client=FakeClient([record, {}, {"protocolSection": None}])
    )
    assert partial.search_status == "partial"
    assert len(partial.trials) == 1
    profile.disease.normalized = None
    profile.disease.raw_text = ""
    assert match_patient(profile, client=FakeClient()).search_status == "not_searched"


def test_recorded_real_response(profile, recorded_response):
    records = [
        {**s, "_retrieved_at": "2026-09-13T00:00:00+00:00", "_cached": True}
        for s in recorded_response["studies"]
    ]
    result = match_patient(profile, client=FakeClient(records))
    assert len(result.trials) == len(records)
    assert all(t.trial.cached and t.trial.sources for t in result.trials)


def test_hard_conflict_is_unscored_not_zero():
    roles = [
        "molecular_profile_qc",
        "disease_oncology",
        "actionability_evidence",
        "pathway_resistance",
        "trial_eligibility",
        "safety_critic",
    ]
    team = {
        "assessments": [
            {
                "expert_role": role,
                "assessment": "conflict" if role == "safety_critic" else "support",
                "reasoning_summary": "Test assessment.",
            }
            for role in roles
        ],
        "consensus": {"safety_gate_triggered_by": ["safety_critic"]},
    }
    assert _clinical_score(team).overall_score is None
