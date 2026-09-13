import json
from pathlib import Path

from schemas.integrated_results import IntegratedCaseResult

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evaluation" / "demo_fixtures"


def test_four_golden_fixtures_obey_demo_safety_contracts():
    paths = sorted(FIXTURES.glob("*.json"))
    golden = [path for path in paths if path.name != "negative-report-safety.json"]
    assert len(golden) == 4
    cases = [
        IntegratedCaseResult.model_validate_json(path.read_text()) for path in golden
    ]
    assert sum(len(case.trials) for case in cases) == 12
    for case in cases:
        assert case.source_report.ingestion_mode == "recorded_public_sample_profile"
        for trial in case.trials:
            assert trial.source_url.startswith("https://clinicaltrials.gov/study/NCT")
            assert trial.registry_last_update
            assert trial.consensus.eligibility_state == "not_determined"
            assert not any(
                term in str(trial.clinical_score.model_dump()).casefold()
                for term in ("distance", "country", "geography", "site_status")
            )
            if trial.nearest_open_site:
                assert trial.overall_status == "RECRUITING"
                assert trial.nearest_open_site.study_status == "RECRUITING"
                assert trial.nearest_open_site.site_status == "RECRUITING"
            if trial.consensus.disposition == "conflict":
                assert not trial.clinical_score.rankable
                assert trial.clinical_score.composite_score is None
                assert trial.plot_position.plot_status == "not_plottable"


def test_negative_demo_invents_no_target_or_trial_result():
    result = json.loads((FIXTURES / "negative-report-safety.json").read_text())
    assert result["reportable_pathogenic_targets"] == []
    assert result["trial_result_status"] == "not_yet_evaluated"
    assert result["msi_status"] == "not_detected"
