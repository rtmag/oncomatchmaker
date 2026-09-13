"""Broad local candidate retrieval; retrieval is never treated as a match."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Mapping

from trials.cohort_matching import contains
from trials.provisional_scoring import provisional_score
from trials.registry_features import fingerprint


@dataclass(frozen=True)
class RetrievedCandidate:
    nct_id: str
    matched_disease_terms: tuple[str, ...]
    matched_molecular_terms: tuple[str, ...]
    preliminary_score: float = 0.0
    retrieval_route: str = "named_disease"
    exact_variant_hits: tuple[str, ...] = ()


@dataclass(frozen=True)
class TrialScreenResult:
    total_screened: int
    status_eligible: int
    disease_eligible: int
    molecular_eligible: int
    candidates: tuple[RetrievedCandidate, ...]
    landscape: tuple[dict, ...] = ()
    exploratory: tuple[RetrievedCandidate, ...] = ()


def _variant_hits(terms, text):
    """Only explicit protein substitutions, not a different allele of the gene."""
    variants = {
        hit.upper()
        for term in terms
        for hit in re.findall(r"(?<![a-z0-9])([a-z]\d+[a-z])(?![a-z0-9])", term)
    }
    return tuple(
        sorted(
            v
            for v in variants
            if re.search(rf"(?<![a-z0-9]){re.escape(v)}(?![a-z0-9])", text, re.I)
        )
    )


def _solid_basket(disease_terms, title, inclusion):
    disease = " ".join(disease_terms)
    # Unknown diseases and hematologic cancers must not be assumed solid tumors.
    if re.search(r"leukemia|leukaemia|lymphoma|myeloma|myelodys|myeloprolif", disease):
        return False
    if not re.search(
        r"carcinoma|sarcoma|melanoma|glioma|glioblastoma|mesothelioma|nsclc|sclc|solid tumou?r",
        disease,
    ):
        return False
    # This is a retrieval hint only; experts check phase/cohort restrictions.
    return bool(re.search(r"\bsolid tumou?rs?\b", title + " " + inclusion, re.I))


def _terms(profile: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    disease = profile["disease"]
    disease_terms = {
        str(term).casefold()
        for term in [
            disease.get("raw_text"),
            disease.get("normalized"),
            *disease.get("synonyms", []),
        ]
        if term and len(str(term)) >= 4
    }
    molecular_terms: set[str] = set()
    biomarkers = profile["biomarkers"]
    for collection in ("snv_indel", "copy_number", "fusions"):
        for finding in biomarkers.get(collection, []):
            classification = str(finding.get("classification") or "").casefold()
            if (
                finding.get("requires_review")
                or finding.get("potential_ch")
                or str(finding.get("report_category") or "").casefold() == "vus"
                or "uncertain significance" in classification
            ):
                continue
            molecular_terms.add(finding["gene"].casefold())
            molecular_terms.update(
                term.casefold() for term in finding.get("gene_synonyms", [])
            )
            for field in ("protein_change", "event", "raw_alteration", "alteration"):
                if finding.get(field):
                    molecular_terms.add(str(finding[field]).casefold())
    if str(biomarkers.get("msi", {}).get("status", "")).casefold() in {
        "high",
        "msi-high",
        "msi high",
    }:
        molecular_terms.update(
            {"msi-h", "msi high", "microsatellite instability-high", "dmmr"}
        )
    return disease_terms, {term for term in molecular_terms if len(term) >= 3}


def screen_trials(
    db: sqlite3.Connection, profile: Mapping[str, Any], feature_records=None
) -> TrialScreenResult:
    """Screen every snapshot study and rank viable candidates without model calls.

    Text hits may come from an exclusion criterion; every result must therefore
    undergo expert inclusion/exclusion review and deterministic safety gates.
    """
    disease_terms, molecular_terms = _terms(profile)
    candidates = []
    exploratory = []
    landscape = []
    total_screened = status_eligible = disease_eligible = molecular_eligible = 0
    for nct_id, title, eligibility, conditions_json, status in db.execute(
        """SELECT nct_id,title,eligibility_text,conditions_json,overall_status
           FROM studies"""
    ):
        total_screened += 1
        row = {
            "nct_id": nct_id,
            "title": title or nct_id,
            "preliminary_score": 0.0,
            "geography_score": None,
            "distance_km": None,
            "screening_state": "status_filtered",
        }
        landscape.append(row)
        stored = (feature_records or {}).get(nct_id)
        features = (
            stored[1]
            if stored
            and stored[0] == fingerprint(title, eligibility, conditions_json, status)
            else None
        )
        assessment = provisional_score(profile, features)
        row.update(
            clinical_score=assessment["overall_score"], clinical_assessment=assessment
        )
        if status not in {"RECRUITING", "NOT_YET_RECRUITING"}:
            continue
        status_eligible += 1
        condition_text = " ".join(json.loads(conditions_json)).casefold()
        full_text = " ".join(
            (title or "", eligibility or "", condition_text)
        ).casefold()
        disease_hits = tuple(
            sorted(term for term in disease_terms if term in full_text)
        )
        molecular_hits = tuple(
            sorted(
                term
                for term in molecular_terms
                if term in full_text and contains(term, full_text)
            )
        )
        inclusion = re.split(r"exclusion\s+criteria", eligibility or "", flags=re.I)[0]
        positive_text = (title or "") + " " + inclusion
        variant_hits = _variant_hits(molecular_terms, positive_text)
        if assessment["status"] == "cohort_unconfirmed":
            row["screening_state"] = "cohort_unconfirmed"
            if variant_hits:
                exploratory.append(
                    RetrievedCandidate(
                        nct_id,
                        disease_hits,
                        molecular_hits,
                        0.0,
                        "other_or_unconfirmed_disease",
                        variant_hits,
                    )
                )
            continue
        basket = bool(molecular_hits) and _solid_basket(
            disease_terms, title or "", inclusion
        )
        # Same transparent retrieval heuristic for every study. These scores
        # describe text evidence for prioritization, not eligibility or benefit.
        preliminary = min(45, 30 + 5 * len(disease_hits)) if disease_hits else 0
        preliminary += min(40, 25 + 5 * len(molecular_hits)) if molecular_hits else 0
        preliminary += 10 if status == "RECRUITING" else 5
        preliminary += 5 if eligibility else 0
        row.update(
            preliminary_score=float(preliminary),
            screening_state="disease_not_retrieved",
        )
        if not disease_hits:
            if not basket:
                if variant_hits:
                    exploratory.append(
                        RetrievedCandidate(
                            nct_id,
                            disease_hits,
                            molecular_hits,
                            float(preliminary),
                            "other_or_unconfirmed_disease",
                            variant_hits,
                        )
                    )
                continue
            # Broad solid-tumor cohorts must not require the literal cancer name.
            preliminary = min(100, preliminary + 30)
            row["preliminary_score"] = float(preliminary)
        disease_eligible += 1
        row["screening_state"] = "molecular_not_retrieved"
        if molecular_terms and not molecular_hits:
            continue
        molecular_eligible += 1
        row["screening_state"] = "shortlist_pool"
        candidates.append(
            RetrievedCandidate(
                nct_id,
                disease_hits,
                molecular_hits,
                float(preliminary),
                "named_disease" if disease_hits else "solid_tumor_basket",
                variant_hits,
            )
        )
    ranked = sorted(
        candidates,
        key=lambda row: (
            -len(row.exact_variant_hits),
            -row.preliminary_score,
            -len(row.matched_molecular_terms),
            -len(row.matched_disease_terms),
            row.nct_id,
        ),
    )
    return TrialScreenResult(
        total_screened,
        status_eligible,
        disease_eligible,
        molecular_eligible,
        tuple(ranked),
        tuple(landscape),
        tuple(
            sorted(
                exploratory,
                key=lambda row: (
                    -len(row.exact_variant_hits),
                    -row.preliminary_score,
                    row.nct_id,
                ),
            )
        ),
    )


def retrieve_candidates(
    db: sqlite3.Connection, profile: Mapping[str, Any]
) -> list[RetrievedCandidate]:
    """Compatibility wrapper returning the complete ranked viable pool."""
    return list(screen_trials(db, profile).candidates)
