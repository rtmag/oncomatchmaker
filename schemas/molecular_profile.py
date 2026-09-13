"""Versioned contract shared by ingestion and matching. Unknown is never negative."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ReportMetadata(Model):
    vendor: str | None = None
    assay: str | None = None
    sample_type: str | None = None
    report_date: str | None = None


class Disease(Model):
    raw_text: str = ""
    normalized: str | None = None
    histology: str | None = None
    stage: str | None = None
    ontology_id: str | None = None
    normalization_status: str = "unverified"
    synonyms: list[str] = Field(default_factory=list)


class Location(Model):
    city: str | None = None
    country: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)

    @model_validator(mode="after")
    def coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Supply both latitude and longitude, or neither")
        return self


class PatientContext(Model):
    age: int | None = Field(None, ge=0, le=120)
    sex: str | None = None
    prior_therapies: list[str] = Field(default_factory=list)
    # An empty list in the original contract means unrecorded, not treatment-naive.
    prior_therapies_known: bool = False
    ecog: int | None = Field(None, ge=0, le=5)
    location: Location = Field(default_factory=Location)


class Variant(Model):
    gene: str
    reported_gene: str | None = None
    gene_synonyms: list[str] = Field(default_factory=list)
    requires_review: bool = False
    raw_alteration: str | None = None
    alteration_type: str = "snv_indel"
    protein_change: str | None = None
    hgvs_c: str | None = None
    hgvs_p: str | None = None
    vaf: float | None = Field(None, ge=0, le=1)
    classification: str | None = None
    source_text: str = ""
    potential_ch: bool = False
    hgnc_id: str | None = None
    gene_validation: str = "unverified"
    origin: str = "unknown"
    source_page: int | None = None
    report_category: str = "detected"
    zygosity: str = "unknown"


class CopyNumber(Model):
    gene: str
    reported_gene: str | None = None
    gene_synonyms: list[str] = Field(default_factory=list)
    requires_review: bool = False
    alteration: str
    classification: str | None = None
    source_text: str = ""
    potential_ch: bool = False
    hgnc_id: str | None = None
    gene_validation: str = "unverified"
    origin: str = "unknown"
    source_page: int | None = None
    report_category: str = "detected"
    zygosity: str = "unknown"


class Fusion(Model):
    gene: str
    reported_gene: str | None = None
    gene_synonyms: list[str] = Field(default_factory=list)
    requires_review: bool = False
    partner: str | None = None
    classification: str | None = None
    source_text: str = ""
    potential_ch: bool = False
    hgnc_id: str | None = None
    gene_validation: str = "unverified"
    partner_hgnc_id: str | None = None
    origin: str = "unknown"
    source_page: int | None = None
    report_category: str = "detected"
    zygosity: str = "unknown"


class MSI(Model):
    status: str | None = None


class TMB(Model):
    value: float | None = Field(None, ge=0)
    unit: str = "mut/Mb"
    classification: str | None = None


class Biomarkers(Model):
    snv_indel: list[Variant] = Field(default_factory=list)
    copy_number: list[CopyNumber] = Field(default_factory=list)
    fusions: list[Fusion] = Field(default_factory=list)
    msi: MSI = Field(default_factory=MSI)
    tmb: TMB = Field(default_factory=TMB)
    tumor_fraction: float | None = Field(None, ge=0, le=1)


class ExtractionConfidence(Model):
    overall: float | None = Field(None, ge=0, le=1)


class MolecularProfile(Model):
    schema_version: Literal["0.1", "0.2", "0.3"] = "0.3"
    report: ReportMetadata = Field(default_factory=ReportMetadata)
    disease: Disease
    patient_context: PatientContext = Field(default_factory=PatientContext)
    biomarkers: Biomarkers = Field(default_factory=Biomarkers)
    technical_notes: list[str] = Field(default_factory=list)
    negative_findings: list[str] = Field(default_factory=list)
    assay_limitations: list[str] = Field(default_factory=list)
    extraction_confidence: ExtractionConfidence = Field(
        default_factory=ExtractionConfidence
    )
    ingestion_provenance: dict | None = None
