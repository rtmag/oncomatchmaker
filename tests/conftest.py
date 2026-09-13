import json
from pathlib import Path

import pytest

from schemas.molecular_profile import MolecularProfile
from trials.trial_parser import parse_trial

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def profile():
    return MolecularProfile.model_validate_json(
        (FIXTURES / "kras_nsclc.json").read_text()
    )


@pytest.fixture
def record():
    # Handcrafted records cover precise boundary cases; never presented as live trials.
    return {
        "_retrieved_at": "2026-09-13T00:00:00+00:00",
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT00000001",
                "briefTitle": "KRAS G12C inhibitor in NSCLC",
            },
            "statusModule": {"overallStatus": "RECRUITING"},
            "conditionsModule": {"conditions": ["Non-small cell lung cancer"]},
            "designModule": {"phases": ["PHASE2"]},
            "eligibilityModule": {
                "minimumAge": "18 Years",
                "maximumAge": "80 Years",
                "sex": "ALL",
                "eligibilityCriteria": "Inclusion Criteria:\nECOG 0-1. Prior targeted therapy required.\nExclusion Criteria:\nUntreated brain metastases.",
            },
            "contactsLocationsModule": {
                "locations": [
                    {
                        "facility": "Synthetic active site",
                        "status": "RECRUITING",
                        "city": "Singapore",
                        "country": "Singapore",
                        "geoPoint": {"lat": 1.35, "lon": 103.82},
                    },
                    {
                        "facility": "Synthetic inactive site",
                        "status": "COMPLETED",
                        "geoPoint": {"lat": 1.3521, "lon": 103.8198},
                    },
                ]
            },
        },
    }


@pytest.fixture
def trial(record):
    return parse_trial(record)


@pytest.fixture
def recorded_response():
    return json.loads((FIXTURES / "ctgov_recorded.json").read_text())
