from ingestion.grounding import anchor_scalar_evidence, check_finding
from ingestion.model_client import PROMPT_VERSION, ExtractionError, SolExtractor
from ingestion.normalize_report import normalize_report
from ingestion.pdf_reader import read_document
from normalization.genes import get_registry
from schemas.extraction import IngestionResult


def ingest_report(
    pdf_path, *, extractor=None, registry=None, ocr=False, full_layout=False
):
    document = read_document(
        pdf_path, ocr=ocr, row_order_pages=None if full_layout else ()
    )
    if any(p.extraction_method == "unreadable" for p in document.pages):
        raise ExtractionError(
            "Report has unreadable pages. Enable OCR or supply a searchable PDF; partial extraction is not accepted."
        )
    registry = registry or get_registry()
    owned = extractor is None
    extractor = extractor or SolExtractor()
    try:
        extracted = extractor.extract(document, pdf_path=pdf_path)
        anchored = anchor_scalar_evidence(extracted, document)
        repair_errors = [
            {"finding_index": i, "errors": errors}
            for i, finding in enumerate(extracted.findings)
            if (errors := check_finding(finding, document, registry)[1])
        ]
        repaired = bool(repair_errors and hasattr(extractor, "repair"))
        if repaired:
            if not full_layout:
                failed_pages = {
                    citation.page
                    for error in repair_errors
                    for citation in (
                        extracted.findings[error["finding_index"]].evidence,
                        extracted.findings[error["finding_index"]].section_evidence,
                    )
                    if citation is not None
                }
                document = read_document(
                    pdf_path, ocr=ocr, row_order_pages=failed_pages
                )
            extracted = extractor.repair(document, extracted, repair_errors)
            anchored.extend(anchor_scalar_evidence(extracted, document))
        review = extractor.review(document, extracted)
        profile, rejected, warnings = normalize_report(
            extracted, review, document, registry
        )
    finally:
        if owned:
            extractor.close()
    profile.ingestion_provenance = {
        "source_sha256": document.sha256,
        "reader_version": document.reader_version,
        "model": extractor.model,
        "prompt_version": PROMPT_VERSION,
        "hgnc_snapshot_sha256": registry.metadata.get("upstream_sha256"),
        "requires_review": bool(warnings or rejected),
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


def parse_report(pdf_path):
    from schemas.molecular_profile import MolecularProfile

    return MolecularProfile.model_validate(ingest_report(pdf_path).profile)
