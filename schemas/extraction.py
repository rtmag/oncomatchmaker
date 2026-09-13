"""Evidence-bearing model output. No model-generated HGNC or ontology IDs."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from schemas.molecular_profile import Model


class Citation(Model):
    page: int = Field(ge=1)
    quote: str = Field(min_length=1)


class ReportField(Model):
    value: str
    evidence: Citation


class NumericField(Model):
    value: float
    unit: str
    evidence: Citation


class ExtractedFinding(Model):
    gene: str
    alteration: str
    kind: Literal["snv_indel", "copy_number", "fusion", "splice", "other"]
    partner: str | None
    classification: Literal[
        "pathogenic", "likely pathogenic", "VUS", "benign", "likely benign", "unknown"
    ]
    classification_evidence: Citation | None
    origin: Literal["somatic", "germline", "clonal_hematopoiesis", "unknown"]
    report_category: Literal[
        "detected", "VUS", "negative", "assay_gene_list", "literature", "unknown"
    ]
    evidence: Citation
    section_evidence: Citation
    vaf: NumericField | None


class ExtractedReport(Model):
    vendor: ReportField | None
    assay: ReportField | None
    sample_type: ReportField | None
    diagnosis: ReportField | None
    histology: ReportField | None
    stage: ReportField | None
    findings: list[ExtractedFinding]
    msi: ReportField | None
    tmb: NumericField | None
    tumor_fraction: NumericField | None
    technical_notes: list[ReportField]
    negative_result: ReportField | None


class FindingReview(Model):
    finding_index: int = Field(ge=0)
    verdict: Literal["supported", "unsupported", "uncertain"]
    reason: str
    fields_requiring_review: list[Literal["vaf", "classification", "origin"]] = Field(
        default_factory=list
    )


class ExtractionReview(Model):
    findings: list[FindingReview]
    fields_requiring_review: list[str]
    missing_findings: list[str]


class PDFPage(Model):
    number: int
    text: str
    extraction_method: Literal["native", "ocr", "unreadable"]
    blocks: list[dict]
    warnings: list[str] = Field(default_factory=list)


class PDFDocument(Model):
    sha256: str
    reader_version: str = "pymupdf-blocks-1"
    pages: list[PDFPage]
    warnings: list[str] = Field(default_factory=list)

    @property
    def text(self):
        return "\n\n".join(f"[PAGE {page.number}]\n{page.text}" for page in self.pages)


class IngestionResult(Model):
    profile: dict
    extracted: ExtractedReport
    review: ExtractionReview
    rejected_findings: list[dict]
    warnings: list[str]
    source_sha256: str
    model: str
    prompt_version: str
    hgnc_metadata: dict
    reader_version: str = "pymupdf-blocks-1"
