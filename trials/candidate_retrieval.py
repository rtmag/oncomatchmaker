"""Broad local candidate retrieval; retrieval is never treated as a match."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RetrievedCandidate:
    nct_id: str
    matched_disease_terms: tuple[str, ...]
    matched_molecular_terms: tuple[str, ...]
    preliminary_score: float = 0.0


@dataclass(frozen=True)
class TrialScreenResult:
    total_screened: int
    status_eligible: int
    disease_eligible: int
    molecular_eligible: int
    candidates: tuple[RetrievedCandidate, ...]
    landscape: tuple[dict, ...] = ()


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
    db: sqlite3.Connection, profile: Mapping[str, Any]
) -> TrialScreenResult:
    """Screen every snapshot study and rank viable candidates without model calls.

    Text hits may come from an exclusion criterion; every result must therefore
    undergo expert inclusion/exclusion review and deterministic safety gates.
    """
    disease_terms, molecular_terms = _terms(profile)
    candidates = []
    landscape = []
    total_screened = status_eligible = disease_eligible = molecular_eligible = 0
    for nct_id, title, eligibility, conditions_json, status in db.execute(
        """SELECT nct_id,title,eligibility_text,conditions_json,overall_status
           FROM studies"""
    ):
        total_screened += 1
        row = {"nct_id": nct_id, "title": title or nct_id, "preliminary_score": 0.0,
               "geography_score": None, "distance_km": None, "screening_state": "status_filtered"}
        landscape.append(row)
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
            sorted(term for term in molecular_terms if term in full_text)
        )
        # Same transparent retrieval heuristic for every study. These scores
        # describe text evidence for prioritization, not eligibility or benefit.
        preliminary = (min(45, 30 + 5 * len(disease_hits)) if disease_hits else 0)
        preliminary += min(40, 25 + 5 * len(molecular_hits)) if molecular_hits else 0
        preliminary += 10 if status == "RECRUITING" else 5
        preliminary += 5 if eligibility else 0
        row.update(preliminary_score=float(preliminary), screening_state="disease_not_retrieved")
        if not disease_hits:
            continue
        disease_eligible += 1
        row["screening_state"] = "molecular_not_retrieved"
        if molecular_terms and not molecular_hits:
            continue
        molecular_eligible += 1
        row["screening_state"] = "shortlist_pool"
        preliminary = min(45, 30 + 5 * len(disease_hits))
        if molecular_terms:
            preliminary += min(40, 25 + 5 * len(molecular_hits))
        preliminary += 10 if status == "RECRUITING" else 5
        preliminary += 5 if eligibility else 0
        candidates.append(
            RetrievedCandidate(
                nct_id,
                disease_hits,
                molecular_hits,
                float(preliminary),
            )
        )
    ranked = sorted(
        candidates,
        key=lambda row: (
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
    )


def retrieve_candidates(
    db: sqlite3.Connection, profile: Mapping[str, Any]
) -> list[RetrievedCandidate]:
    """Compatibility wrapper returning the complete ranked viable pool."""
    return list(screen_trials(db, profile).candidates)
