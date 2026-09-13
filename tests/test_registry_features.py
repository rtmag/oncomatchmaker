import hashlib
import json
import sqlite3

import pytest

from trials.candidate_retrieval import screen_trials
from trials.clinical_scoring import CLINICAL_WEIGHTS, aggregate
from trials.provisional_scoring import provisional_score
from trials.registry_features import build, extract_features, load


def patient(gene="KRAS", variant="G12D", disease="cholangiocarcinoma"):
    return {
        "disease": {"raw_text": disease},
        "biomarkers": {"snv_indel": [{"gene": gene, "protein_change": variant}]},
    }


def features(
    title="KRAS G12D solid tumors",
    criteria="Inclusion Criteria:\nAdvanced solid tumors.\nExclusion Criteria:\nECOG > 1",
):
    return extract_features(title, criteria, '["Solid Tumor"]', "RECRUITING")


@pytest.mark.parametrize(
    "gene,variant", [("KRAS", "G12D"), ("EGFR", "L858R"), ("BRAF", "V600E")]
)
def test_each_new_patient_is_compared_against_reusable_features(gene, variant):
    f = features(f"{gene} {variant} solid tumors")
    assert (
        provisional_score(patient(gene, variant), f)["components"]["molecular"] == 0.9
    )
    assert (
        provisional_score(patient("NRAS", "Q61R"), f)["components"]["molecular"] is None
    )
    assert (
        provisional_score(patient(gene, "G12C"), f)["components"]["molecular"] is None
    )


def test_exclusions_unknowns_vus_and_gene_variant_pairs_do_not_create_matches():
    f = features("Solid tumors", "Exclusion Criteria:\nKRAS G12D")
    assert provisional_score(patient(), f)["components"]["molecular"] is None
    f = features("KRAS G12C and BRAF G12D solid tumors")
    assert provisional_score(patient(), f)["components"]["molecular"] is None
    p = patient()
    p["biomarkers"]["snv_indel"][0]["report_category"] = "VUS"
    assert provisional_score(p, features())["components"]["molecular"] is None
    result = provisional_score(patient(), features())
    assert all(
        result["components"][key] is None
        for key in ("evidence", "mechanism", "eligibility", "safety")
    )
    assert result["coverage"] == 0.45
    assert result["references"]


def test_shared_scale_preserves_unknowns_and_conflicts():
    components = dict.fromkeys(CLINICAL_WEIGHTS)
    assert aggregate(components)["overall_score"] is None
    components["molecular"] = 0.9
    assert aggregate(components)["overall_score"] == 27
    assert aggregate(components)["coverage"] == 0.3
    assert aggregate(components)["uncertainty_bounds"] == [27, 97]
    assert aggregate(components, conflict=True)["overall_score"] is None


def test_target_mismatch_cannot_receive_disease_only_high_score():
    f = features("KRAS G12D non-small cell lung cancer")
    result = provisional_score(
        patient("EGFR", "L858R", "non-small cell lung cancer"), f
    )
    assert result["overall_score"] is None
    assert result["status"] == "cohort_unconfirmed"


@pytest.mark.parametrize(
    "gene,collection,alteration,title",
    [
        ("ALK", "fusions", "fusion", "ALK fusion solid tumors"),
        ("ERBB2", "copy_number", "amplification", "ERBB2 amplification solid tumors"),
    ],
)
def test_non_substitution_biomarkers(gene, collection, alteration, title):
    p = {
        "disease": {"raw_text": "carcinoma"},
        "biomarkers": {collection: [{"gene": gene, "event": alteration}]},
    }
    assert provisional_score(p, features(title))["components"]["molecular"] == 0.9


def test_negated_and_unscoped_mentions_do_not_gain_molecular_credit():
    for title, criteria in [
        ("Solid tumors without KRAS G12D", ""),
        ("Solid tumors", "KRAS G12D"),
    ]:
        assert (
            provisional_score(patient(), features(title, criteria))["components"][
                "molecular"
            ]
            is None
        )


def test_source_sections_and_cohort_context_are_retained():
    text = "Inclusion Criteria:\nCohort A: KRAS G12D, ECOG 0-1, prior therapy required.\nExclusion Criteria:\nCohort B: EGFR L858R"
    f = features("Study", text)
    assert any(
        row["section"] == "inclusion" and "Cohort A" in row["text"]
        for row in f["criteria"]
    )
    assert any(
        row["section"] == "exclusion" and "Cohort B" in row["text"]
        for row in f["criteria"]
    )
    assert all(row["source_field"] == "eligibility_text" for row in f["criteria"])


def test_companion_build_preserves_source_and_rejects_stale_features(tmp_path):
    snapshot = tmp_path / "oncology.sqlite"
    with sqlite3.connect(snapshot) as db:
        db.execute(
            "CREATE TABLE studies(nct_id,title,eligibility_text,conditions_json,overall_status)"
        )
        db.execute(
            "INSERT INTO studies VALUES(?,?,?,?,?)",
            (
                "NCT00000001",
                "KRAS G12D solid tumors",
                "Inclusion Criteria:\nKRAS G12D",
                json.dumps(["Solid Tumor"]),
                "RECRUITING",
            ),
        )
    before = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    assert build(snapshot)["records"] == 1
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == before
    stored = load(snapshot)
    with sqlite3.connect(snapshot) as db:
        first = screen_trials(db, patient(), stored).landscape[0]
        assert first["clinical_score"] is not None
        assert first["clinical_assessment"]["score_version"] == "clinical-fit-v3"
        db.execute("UPDATE studies SET eligibility_text='Changed'")
        stale = screen_trials(db, patient(), stored).landscape[0]
        assert stale["clinical_score"] is None
    with pytest.raises(ValueError):
        build(snapshot, snapshot)


def test_failed_feature_rebuild_keeps_previous_companion(tmp_path, monkeypatch):
    import trials.registry_features as registry

    snapshot = tmp_path / "oncology.sqlite"
    output = tmp_path / "trial_features.sqlite"
    output.write_bytes(b"previous derived database")
    before = output.read_bytes()

    def fail(*args):
        raise RuntimeError("Synthetic builder failure")

    monkeypatch.setattr(registry, "_build", fail)
    with pytest.raises(RuntimeError, match="Synthetic"):
        registry.build(snapshot)
    assert output.read_bytes() == before
    assert not list(tmp_path.glob(".trial-features-*"))
