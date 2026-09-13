"""Fresh patient-to-registry comparison; no patient-specific match is cached."""

import re

from trials.clinical_scoring import CLINICAL_WEIGHTS, aggregate


def provisional_score(profile, features):
    components = dict.fromkeys(CLINICAL_WEIGHTS)
    reasons, references = [], []
    if features is None:
        return {
            **aggregate(components),
            "rationale": ["Features missing or stale; rebuild snapshot features."],
            "references": [],
            "status": "unscored",
        }
    if features["status"] not in {"RECRUITING", "NOT_YET_RECRUITING"}:
        return {
            **aggregate(components),
            "rationale": ["Study status is not active/upcoming."],
            "references": [],
            "status": "unscored",
        }
    disease = profile.get("disease", {})
    terms = [
        v.casefold()
        for v in [
            disease.get("raw_text"),
            disease.get("normalized"),
            *disease.get("synonyms", []),
        ]
        if v and len(v) >= 4
    ]
    context = " ".join([features["title"], *features["conditions"]]).casefold()
    if any(term in context for term in terms):
        components["disease"] = 0.9
        references.append({"source_field": "conditions/title", "text": context})
        reasons.append(
            "Named disease context present; applicable cohort still unconfirmed."
        )
    elif (
        features["broad_solid_mention"]
        and re.search(
            r"carcinoma|sarcoma|melanoma|glioma|glioblastoma|mesothelioma|nsclc",
            " ".join(terms),
        )
        and not re.search(r"leukemia|lymphoma|myeloma", " ".join(terms))
    ):
        components["disease"] = 0.6
        reasons.append(
            "Possible solid-tumor basket; histology and cohort require review."
        )
    for collection in ("snv_indel", "copy_number", "fusions"):
        for finding in profile.get("biomarkers", {}).get(collection, []):
            classification = str(finding.get("classification") or "").casefold()
            if (
                finding.get("requires_review")
                or finding.get("potential_ch")
                or "vus" in classification
                or "uncertain" in classification
                or str(finding.get("report_category", "")).casefold() == "vus"
            ):
                continue
            names = [finding["gene"], *finding.get("gene_synonyms", [])]
            if not set(n.upper() for n in names).intersection(
                features["lexical_tokens"]
            ):
                continue
            gene_pattern = re.compile(
                r"(?<![A-Za-z0-9])(?:"
                + "|".join(re.escape(n) for n in names)
                + r")(?![A-Za-z0-9])",
                re.I,
            )
            variant = (
                str(finding.get("protein_change") or "").removeprefix("p.").upper()
            )
            for mention in features["biomarker_mentions"]:
                if not gene_pattern.search(mention["text"]):
                    continue
                if mention["section"] not in {"title", "inclusion"}:
                    reasons.append(
                        "Biomarker appears in exclusion/unscoped text; no positive credit from that clause."
                    )
                    continue
                if re.search(
                    r"\bwithout\b|\bnegative\b|wild.type|not eligible|not permitted|\bexcluded\b",
                    mention["text"],
                    re.I,
                ):
                    reasons.append(
                        "Negated or restrictive biomarker clause needs review; no positive credit."
                    )
                    continue
                exact = variant and any(
                    gene in names and allele == variant
                    for gene, allele in mention.get("gene_variant_pairs", [])
                )
                event = collection == "fusions" and any(
                    e.casefold() == "fusion" for e in mention["events"]
                )
                event = event or (
                    collection == "copy_number"
                    and "amplification"
                    in str(
                        finding.get("event") or finding.get("alteration") or ""
                    ).casefold()
                    and any(e.casefold() == "amplification" for e in mention["events"])
                )
                gene_level = (
                    not mention["variants"]
                    and not mention["events"]
                    and bool(
                        re.search(r"mutant|mutation|alteration", mention["text"], re.I)
                    )
                )
                if exact or event or gene_level:
                    value = (
                        0.9 if mention["section"] == "title" and not gene_level else 0.6
                    )
                    components["molecular"] = max(components["molecular"] or 0, value)
                    references.append(mention)
                    reasons.append(
                        "Reported gene and alteration co-occur in a registry clause; logical/cohort applicability remains uncertain."
                    )
    # Never infer eligibility, actionability, mechanism, or safety from word counts.
    reasons.append(
        "Unassessed dimensions are unknown, not poor matches. Scores are uncalibrated provisional estimates, not enrollment probabilities."
    )
    result = aggregate(components)
    # A named mutation-targeted title cannot become a high disease-only score
    # when the patient's qualifying marker is not established.
    unresolved_target = components["molecular"] is None and any(
        m["section"] == "title" and (m.get("gene_variant_pairs") or m["events"])
        for m in features["biomarker_mentions"]
    )
    if unresolved_target:
        result["overall_score"] = None
        reasons.append(
            "Title specifies a molecular target not established for this patient; molecular applicability requires review."
        )
    return {
        **result,
        "rationale": list(dict.fromkeys(reasons)),
        "references": references,
        "status": "provisional" if result["overall_score"] is not None else "unscored",
    }
