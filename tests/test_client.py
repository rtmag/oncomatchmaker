import os
from pathlib import Path

import httpx
import pytest

from schemas.molecular_profile import MolecularProfile
from trials.client import ClinicalTrialsClient, TrialServiceError
from trials.pipeline import match_patient


def make_client(handler, **kwargs):
    return ClinicalTrialsClient(
        http=httpx.Client(
            base_url="https://example.test", transport=httpx.MockTransport(handler)
        ),
        sleep=lambda _: None,
        **kwargs,
    )


def test_pagination_cache_and_timestamps(record):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.params.get("pageToken"):
            return httpx.Response(200, json={"studies": [record]})
        return httpx.Response(200, json={"studies": [record], "nextPageToken": "next"})

    client = make_client(handler)
    first = client.search_trials("NSCLC", "KRAS")
    second = client.search_trials("NSCLC", "KRAS")
    assert len(first) == 2 and len(calls) == 2
    assert all(s["_cached"] for s in second)
    assert first[0]["_retrieved_at"] == second[0]["_retrieved_at"]
    assert (
        calls[0].url.params["filter.overallStatus"] == "RECRUITING,NOT_YET_RECRUITING"
    )


@pytest.mark.parametrize("status", [429, 503])
def test_retry_bounded(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status)

    with pytest.raises(TrialServiceError):
        make_client(handler).search_trials("NSCLC")
    assert len(calls) == 3


def test_bad_payload():
    with pytest.raises(TrialServiceError):
        make_client(lambda _: httpx.Response(200, json={})).search_trials("NSCLC")
    with pytest.raises(TrialServiceError):
        make_client(lambda _: httpx.Response(200, text="not json")).search_trials(
            "NSCLC"
        )


def test_later_page_failure_keeps_partial_records(record):
    def handler(request):
        if request.url.params.get("pageToken"):
            return httpx.Response(503)
        return httpx.Response(200, json={"studies": [record], "nextPageToken": "x"})

    client = make_client(handler)
    assert len(client.search_trials("NSCLC")) == 1
    assert client.warnings


def test_truncation_and_details(record):
    client = make_client(
        lambda _: httpx.Response(200, json={"studies": [record], "nextPageToken": "x"}),
        max_pages=1,
    )
    assert client.search_trials("NSCLC")
    assert client.warnings
    detail = make_client(lambda _: httpx.Response(200, json=record)).get_trial(
        "NCT00000001"
    )
    assert detail["_retrieved_at"]
    with pytest.raises(ValueError):
        client.get_trial("../invalid")


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("ONCOMATCH_LIVE") != "1",
    reason="Set ONCOMATCH_LIVE=1 for network smoke test",
)
def test_live_search():
    client = ClinicalTrialsClient(max_pages=1)
    try:
        records = client.search_trials("non-small cell lung cancer", "KRAS G12C")
        assert records
        assert records[0]["protocolSection"]["identificationModule"][
            "nctId"
        ].startswith("NCT")
    finally:
        client.close()


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("ONCOMATCH_LIVE") != "1", reason="Opt-in live integration"
)
@pytest.mark.parametrize("case", ["kras_nsclc", "egfr_nsclc", "negative"])
def test_live_pipeline(case):
    profile = MolecularProfile.model_validate_json(
        (Path(__file__).parent / "fixtures" / f"{case}.json").read_text()
    )
    client = ClinicalTrialsClient(max_pages=1)
    try:
        results = match_patient(profile, client=client)
        assert results.search_status in {"complete", "partial"}
        assert results.trials
        assert not any("malformed" in w or "failed" in w for w in results.warnings)
        assert len({r.trial.nct_id for r in results.trials}) == len(results.trials)
        if case == "negative":
            assert not results.approved_options
        else:
            assert results.approved_options
        assert all(r.trial.sources and r.trial.retrieved_at for r in results.trials)
    finally:
        client.close()
