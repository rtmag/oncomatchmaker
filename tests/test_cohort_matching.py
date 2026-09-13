import json
import sqlite3

import pytest

from trials.cohort_matching import contains
from trials.pipeline import SNAPSHOT
from trials.provisional_scoring import provisional_score
from trials.registry_features import extract_features


def patient(gene="KRAS", allele="G12D", disease="cholangiocarcinoma"):
    return {
        "disease": {"raw_text": disease},
        "biomarkers": {"snv_indel": [{"gene": gene, "protein_change": allele}]},
    }


def score(profile, title, criteria, conditions='["Solid Tumor"]'):
    return provisional_score(
        profile, extract_features(title, criteria, conditions, "RECRUITING")
    )


@pytest.mark.parametrize(
    "gene,allele,other",
    [("KRAS", "G12D", "G12C"), ("BRAF", "V600E", "V600K"), ("EGFR", "L858R", "T790M")],
)
def test_specific_allele_overrides_broad_title_for_any_gene(gene, allele, other):
    result = score(
        patient(gene, allele),
        f"{gene} mutant solid tumors",
        f"Inclusion Criteria:\nSolid tumors with {gene} {other} mutation",
    )
    assert result["overall_score"] is None
    assert result["status"] == "cohort_unconfirmed"


def test_cross_cohort_basket_is_not_synthesized():
    result = score(
        patient(),
        "RAS-mutated NSCLC",
        "Inclusion Criteria:\nKRAS G12C solid tumors (Subprotocol A)\nRAS G12D NSCLC (Subprotocol C)",
    )
    assert result["overall_score"] is None
    positive = score(
        patient(),
        "Study",
        "Inclusion Criteria:\nKRAS G12C NSCLC (Arm A)\nKRAS G12D solid tumors (Arm B)",
    )
    assert positive["components"]["molecular"] == 0.6
    assert "Arm B" in positive["references"][-1]["text"]


def test_msi_negation_cannot_be_rescued_by_ras_hit():
    profile = patient(disease="colorectal cancer")
    profile["biomarkers"]["msi"] = {"status": "high"}
    result = score(
        profile,
        "RAS mutant colorectal cancer",
        "Inclusion Criteria:\nKRAS mutant colorectal cancer\nNon-MSI-H/non dMMR tumor status",
    )
    assert result["overall_score"] is None
    assert (
        score(
            profile,
            "MSI-H colorectal cancer",
            "Inclusion:\nColorectal cancer with dMMR and/or MSI-H",
        )["components"]["molecular"]
        == 0.6
    )


def test_gene_boundaries_and_event_binding():
    assert not contains("MET", "metastatic tumor")
    assert contains("MET", "MET-mutated tumor")
    profile = patient("MET", None, "non-small cell lung cancer")
    profile["biomarkers"]["snv_indel"][0]["event"] = (
        "exon 14 skipping splice-site alteration"
    )
    assert (
        score(
            profile,
            "Study",
            "Inclusion Criteria:\nMET exon 14 skipping non-small cell lung cancer",
        )["components"]["molecular"]
        == 0.6
    )
    assert (
        score(
            patient("ALK", None),
            "Study",
            "Inclusion Criteria:\nALK mutation and RET fusion solid tumors",
        )["components"]["molecular"]
        is None
    )


def test_separate_disease_requirement_overrides_broad_title():
    result = score(
        patient(),
        "KRAS mutant solid tumors",
        "Inclusion Criteria:\nHistologically confirmed NSCLC\nKRAS G12D mutation",
    )
    assert result["overall_score"] is None


def test_unscoped_explicit_requirement_but_not_incidental_mention():
    p = patient("MET", None, "NSCLC")
    p["biomarkers"]["snv_indel"][0]["event"] = "exon 14 skipping"
    assert (
        score(p, "NSCLC study", "Criteria:\nPatients must have MET exon 14 skipping")[
            "components"
        ]["molecular"]
        == 0.6
    )
    assert (
        score(p, "NSCLC study", "MET exon 14 skipping background discussion")[
            "components"
        ]["molecular"]
        is None
    )


@pytest.mark.skipif(
    not SNAPSHOT.exists(), reason="Local non-redistributed snapshot unavailable"
)
@pytest.mark.parametrize(
    "nct,case,supported",
    [
        ("NCT05067283", "cholangi", False),
        ("NCT06162221", "cholangi", False),
        ("NCT06040541", "cholangi", True),
        ("NCT06031688", "met", True),
        ("NCT07619339", "met", True),
        ("NCT04181060", "egfr", True),
        ("NCT05310643", "msi", True),
        ("NCT07807800", "msi", True),
        ("NCT07446322", "msi", False),
    ],
)
def test_preserved_registry_regressions(nct, case, supported):
    profiles = json.loads(
        (
            SNAPSHOT.parents[2].parent / "evaluation/matching_spike/profiles.json"
        ).read_text()
    )["cases"]
    profile = (
        patient()
        if case == "cholangi"
        else next(p for p in profiles if case in p["case_id"].lower())
    )
    with sqlite3.connect(f"file:{SNAPSHOT}?mode=ro", uri=True) as db:
        title, criteria, conditions = db.execute(
            "SELECT title,eligibility_text,conditions_json FROM studies WHERE nct_id=?",
            (nct,),
        ).fetchone()
    result = score(profile, title, criteria, conditions)
    assert (result["components"]["molecular"] is not None) is supported, (nct, result)
    if not supported:
        assert result["overall_score"] is None
