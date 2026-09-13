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


def retrieve_candidates(
    db: sqlite3.Connection, profile: Mapping[str, Any]
) -> list[RetrievedCandidate]:
    """Find broad recall candidates in the complete snapshot.

    Text hits may come from an exclusion criterion; every result must therefore
    undergo expert inclusion/exclusion review and deterministic safety gates.
    """
    disease_terms, molecular_terms = _terms(profile)
    candidates = []
    for nct_id, title, eligibility, conditions_json in db.execute(
        """SELECT nct_id,title,eligibility_text,conditions_json FROM studies
           WHERE overall_status IN ('RECRUITING','NOT_YET_RECRUITING')"""
    ):
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
        if disease_hits and molecular_hits:
            candidates.append(RetrievedCandidate(nct_id, disease_hits, molecular_hits))
    return sorted(
        candidates,
        key=lambda row: (
            -len(row.matched_molecular_terms),
            -len(row.matched_disease_terms),
            row.nct_id,
        ),
    )
