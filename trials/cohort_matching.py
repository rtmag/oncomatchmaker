"""Conservative local marker/cohort evidence, never an enrollment decision.

Specific inclusion clauses take precedence over broad titles. A supported marker
and its disease context must occur in the same clause (or explicit heading).
Unparsed logic is returned for review, rather than asserted as compatibility.
"""

import re


def contains(term, text):
    return bool(re.search(r"(?<![\w])" + re.escape(term) + r"(?![\w])", text, re.I))


SOLID = r"\bsolid[ -](?:tumou?rs?|malignanc\w*)\b"
DISEASES = (
    r"nsclc|non.small.cell lung",
    r"colorectal|\bm?crc\b|\bcolon\b|\brectum\b|\brectal\b",
    r"pancrea|\bpdac\b",
    r"cholangi|biliary",
    r"breast",
    r"prostate",
    r"melanoma",
    r"glioma|glioblastoma",
    r"leuk[ae]mia",
    r"lymphoma",
    r"myeloma",
    r"endometri",
    r"ovarian",
)
NEGATIVE = r"\bwithout\b|\bnegative\b|wild.type|not eligible|not permitted|\bexcluded\b|must not|\bno prior\b"
MSI_HIGH = r"\bMSI[ -](?:H|high)\b|microsatellite instability.high|\bdMMR\b|deficient mismatch repair"
MSI_LOW = r"\bMSS\b|microsatellite.stable|\bpMMR\b|proficient mismatch repair|non[ -](?:MSI[ -]H|dMMR)|non.microsatellite instability high|non.deficient mismatch repair"


def disease_fit(text, profile):
    disease = profile.get("disease", {})
    terms = [
        v
        for v in [
            disease.get("raw_text"),
            disease.get("normalized"),
            *disease.get("synonyms", []),
        ]
        if v
    ]
    patient = " ".join(terms)
    groups = [pattern for pattern in DISEASES if re.search(pattern, text, re.I)]
    if re.search(SOLID, text, re.I):
        if re.search(
            r"leuk[ae]mia|lymphoma|myeloma|myelodys|myeloprolif", patient, re.I
        ):
            return None
        if re.search(
            r"carcinoma|sarcoma|melanoma|glioma|glioblastoma|mesothelioma|nsclc|solid tumou?r",
            patient,
            re.I,
        ):
            # Excluded histologies are not positive disease evidence.
            if re.search(r"excluding|except|other than", text, re.I) and any(
                re.search(p, patient, re.I) for p in groups
            ):
                return None
            return 0.6
    if groups:
        return 0.9 if any(re.search(p, patient, re.I) for p in groups) else None
    return 0.9 if any(len(t) >= 4 and contains(t, text) for t in terms) else None


def marker_fit(finding, collection, text):
    names = [finding["gene"], *finding.get("gene_synonyms", [])]
    if finding["gene"].upper() in {"KRAS", "NRAS", "HRAS"}:
        names.append("RAS")  # Explicit RAS family cohorts, not arbitrary substrings.
    upper = text.upper()
    if not any(n.upper() in upper for n in names):
        return None
    pattern = r"(?<![\w])(?:" + "|".join(re.escape(n) for n in names) + r")(?![\w])"
    if not re.search(pattern, text, re.I):
        return None
    if re.search(NEGATIVE, text, re.I):
        return False
    variant = str(finding.get("protein_change") or "").removeprefix("p.").upper()
    # Bind the event to its gene, never to another gene elsewhere in the line.
    pairs = re.findall(pattern + r"[\s:(-]+(?:p\.)?([A-Z]\d+[A-Z])\b", text, re.I)
    if pairs:
        return bool(variant and variant in [v.upper() for v in pairs])
    lists = re.findall(pattern + r"\s*\(([^)]{1,400})\)", text, re.I)
    for alleles in lists:
        if re.search(r"\b[A-Z]{2,}[ -]+[A-Z]\d+[A-Z]\b", alleles):
            continue  # Another gene's variant must not be borrowed.
        variants = re.findall(r"\b[A-Z]\d+[A-Z]\b", alleles, re.I)
        if variants:
            return bool(variant and variant in [v.upper() for v in variants])
    event = str(finding.get("event") or finding.get("alteration") or "").casefold()
    events = (
        (r"exon[ -]+14[ -]+skipping", "exon 14 skipping" in event),
        (r"fusions?", collection == "fusions"),
        (r"amplification", "amplification" in event),
        (r"(?:biallelic[ -]+)?loss|deletion", "loss" in event or "deletion" in event),
    )
    for expression, present in events:
        if re.search(pattern + r"[\s:(-]+(?:gene[ -]+)?" + expression, text, re.I):
            # Biallelic/germline/assay qualifications remain unresolved.
            return present
    if re.search(r"\b[A-Z]\d+[A-Z]\b|exon[ -]+\d+|fusion|amplification", text, re.I):
        return False
    return bool(
        re.search(
            pattern + r"[ -]+(?:gene[ -]+)?(?:mutant|mutated|mutation|alteration)",
            text,
            re.I,
        )
    )


def assess_cohorts(profile, features):
    mentions = features["biomarker_mentions"]
    inclusion = [m for m in mentions if m["section"] == "inclusion"]
    title = [m for m in mentions if m["section"] == "title"]
    findings = []
    for collection in ("snv_indel", "copy_number", "fusions"):
        for finding in profile.get("biomarkers", {}).get(collection, []):
            label = (
                str(finding.get("classification") or "")
                + " "
                + str(finding.get("report_category") or "")
            )
            if not (
                finding.get("requires_review")
                or finding.get("potential_ch")
                or re.search(r"vus|uncertain", label, re.I)
            ):
                findings.append((collection, finding))
    supported, unresolved = [], []
    targeted = bool(title)
    context = features["title"] + " " + " ".join(features["conditions"])
    explicit_context = features.get("inclusion_context", "")
    if not features.get("multiple_cohorts") and any(
        re.search(p, explicit_context, re.I) for p in DISEASES
    ):
        # Specific inclusion histology beats a broad title even when the marker
        # and histology requirements are on separate lines.
        context = explicit_context
    for collection, finding in findings:
        scoped = [(m, marker_fit(finding, collection, m["text"])) for m in inclusion]
        scoped = [(m, fit) for m, fit in scoped if fit is not None]
        # An explicit constraint for this gene overrides all title-level hints.
        choices = scoped or [
            (m, marker_fit(finding, collection, m["text"])) for m in title
        ]
        for mention, fit in choices:
            if fit is None:
                continue
            targeted = True
            if not fit:
                unresolved.append(mention)
                continue
            text = mention.get("cohort_context", "") + " " + mention["text"]
            disease = disease_fit(text, profile)
            explicit_disease = re.search(SOLID, text, re.I) or any(
                re.search(p, text, re.I) for p in DISEASES
            )
            if (
                disease is None
                and not explicit_disease
                and not features.get("multiple_cohorts")
            ):
                disease = disease_fit(context, profile)
            if disease is None or re.search(
                r"\b(?:and|plus)\b.*\b(?:mutation|fusion|amplification)\b", text, re.I
            ):
                unresolved.append(mention)
                continue
            supported.append(
                (0.9 if mention["section"] == "title" else 0.6, disease, mention)
            )
    msi = str(profile.get("biomarkers", {}).get("msi", {}).get("status", "")).casefold()
    if msi in {"high", "msi-high", "msi high", "msi-h"}:
        choices = [
            m for m in inclusion if re.search(MSI_HIGH + "|" + MSI_LOW, m["text"], re.I)
        ]
        choices = choices or [
            m for m in title if re.search(MSI_HIGH + "|" + MSI_LOW, m["text"], re.I)
        ]
        for m in choices:
            targeted = True
            if re.search(MSI_LOW, m["text"], re.I) or re.search(
                NEGATIVE, m["text"], re.I
            ):
                continue
            text = m.get("cohort_context", "") + " " + m["text"]
            disease = disease_fit(text, profile) or (
                disease_fit(context, profile)
                if not features.get("multiple_cohorts")
                else None
            )
            if disease:
                supported.append((0.6, disease, m))
            else:
                unresolved.append(m)
    # Incompatible phenotype requirements cannot be rescued by another gene hit.
    phenotype_conflict = (
        msi in {"high", "msi-high", "msi high", "msi-h"}
        and any(re.search(MSI_LOW, m["text"], re.I) for m in inclusion)
        and not any(
            re.search(MSI_HIGH, m["text"], re.I)
            and not re.search(MSI_LOW, m["text"], re.I)
            for m in inclusion
        )
    )
    if phenotype_conflict:
        return {
            "supported": [],
            "restricted": True,
            "references": [m for m in inclusion if re.search(MSI_LOW, m["text"], re.I)],
            "reason": "Registry requires a different MSI/MMR phenotype; no supported applicable cohort established.",
        }
    return {
        "supported": supported,
        "restricted": targeted and not supported,
        "references": unresolved,
        "reason": "No same-cohort disease and molecular support established; specific inclusion constraints override broad titles. This is not a definitive eligibility decision.",
    }
