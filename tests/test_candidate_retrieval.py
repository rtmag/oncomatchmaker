import sqlite3
from pathlib import Path

import pytest

from schemas.molecular_profile import Location
from trials.candidate_retrieval import retrieve_candidates, screen_trials
from trials.pipeline import attach_screening_geography


def _kras_profile(disease="Cholangiocarcinoma"):
    return {
        "disease": {"raw_text": disease},
        "biomarkers": {"snv_indel": [{"gene": "KRAS", "protein_change": "G12D"}]},
    }


def test_baskets_and_other_disease_leads_remain_separate():
    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE studies(nct_id,title,eligibility_text,conditions_json,overall_status)"
    )
    db.executemany(
        "INSERT INTO studies VALUES(?,?,?,?,?)",
        [
            (
                "NCT00000001",
                "KRAS G12D solid tumors",
                "Inclusion Criteria: Solid tumors with KRAS G12D",
                '["Solid Tumor"]',
                "RECRUITING",
            ),
            (
                "NCT00000002",
                "KRAS G12D pancreatic cancer",
                "Inclusion Criteria: Pancreatic cancer only",
                '["Solid Tumor"]',
                "RECRUITING",
            ),
            (
                "NCT00000003",
                "KRAS G12C solid tumors",
                "Inclusion Criteria: G12C. Exclusion Criteria: G12D",
                '["Solid Tumor"]',
                "RECRUITING",
            ),
            (
                "NCT00000004",
                "KRAS G12D solid tumors",
                "",
                '["Solid Tumor"]',
                "COMPLETED",
            ),
        ],
    )
    result = screen_trials(db, _kras_profile())
    assert result.candidates[0].nct_id == "NCT00000001"
    assert result.candidates[0].retrieval_route == "solid_tumor_basket"
    assert result.candidates[0].exact_variant_hits == ("G12D",)
    assert [r.nct_id for r in result.exploratory] == ["NCT00000002"]
    wrong_allele = next(r for r in result.candidates if r.nct_id == "NCT00000003")
    assert (
        wrong_allele.exact_variant_hits == ()
    )  # No exact-match prioritization from exclusions.
    assert all(r.nct_id != "NCT00000004" for r in result.candidates)
    assert not screen_trials(db, _kras_profile("Acute myeloid leukemia")).candidates
    assert not screen_trials(db, _kras_profile("unknown")).candidates
    profile = _kras_profile()
    profile["biomarkers"]["snv_indel"][0]["report_category"] = "VUS"
    assert not screen_trials(db, profile).candidates
    assert not screen_trials(db, profile).exploratory


def test_snapshot_retrieves_rmc9805_for_cholangiocarcinoma():
    path = Path(__file__).parents[1] / "data/snapshots/2026-09-13-v1/oncology.sqlite"
    if not path.exists():
        pytest.skip("Local registry snapshot unavailable")
    with sqlite3.connect(path) as db:
        result = screen_trials(db, _kras_profile())
    candidate = next(r for r in result.candidates[:20] if r.nct_id == "NCT06040541")
    assert candidate.retrieval_route == "solid_tumor_basket"
    assert candidate.exact_variant_hits == ("G12D",)
    assert len(result.landscape) == result.total_screened


@pytest.mark.parametrize("fail", [False, True])
def test_snapshot_pipeline_keeps_exploratory_leads_unscored(profile, fail):
    from schemas.astra_contracts import EXPERT_ROLES
    from schemas.match_results import MatchResults
    from trials.pipeline import SNAPSHOT, match_patient

    if not SNAPSHOT.exists():
        pytest.skip("Local registry snapshot unavailable")
    profile.disease.raw_text = "Cholangiocarcinoma"
    profile.disease.normalized = "cholangiocarcinoma"
    profile.disease.synonyms = []
    profile.biomarkers.snv_indel[0].protein_change = "G12D"

    class StubTeam:
        def run_team(self, profile, record, evidence):
            if fail:
                from trials.astra_runner import ExpertTeamError

                raise ExpertTeamError("Synthetic failure")
            return {
                "assessments": [
                    {
                        "expert_role": role,
                        "assessment": "caution",
                        "reasoning_summary": "Synthetic test: cohort confirmation required.",
                    }
                    for role in EXPERT_ROLES
                ],
                "consensus": {
                    "disposition": "needs_review",
                    "safety_gate_triggered_by": [],
                },
            }

    result = match_patient(
        profile, astra_runner=StubTeam(), max_candidates=3, target_candidates=1
    )
    if fail:
        assert not result.trials
        failures = [
            p
            for p in result.screening_landscape
            if p["clinical_assessment"]["status"] == "review_failed"
        ]
        assert len(failures) == 3
        assert all(
            p["clinical_score"] is None
            and p["clinical_assessment"]["overall_score"] is None
            for p in failures
        )
        return
    # A three-review smoke budget is not a fixed trial-ID ordering guarantee.
    # The full twenty-review basket regression is checked separately.
    assert len(result.trials) == 3
    for trial in result.trials:
        point = next(
            p for p in result.screening_landscape if p["nct_id"] == trial.trial.nct_id
        )
        assert point["clinical_score"] == trial.match.overall_score
        assert point["clinical_assessment"]["coverage"] == trial.match.coverage
        assert "provisional_clinical_assessment" in point
    assert result.exploratory_trials
    assert all(not r.expert_reviewed for r in result.exploratory_trials)
    assert not (
        {r.trial.nct_id for r in result.trials}
        & {r.trial.nct_id for r in result.exploratory_trials}
    )
    payload = result.model_dump(mode="json")
    assert all(
        "match" not in r and "geography_score" not in r
        for r in payload["exploratory_trials"]
    )
    assert MatchResults.model_validate(payload) == result


def test_review_continues_after_failure_and_hard_conflict(profile):
    from schemas.astra_contracts import EXPERT_ROLES
    from trials.astra_runner import ExpertTeamError
    from trials.pipeline import SNAPSHOT, _match_snapshot

    if not SNAPSHOT.exists():
        pytest.skip("Local registry snapshot unavailable")

    class SequencedTeam:
        calls = []

        def run_team(self, profile, record, evidence):
            self.calls.append(record["nct_id"])
            if len(self.calls) == 1:
                raise ExpertTeamError("Synthetic validation failure")
            conflict = len(self.calls) == 2
            return {
                "assessments": [
                    {
                        "expert_role": role,
                        "assessment": "caution",
                        "reasoning_summary": "Synthetic regression only",
                    }
                    for role in EXPERT_ROLES
                ],
                "consensus": {
                    "disposition": "conflict" if conflict else "needs_review",
                    "safety_gate_triggered_by": ["safety_critic"] if conflict else [],
                },
            }

    runner = SequencedTeam()
    result = _match_snapshot(
        profile,
        database=SNAPSHOT,
        astra_runner=runner,
        minimum_reviews=1,
        maximum_reviews=3,
        target_candidates=1,
        team_concurrency=1,
    )
    assert len(set(runner.calls)) == 3
    assert result.screening_summary["non_conflicting_candidates"] == 1
    points = {p["nct_id"]: p for p in result.screening_landscape}
    assert points[runner.calls[0]]["clinical_score"] is None
    assert points[runner.calls[1]]["clinical_score"] is None
    assert points[runner.calls[2]]["clinical_score"] == 60


def test_landscape_uses_only_open_studies_and_open_sites():
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE studies(nct_id TEXT, overall_status TEXT);
        CREATE TABLE sites(nct_id TEXT,status TEXT,latitude REAL,longitude REAL,country TEXT);
        INSERT INTO studies VALUES ('A','RECRUITING'),('B','NOT_YET_RECRUITING'),('C','RECRUITING');
        INSERT INTO sites VALUES ('A','ACTIVE_NOT_RECRUITING',0,0,NULL),('A','RECRUITING',0,1,NULL),
        ('B','RECRUITING',0,0,NULL),('C','UNKNOWN',0,0,NULL),('C','RECRUITING',NULL,NULL,NULL);
    """)
    points = [dict(nct_id=n, distance_km=None, geography_score=None) for n in "ABC"]
    attach_screening_geography(db, points, Location(latitude=0, longitude=0))
    assert 111 < points[0]["distance_km"] < 112
    assert 0 < points[0]["geography_score"] < 100
    assert all(
        row["distance_km"] is None and row["geography_score"] is None
        for row in points[1:]
    )


def test_retrieval_requires_disease_and_molecular_hit():
    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE studies(nct_id TEXT,title TEXT,eligibility_text TEXT,conditions_json TEXT,overall_status TEXT)"
    )
    db.executemany(
        "INSERT INTO studies VALUES(?,?,?,?,?)",
        [
            ("NCT00000001", "EGFR study", "Requires L858R", '["NSCLC"]', "RECRUITING"),
            (
                "NCT00000002",
                "EGFR study",
                "Requires L858R",
                '["Melanoma"]',
                "RECRUITING",
            ),
            ("NCT00000003", "EGFR study", "Requires L858R", '["NSCLC"]', "COMPLETED"),
        ],
    )
    profile = {
        "disease": {"raw_text": "NSCLC", "normalized": "NSCLC", "synonyms": []},
        "biomarkers": {"snv_indel": [{"gene": "EGFR", "protein_change": "L858R"}]},
    }
    assert [row.nct_id for row in retrieve_candidates(db, profile)] == ["NCT00000001"]
    screened = screen_trials(db, profile)
    assert screened.total_screened == 3
    assert screened.status_eligible == 2
    assert len(screened.candidates) == 1
    assert screened.candidates[0].preliminary_score > 0
    assert len(screened.landscape) == 3
    assert len({row["nct_id"] for row in screened.landscape}) == 3
    assert (
        screened.landscape[0]["preliminary_score"]
        == screened.candidates[0].preliminary_score
    )
    assert screened.landscape[1]["screening_state"] == "disease_not_retrieved"
    assert screened.landscape[2]["preliminary_score"] == 0
    assert all(row["geography_score"] is None for row in screened.landscape)

    profile["biomarkers"] = {"snv_indel": [], "copy_number": [], "fusions": []}
    assert [row.nct_id for row in retrieve_candidates(db, profile)] == ["NCT00000001"]


def test_unknown_location_does_not_query_or_assign_geography():
    # No site tables needed: clinical-only matching should skip the geographic pass.
    db = sqlite3.connect(":memory:")
    points = [{"nct_id": "NCT1", "distance_km": None, "geography_score": None}]
    attach_screening_geography(db, points, Location())
    assert points[0]["distance_km"] is None
    assert points[0]["geography_score"] is None


def test_snapshot_matching_without_location_keeps_clinical_scores(profile, monkeypatch):
    from schemas.astra_contracts import EXPERT_ROLES
    from trials import pipeline

    if not pipeline.SNAPSHOT.exists():
        pytest.skip("Local registry snapshot unavailable")
    profile.patient_context.location = Location()
    profile.patient_context.ecog = None
    profile.patient_context.prior_therapies = []
    profile.patient_context.prior_therapies_known = False

    def forbidden_lookup(*args, **kwargs):
        raise AssertionError("Blank optional location must not call a geocoder")

    monkeypatch.setattr(pipeline, "resolve_city_location", forbidden_lookup)

    class Team:
        def run_team(self, payload, record, evidence):
            assert payload["patient_context"]["ecog"] is None
            assert payload["patient_context"]["prior_therapies_known"] is False
            return {
                "assessments": [
                    {
                        "expert_role": role,
                        "assessment": "caution",
                        "reasoning_summary": "Synthetic test",
                    }
                    for role in EXPERT_ROLES
                ],
                "consensus": {
                    "disposition": "needs_review",
                    "safety_gate_triggered_by": [],
                },
            }

    result = pipeline.match_patient(
        profile, astra_runner=Team(), max_candidates=1, target_candidates=1
    )
    assert result.trials
    assert result.trials[0].match.overall_score is not None
    assert all(
        t.geography_score is None and t.nearest_site is None for t in result.trials
    )
    assert all(p["geography_score"] is None for p in result.screening_landscape)
