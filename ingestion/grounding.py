"""Independent checks for source presence and valid gene nomenclature."""

import re
import unicodedata


def compact(value):
    return " ".join(unicodedata.normalize("NFKC", value).split())


def citation_present(citation, document):
    if citation is None or not 1 <= citation.page <= len(document.pages):
        return False
    quote = compact(citation.quote)
    return bool(quote) and quote in compact(document.pages[citation.page - 1].text)


def anchor_scalar_evidence(extracted, document):
    """Narrow a noncontiguous scalar quote to its verbatim value, never repair findings.

    Layout-aware models sometimes join a label and value across intervening text.
    A literal value present on the same cited page is a legitimate narrower quote;
    the second model pass still checks its meaning in the full document.
    """
    anchored = []
    for name in (
        "vendor",
        "assay",
        "sample_type",
        "diagnosis",
        "histology",
        "stage",
        "msi",
        "negative_result",
    ):
        field = getattr(extracted, name)
        if (
            field
            and not citation_present(field.evidence, document)
            and 1 <= field.evidence.page <= len(document.pages)
        ):
            value = compact(field.value)
            if (
                value
                and value in compact(field.evidence.quote)
                and value in compact(document.pages[field.evidence.page - 1].text)
            ):
                field.evidence.quote = field.value
                anchored.append(name)
    return anchored


def token_present(token, quote):
    return bool(
        re.search(
            r"(?<![A-Za-z0-9])" + re.escape(compact(token)) + r"(?![A-Za-z0-9])",
            compact(quote),
            re.I,
        )
    )


def numeric_supported(field, document):
    if not citation_present(field.evidence, document):
        return False
    if re.search(
        r"[<>≤≥]\s*\d|(?:less than|greater than|at least|at most)\s+\d",
        field.evidence.quote,
        re.I,
    ):
        return False
    numbers = re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", field.evidence.quote)
    return any(float(number) == field.value for number in numbers)


def check_finding(finding, document, registry):
    reasons = []
    gene = registry.resolve(finding.gene)
    if gene.symbol is None:
        reasons.append(f"HGNC {gene.status}: {finding.gene}")
    if not citation_present(finding.evidence, document):
        reasons.append("Finding quote does not match the cited page")
    if (
        not citation_present(finding.section_evidence, document)
        or finding.section_evidence.page != finding.evidence.page
    ):
        reasons.append("Section heading is not grounded on the finding's page")
    for token in (finding.gene, finding.alteration):
        if not token.strip() or not token_present(token, finding.evidence.quote):
            reasons.append(f"Reported token absent from finding quote: {token}")
    if finding.kind == "fusion" and finding.partner:
        partner = registry.resolve(finding.partner)
        if partner.symbol is None or not token_present(
            finding.partner, finding.evidence.quote
        ):
            reasons.append("Fusion partner is not HGNC validated and source grounded")
    if finding.classification != "unknown":
        if not citation_present(finding.classification_evidence, document):
            reasons.append("Classification lacks source evidence")
        elif not re.search(
            r"\bVUS\b|(?:uncertain|unknown) significance"
            if finding.classification == "VUS"
            else re.escape(finding.classification),
            finding.classification_evidence.quote,
            re.I,
        ):
            reasons.append(
                "Claimed classification is absent from the classification quote"
            )
        elif finding.classification == "pathogenic" and re.search(
            r"likely pathogenic|uncertain significance|\bVUS\b|non.pathogenic",
            finding.classification_evidence.quote,
            re.I,
        ):
            reasons.append(
                "Classification evidence is uncertain or weaker than pathogenic"
            )
    if finding.report_category not in {"detected", "VUS"}:
        reasons.append("Not a confirmed patient finding section")
    section = finding.section_evidence.quote.lower()
    if any(
        s in section
        for s in (
            "genes tested",
            "genes assayed",
            "genes interrogated",
            "references",
            "bibliography",
        )
    ):
        reasons.append("Source section describes assay coverage or literature")
    if re.search(
        r"not detected|no reportable|negative for|wild.type",
        finding.evidence.quote,
        re.I,
    ):
        reasons.append("Finding quote contains a negative or conflicting result")
    return gene, reasons
