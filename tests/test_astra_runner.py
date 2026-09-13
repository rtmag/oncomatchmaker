import json
import threading

import httpx
import pytest

from schemas.astra_contracts import EXPERT_ROLES
from trials.astra_runner import AstraExpertRunner, ExpertTeamError


def profile():
    return {
        "schema_version": "0.3",
        "report": {"vendor": "Test", "assay": "Test", "sample_type": "tissue"},
        "disease": {"raw_text": "NSCLC", "normalized": "non-small cell lung cancer"},
        "patient_context": {},
        "biomarkers": {"snv_indel": [{"gene": "EGFR"}]},
    }


def trial():
    return {
        "nct_id": "NCT00000001",
        "title": "Test",
        "overall_status": "RECRUITING",
        "eligibility_text": "EGFR L858R",
        "source_url": "https://clinicaltrials.gov/study/NCT00000001",
    }


def response_for(request, *, status="completed", mismatch=False):
    payload = json.loads(request.content)
    assert payload["model"] == "gpt-6-astra"
    assert payload["reasoning"] == {"effort": "medium"}
    assert payload["store"] is False
    assert "previous_response_id" not in payload and "conversation" not in payload
    assert payload["text"]["format"]["strict"] is True
    role = payload["metadata"]["expert_role"]
    assessment = {
        "trial_id": "NCT99999999" if mismatch else "NCT00000001",
        "expert_role": role,
        "assessment": "caution",
        "confidence": 0.8,
        "relationships": ["direct_variant"],
        "supporting_facts": ["EGFR L858R"],
        "conflicting_facts": [],
        "missing_information": ["ECOG"],
        "evidence_references": ["https://clinicaltrials.gov/study/NCT00000001"],
        "reasoning_summary": "Requires clinical review.",
    }
    return httpx.Response(
        200,
        json={
            "id": "resp_" + role,
            "status": status,
            "model": "gpt-6-astra",
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": json.dumps(assessment)}
                    ],
                }
            ],
        },
    )


def test_six_experts_are_isolated_concurrent_and_provenanced():
    barrier = threading.Barrier(6, timeout=2)

    def handler(request):
        barrier.wait()
        return response_for(request)

    runner = AstraExpertRunner(
        api_key="test-only",
        http=httpx.Client(
            base_url="https://example.test", transport=httpx.MockTransport(handler)
        ),
    )
    result = runner.run_team(profile(), trial(), [])
    assert [row["expert_role"] for row in result["assessments"]] == list(EXPERT_ROLES)
    assert result["execution"] == "concurrent_isolated_responses"
    assert all(row["execution"]["status"] == "live" for row in result["assessments"])
    assert all(row["execution"]["total_tokens"] == 15 for row in result["assessments"])
    assert result["consensus"]["eligibility_state"] == "not_determined"


@pytest.mark.parametrize("failure", ["incomplete", "mismatch"])
def test_any_bad_agent_fails_the_entire_team(failure):
    def handler(request):
        return response_for(
            request,
            status="incomplete" if failure == "incomplete" else "completed",
            mismatch=failure == "mismatch",
        )

    runner = AstraExpertRunner(
        api_key="test-only",
        http=httpx.Client(
            base_url="https://example.test", transport=httpx.MockTransport(handler)
        ),
    )
    with pytest.raises(ExpertTeamError):
        runner.run_team(profile(), trial(), [])


def test_missing_server_key_fails_closed(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ExpertTeamError, match="not configured"):
        AstraExpertRunner()
