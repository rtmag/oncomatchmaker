from ingestion.grounding import anchor_scalar_evidence, check_finding
from ingestion.model_client import PROMPT_VERSION, ExtractionError, SolExtractor
from ingestion.normalize_report import normalize_report
from ingestion.pdf_reader import read_document
from normalization.genes import get_registry
from schemas.extraction import ExtractionReview, FindingReview, IngestionResult

FAST_MODE_WARNING = (
    "Fast extraction used patient-result sections plus deterministic evidence validation; "
    "an independent completeness review was not performed. Confirm the profile "
    "against the source report before acting on trial results."
)


def _deterministic_review(extracted, document, registry):
    """Build a fail-closed review from local evidence checks, without another LLM call."""
    findings = []
    for index, finding in enumerate(extracted.findings):
        errors = check_finding(finding, document, registry)[1]
        findings.append(
            FindingReview(
                finding_index=index,
                verdict="unsupported" if errors else "supported",
                reason="; ".join(errors)
                if errors
                else "Passed deterministic source and HGNC checks",
            )
        )
    return ExtractionReview(
        findings=findings,
        fields_requiring_review=[],
        missing_findings=[],
    )


def ingest_report(
    pdf_path,
    *,
    extractor=None,
    registry=None,
    ocr=False,
    reader_mode="fast",
    extraction_mode="audited",
):
    if extraction_mode not in {"audited", "fast"}:
        raise ValueError("extraction_mode must be 'audited' or 'fast'")
    document = read_document(pdf_path, ocr=ocr, mode=reader_mode)
    if any(p.extraction_method == "unreadable" for p in document.pages):
        raise ExtractionError(
            "Report has unreadable pages. Enable OCR or supply a searchable PDF; partial extraction is not accepted."
        )
    registry = registry or get_registry()
    owned = extractor is None
    extractor = extractor or (
        SolExtractor(
            vision_pages=0,
            reasoning_effort="low",
            max_output_tokens=8000,
            service_tier="priority",
            select_patient_sections=True,
        )
        if extraction_mode == "fast"
        else SolExtractor()
    )
    try:
        extracted = extractor.extract(document, pdf_path=pdf_path)
        anchored = anchor_scalar_evidence(extracted, document)
        repair_errors = [
            {"finding_index": i, "errors": errors}
            for i, finding in enumerate(extracted.findings)
            if (errors := check_finding(finding, document, registry)[1])
        ]
        repaired = bool(
            extraction_mode == "audited"
            and repair_errors
            and hasattr(extractor, "repair")
        )
        if repaired:
            extracted = extractor.repair(document, extracted, repair_errors)
            anchored.extend(anchor_scalar_evidence(extracted, document))
        review = (
            _deterministic_review(extracted, document, registry)
            if extraction_mode == "fast"
            else extractor.review(document, extracted)
        )
        profile, rejected, warnings = normalize_report(
            extracted, review, document, registry
        )
        if extraction_mode == "fast":
            warnings.append(FAST_MODE_WARNING)
            profile.technical_notes.append(FAST_MODE_WARNING)
    finally:
        if owned:
            extractor.close()
    profile.ingestion_provenance = {
        "source_sha256": document.sha256,
        "reader_version": document.reader_version,
        "reader_mode": reader_mode,
        "extraction_mode": extraction_mode,
        "model": extractor.model,
        "reasoning_effort": getattr(extractor, "reasoning_effort", None),
        "service_tier": getattr(extractor, "service_tier", None),
        "vision_pages": getattr(extractor, "vision_pages", None),
        "prompt_version": PROMPT_VERSION,
        "section_selection": getattr(extractor, "section_selection", None),
        "model_calls": getattr(extractor, "calls", []),
        "hgnc_snapshot_sha256": registry.metadata.get("upstream_sha256"),
        "requires_review": extraction_mode == "fast" or bool(warnings or rejected),
        "independent_completeness_review_performed": extraction_mode == "audited",
        "scalar_quotes_narrowed_to_verbatim_value": anchored,
        "model_repair_performed": repaired,
        "warnings": warnings,
        "rejected_findings": rejected,
        "field_evidence": extracted.model_dump(exclude={"findings"}),
        "review": review.model_dump(),
    }
    return IngestionResult(
        profile=profile.model_dump(),
        extracted=extracted,
        review=review,
        rejected_findings=rejected,
        warnings=warnings,
        source_sha256=document.sha256,
        model=extractor.model,
        prompt_version=PROMPT_VERSION,
        hgnc_metadata=registry.metadata,
        reader_version=document.reader_version,
    )


def parse_report(pdf_path, *, reader_mode="fast"):
    from schemas.molecular_profile import MolecularProfile

    return MolecularProfile.model_validate(
        ingest_report(pdf_path, reader_mode=reader_mode).profile
    )
