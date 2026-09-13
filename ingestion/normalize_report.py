"""Convert only grounded, reviewed extraction into the downstream contract."""

import re
from collections import Counter

from ingestion.grounding import (
    check_finding,
    citation_present,
    compact,
    numeric_supported,
)
from normalization.disease import DiseaseRegistry
from schemas.molecular_profile import (
    CopyNumber,
    Disease,
    Fusion,
    MolecularProfile,
    ReportMetadata,
    Variant,
)

AA = dict(
    zip(
        "Ala Arg Asn Asp Cys Gln Glu Gly His Ile Leu Lys Met Phe Pro Ser Thr Trp Tyr Val Ter".split(),
        "A R N D C Q E G H I L K M F P S T W Y V *".split(),
    )
)


def protein_notation(value):
    value = value.removeprefix("p.")
    for long, short in AA.items():
        value = re.sub(long, lambda _: short, value)
    return value


def normalize_report(extracted, review, document, registry):
    warnings, rejected = list(document.warnings), []
    counts = Counter(r.finding_index for r in review.findings)
    reviews = {r.finding_index: r for r in review.findings}
    if any(i >= len(extracted.findings) for i in reviews):
        warnings.append("Reviewer returned an out-of-range finding index.")
    bad_fields = set(review.fields_requiring_review)

    def field(name):
        value = getattr(extracted, name)
        if value is None:
            return None
        if (
            name in bad_fields
            or not citation_present(value.evidence, document)
            or compact(value.value) not in compact(value.evidence.quote)
        ):
            warnings.append(f"{name}: unsupported or flagged scalar field withheld")
            return None
        return value.value

    diagnosis = field("diagnosis")
    normalized = DiseaseRegistry().resolve(diagnosis) if diagnosis else {}
    if not normalized.get("normalized"):
        warnings.append(
            "Diagnosis needs review: no unambiguous NCIt mapping; original wording retained."
        )
    profile = MolecularProfile(
        schema_version="0.2",
        report=ReportMetadata(
            vendor=field("vendor"),
            assay=field("assay"),
            sample_type=field("sample_type"),
        ),
        disease=Disease(
            raw_text=diagnosis or "",
            histology=field("histology"),
            stage=field("stage"),
            **normalized,
        ),
    )
    seen = set()
    for i, finding in enumerate(extracted.findings):
        gene, reasons = check_finding(finding, document, registry)
        verdict = reviews.get(i)
        if counts[i] != 1 or verdict is None or verdict.verdict != "supported":
            reasons.append(
                "Independent review did not uniquely support this finding"
                + (f": {verdict.reason}" if verdict else "")
            )
        if reasons:
            rejected.append(
                {
                    "finding": finding.model_dump(),
                    "reasons": reasons,
                    "gene_resolution": gene.model_dump(),
                }
            )
            continue
        identity = (gene.symbol, finding.kind, finding.alteration, finding.origin)
        if identity in seen:
            continue
        seen.add(identity)
        section = finding.section_evidence.quote.lower()
        optional_flags = set(verdict.fields_requiring_review)
        if optional_flags:
            warnings.append(
                f"{gene.symbol} {finding.alteration}: review optional fields {', '.join(sorted(optional_flags))}; core finding retained."
            )
        origin = (
            "clonal_hematopoiesis"
            if re.fullmatch(
                r"clonal hematopoiesis(?: findings)?|CH", section.strip(), re.I
            )
            else "germline"
            if re.fullmatch(
                r"germline(?: findings| variant details)?", section.strip(), re.I
            )
            else finding.origin
        )
        possible_ch = (
            finding.origin == "clonal_hematopoiesis" or origin == "clonal_hematopoiesis"
        )
        if "origin" in optional_flags and origin not in {
            "germline",
            "clonal_hematopoiesis",
        }:
            origin = "unknown"
        classification = (
            "VUS"
            if finding.report_category == "VUS"
            or re.fullmatch(
                r"(?:variants of (?:uncertain|unknown) significance|VUS)(?: somatic| germline)?",
                section.strip(),
                re.I,
            )
            else finding.classification
        )
        if "classification" in optional_flags:
            classification = "unknown"
        common = dict(
            gene=gene.symbol,
            hgnc_id=gene.hgnc_id,
            gene_validation=gene.status,
            classification=None if classification == "unknown" else classification,
            origin=origin,
            requires_review=bool(optional_flags & {"origin", "classification"}),
            potential_ch=possible_ch,
            source_text=finding.evidence.quote,
            source_page=finding.evidence.page,
        )
        if finding.kind == "fusion":
            partner = registry.resolve(finding.partner) if finding.partner else None
            profile.biomarkers.fusions.append(
                Fusion(
                    **common,
                    partner=partner.symbol if partner else None,
                    partner_hgnc_id=partner.hgnc_id if partner else None,
                )
            )
        elif finding.kind == "copy_number":
            profile.biomarkers.copy_number.append(
                CopyNumber(**common, alteration=finding.alteration)
            )
        elif finding.kind in {"snv_indel", "splice"}:
            protein_match = re.search(r"\bp\.([^\s,)]+)", finding.alteration)
            dna_match = re.search(r"\bc\.([^\s,)]+)", finding.alteration)
            protein = (
                protein_match.group(1)
                if protein_match
                else finding.alteration
                if re.fullmatch(r"[A-Z][a-z]{0,2}\d+[^\s]*", finding.alteration)
                else None
            )
            vaf = None
            if (
                finding.vaf
                and "vaf" not in optional_flags
                and numeric_supported(finding.vaf, document)
                and finding.vaf.evidence.page == finding.evidence.page
            ):
                unit = finding.vaf.unit.lower()
                vaf = (
                    finding.vaf.value / 100
                    if unit in {"%", "percent", "percentage"}
                    else finding.vaf.value
                    if unit == "fraction"
                    else None
                )
                if vaf is None or not 0 <= vaf <= 1:
                    warnings.append(
                        f"{gene.symbol}: unsupported VAF unit or range; value withheld"
                    )
                    vaf = None
            if finding.vaf and vaf is None:
                warnings.append(
                    f"{gene.symbol}: VAF withheld because evidence, temporal linkage, or exact value is unconfirmed."
                )
            profile.biomarkers.snv_indel.append(
                Variant(
                    **common,
                    protein_change=protein_notation(protein) if protein else None,
                    hgvs_c=dna_match.group(0) if dna_match else None,
                    vaf=vaf,
                    raw_alteration=finding.alteration,
                    alteration_type=finding.kind,
                )
            )
        else:
            rejected.append(
                {
                    "finding": finding.model_dump(),
                    "reasons": ["Unsupported alteration type requires review"],
                }
            )
    msi = field("msi")
    if msi:
        key = msi.lower().strip()
        profile.biomarkers.msi.status = {
            "ms-stable": "stable",
            "msi stable": "stable",
            "msi-high": "high",
            "msi - not detected": "not_detected",
            "not detected": "not_detected",
        }.get(key, key)
    for name in ("tmb", "tumor_fraction"):
        value = getattr(extracted, name)
        if value is None:
            continue
        if name in bad_fields or not numeric_supported(value, document):
            warnings.append(f"{name}: unsupported numerical evidence; value withheld")
            continue
        if (
            name == "tmb"
            and value.unit.lower().replace(" ", "")
            in {"mut/mb", "muts/mb", "mutations/mb"}
            and value.value >= 0
        ):
            profile.biomarkers.tmb.value = value.value
        elif name == "tumor_fraction" and value.unit.lower() in {
            "%",
            "percent",
            "fraction",
        }:
            fraction = (
                value.value if value.unit.lower() == "fraction" else value.value / 100
            )
            if 0 <= fraction <= 1:
                profile.biomarkers.tumor_fraction = fraction
            else:
                warnings.append("tumor_fraction: out-of-range value withheld")
        else:
            warnings.append(f"{name}: unsupported unit or value withheld")
    for note in extracted.technical_notes:
        if (
            "technical_notes" not in bad_fields
            and citation_present(note.evidence, document)
            and compact(note.value) in compact(note.evidence.quote)
        ):
            profile.technical_notes.append(note.value)
    negative = field("negative_result")
    if negative:
        profile.technical_notes.append(negative)
        if (
            profile.biomarkers.snv_indel
            or profile.biomarkers.copy_number
            or profile.biomarkers.fusions
        ) and re.fullmatch(
            r"No (?:reportable )?(?:pathogenic )?(?:genomic )?(?:variants|alterations) (?:were )?(?:found|detected)\.?",
            negative.strip(),
            re.I,
        ):
            warnings.append(
                "Report contains both a negative statement and findings; reconcile sections manually."
            )
    warnings.extend(
        f"Reviewer reports omitted finding: {f}" for f in review.missing_findings
    )
    warnings.extend(f"Reviewer flags field: {f}" for f in bad_fields)
    if rejected:
        warnings.append(
            f"{len(rejected)} proposed findings held out for review; do not interpret this as a negative report."
        )
    profile.technical_notes.extend(warnings)
    return profile, rejected, warnings
