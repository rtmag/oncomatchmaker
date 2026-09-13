"""Conservative query concepts; no actionability inferred from VUS or CH."""

from __future__ import annotations

import re

from normalization.genes import get_registry
from schemas.molecular_profile import MolecularProfile


def disease_name(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    text = re.sub(r"\s+nsclc$", "", text)
    if text in {
        "nsclc",
        "non small cell lung cancer",
        "non small cell lung carcinoma",
        "lung adenocarcinoma",
    }:
        return "non-small cell lung cancer"
    return text


def actionable_findings(profile: MolecularProfile) -> list[tuple[str, str]]:
    findings = []
    for collection, kind in [
        (profile.biomarkers.snv_indel, "variant"),
        (profile.biomarkers.copy_number, "cnv"),
        (profile.biomarkers.fusions, "fusion"),
    ]:
        for item in collection:
            if item.requires_review or item.origin in {
                "germline",
                "clonal_hematopoiesis",
            }:
                continue
            gene = get_registry().resolve(item.gene)
            if gene.symbol is None:
                continue
            if item.potential_ch or (item.classification or "").lower().replace(
                "_", " "
            ) not in {
                "pathogenic",
                "likely pathogenic",
                "oncogenic",
                "likely oncogenic",
            }:
                continue
            alteration = (
                (
                    item.protein_change
                    or item.hgvs_p
                    or item.hgvs_c
                    or item.raw_alteration
                    or ""
                ).removeprefix("p.")
                if kind == "variant"
                else item.alteration
                if kind == "cnv"
                else "fusion"
            )
            findings.append((gene.symbol, alteration))
    if (profile.biomarkers.msi.status or "").lower() in {
        "high",
        "msi-high",
        "msi high",
    }:
        findings.append(("MSI", "high"))
    return list(dict.fromkeys(findings))


def generate_queries(profile: MolecularProfile) -> list[dict[str, str]]:
    disease = disease_name(profile.disease.normalized or profile.disease.raw_text)
    if not disease:
        return []
    queries = []
    for gene, variant in actionable_findings(profile):
        for condition, term in [
            (disease, f"{gene} {variant}".strip()),
            (disease, gene),
            ("solid tumor", f"{gene} {variant}".strip()),
        ]:
            query = {"disease": condition, "term": term}
            if query not in queries:
                queries.append(query)
    # Negative reports can still find disease trials, without inventing a target.
    return queries or [{"disease": disease, "term": ""}]
