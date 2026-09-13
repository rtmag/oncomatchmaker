"""Contract and safety-gate tests for the ASTRA expert team."""

import json
import unittest
from pathlib import Path

from schemas.astra_contracts import (
    EXPERT_ROLES,
    ContractError,
    validate_molecular_profile,
)
from trials.astra_team import build_expert_packets, reach_consensus

ROOT = Path(__file__).resolve().parents[1]


def assessment(
    role, decision="support", relationships=None, missing=None, conflicts=None
):
    return {
        "trial_id": "NCT00000001",
        "expert_role": role,
        "assessment": decision,
        "confidence": 0.8,
        "relationships": relationships or ["not_applicable"],
        "supporting_facts": ["Synthetic evidence"],
        "conflicting_facts": conflicts or [],
        "missing_information": missing or [],
        "evidence_references": ["https://clinicaltrials.gov/study/NCT00000001"],
        "reasoning_summary": "Synthetic contract test.",
    }


class AstraTeamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(
            (ROOT / "tests/fixtures/astra_profile.json").read_text()
        )

    def test_profile_contract_accepts_canonical_symbols_and_synonyms(self):
        validate_molecular_profile(self.profile)
        invalid = json.loads(json.dumps(self.profile))
        invalid["biomarkers"]["snv_indel"][0]["gene"] = "Egfr"
        with self.assertRaises(ContractError):
            validate_molecular_profile(invalid)

    def test_packets_are_role_specific_and_strip_locations(self):
        trial = {
            "nct_id": "NCT00000001",
            "title": "Synthetic",
            "eligibility_text": "EGFR L858R",
            "locations": [{"facility": "Must not enter molecular review"}],
        }
        packets = build_expert_packets(self.profile, trial, [])
        self.assertEqual(
            {packet["expert_role"] for packet in packets}, set(EXPERT_ROLES)
        )
        self.assertTrue(all("locations" not in packet["trial"] for packet in packets))

    def test_missing_clinical_facts_prevent_tier_one(self):
        values = [assessment(role) for role in EXPERT_ROLES]
        values[1] = assessment(
            "disease_oncology", relationships=["direct_variant"], missing=["stage"]
        )
        result = reach_consensus(values)
        self.assertEqual(result["disposition"], "candidate")
        self.assertEqual(result["match_tier"], "tier_2")
        self.assertEqual(result["eligibility_state"], "not_determined")

    def test_safety_conflict_cannot_be_outvoted(self):
        values = [
            assessment(role, relationships=["direct_variant"]) for role in EXPERT_ROLES
        ]
        values[-1] = assessment(
            "safety_critic",
            "conflict",
            ["direct_variant"],
            conflicts=["Trial excludes EGFR L858R"],
        )
        result = reach_consensus(values)
        self.assertEqual(result["match_tier"], "not_matched")
        self.assertEqual(result["safety_gate_triggered_by"], ["safety_critic"])

    def test_wrong_disease_is_a_hard_conflict(self):
        values = [
            assessment(role, relationships=["direct_variant"]) for role in EXPERT_ROLES
        ]
        values[1] = assessment(
            "disease_oncology",
            "conflict",
            ["direct_variant"],
            conflicts=["Wrong disease cohort"],
        )
        result = reach_consensus(values)
        self.assertEqual(result["disposition"], "conflict")
        self.assertEqual(result["safety_gate_triggered_by"], ["disease_oncology"])

    def test_caution_prevents_tier_one(self):
        values = [
            assessment(role, relationships=["direct_variant"]) for role in EXPERT_ROLES
        ]
        values[2] = assessment("actionability_evidence", "caution", ["direct_variant"])
        self.assertEqual(reach_consensus(values)["match_tier"], "tier_2")

    def test_consensus_requires_every_role_exactly_once(self):
        with self.assertRaises(ContractError):
            reach_consensus([assessment(role) for role in EXPERT_ROLES[:-1]])


if __name__ == "__main__":
    unittest.main()
