import json
import threading
from pathlib import Path
from unittest.mock import patch

import httpx
import pymupdf
import pytest

from ingestion.grounding import anchor_scalar_evidence, check_finding
from ingestion.model_client import ExtractionError, SolExtractor, strict_schema
from ingestion.normalize_report import normalize_report, protein_notation
from ingestion.pdf_reader import PDFReadError, read_document
from ingestion.pipeline import ingest_report
from normalization.disease import DiseaseRegistry
from normalization.genes import HGNCRegistry, get_registry
from schemas.extraction import (
    Citation,
    ExtractedFinding,
    ExtractedReport,
    ExtractionReview,
    FindingReview,
    NumericField,
    PDFDocument,
    PDFPage,
    ReportField,
)
from schemas.molecular_profile import MolecularProfile
from trials.search import actionable_findings


@pytest.fixture
def document():
    text = "Diagnosis: NSCLC\nSomatic Findings\nKRAS G12C Pathogenic 7.7%\nGenes Tested\nEGFR\nNo reportable fusions.\nGermline Findings\nVUS\nMicrosatellite Status: Stable"
    return PDFDocument(
        sha256="abc",
        pages=[PDFPage(number=1, text=text, extraction_method="native", blocks=[])],
    )


@pytest.fixture
def finding():
    return ExtractedFinding(
        gene="KRAS",
        alteration="G12C",
        kind="snv_indel",
        partner=None,
        classification="pathogenic",
        classification_evidence=Citation(page=1, quote="Pathogenic"),
        origin="somatic",
        report_category="detected",
        evidence=Citation(page=1, quote="KRAS G12C Pathogenic 7.7%"),
        section_evidence=Citation(page=1, quote="Somatic Findings"),
        vaf=NumericField(value=7.7, unit="%", evidence=Citation(page=1, quote="7.7%")),
    )


def extraction(findings=None):
    fields = {name: None for name in ExtractedReport.model_fields}
    fields.update(
        findings=findings or [],
        technical_notes=[],
        diagnosis=ReportField(
            value="NSCLC", evidence=Citation(page=1, quote="Diagnosis: NSCLC")
        ),
    )
    return ExtractedReport(**fields)


def review(findings):
    return ExtractionReview(
        findings=[
            FindingReview(
                finding_index=i, verdict="supported", reason="Source supported"
            )
            for i, _ in enumerate(findings)
        ],
        fields_requiring_review=[],
        missing_findings=[],
    )


def test_hgnc_approved_alias_previous_ambiguous():
    registry = HGNCRegistry(
        [
            {
                "symbol": "GENE1",
                "hgnc_id": "HGNC:1",
                "status": "Approved",
                "alias_symbol": ["ALIAS", "SHARED"],
                "prev_symbol": ["OLD"],
            },
            {
                "symbol": "GENE2",
                "hgnc_id": "HGNC:2",
                "status": "Approved",
                "alias_symbol": ["SHARED"],
            },
        ]
    )
    assert registry.resolve("gene1").status == "approved"
    assert registry.resolve("ALIAS").symbol == "GENE1"
    assert registry.resolve("OLD").status == "previous"
    assert registry.resolve("SHARED").status == "ambiguous"
    assert registry.resolve("GENE11").status == "unknown"
    assert registry.resolve("SHARED").symbol is None


def test_real_hgnc_snapshot():
    registry = get_registry()
    assert len(registry.approved) > 40000
    assert registry.resolve("KRAS").hgnc_id == "HGNC:6407"
    assert registry.resolve("HER2").symbol == "ERBB2"
    assert registry.resolve("FAKEONCOGENE999").symbol is None
    assert registry.metadata["upstream_sha256"]


@pytest.mark.parametrize(
    "change",
    [
        dict(gene="FAKEONCOGENE999"),
        dict(gene="EGFR"),
        dict(alteration="G12D"),
        dict(evidence=Citation(page=2, quote="KRAS G12C Pathogenic 7.7%")),
        dict(section_evidence=Citation(page=1, quote="Genes Tested")),
        dict(report_category="literature"),
        dict(classification_evidence=Citation(page=1, quote="Somatic Findings")),
    ],
)
def test_hallucinations_and_assay_lists_rejected(document, finding, change):
    changed = finding.model_copy(update=change)
    assert check_finding(changed, document, get_registry())[1]


def test_supported_finding_with_vaf_and_provenance(document, finding):
    raw = extraction([finding])
    profile, rejected, warnings = normalize_report(
        raw, review(raw.findings), document, get_registry()
    )
    assert not rejected
    variant = profile.biomarkers.snv_indel[0]
    assert variant.vaf == pytest.approx(0.077)
    assert variant.hgnc_id == "HGNC:6407" and variant.source_page == 1
    assert profile.disease.ontology_id == "NCIT:C2926"
    assert profile.schema_version == "0.3"
    assert variant.reported_gene == "KRAS"
    assert "KRAS2" in variant.gene_synonyms


def test_uncertain_or_duplicate_review_holds_finding(document, finding):
    raw = extraction([finding])
    audited = review(raw.findings)
    audited.findings[0].verdict = "uncertain"
    assert normalize_report(raw, audited, document, get_registry())[1]
    audited = review(raw.findings)
    audited.findings *= 2
    assert normalize_report(raw, audited, document, get_registry())[1]


def test_germline_vus_not_tumor_targets(document, finding):
    finding.section_evidence.quote = "Germline Findings"
    raw = extraction([finding])
    profile, _, _ = normalize_report(
        raw, review(raw.findings), document, get_registry()
    )
    assert profile.biomarkers.snv_indel[0].origin == "germline"
    assert not actionable_findings(profile)
    finding.section_evidence.quote = "VUS"
    profile, _, _ = normalize_report(
        raw, review(raw.findings), document, get_registry()
    )
    assert profile.biomarkers.snv_indel[0].classification == "VUS"
    assert not actionable_findings(profile)


def test_no_invented_cancer_subtype():
    registry = DiseaseRegistry()
    assert registry.resolve("NSCLC")["ontology_id"] == "NCIT:C2926"
    assert registry.resolve("Adenocarcinoma")["ontology_id"] == "NCIT:C2852"
    assert (
        registry.resolve("Metastatic carcinoma of uncertain primary")["normalized"]
        is None
    )


def test_mixed_tumor_germline_heading_does_not_override_origin(document, finding):
    heading = "DNA Sequencing - Tumor and Germline Results"
    document.pages[0].text += "\n" + heading
    finding.section_evidence.quote = heading
    raw = extraction([finding])
    profile, _, _ = normalize_report(
        raw, review(raw.findings), document, get_registry()
    )
    assert profile.biomarkers.snv_indel[0].origin == "somatic"


def test_ch_is_retained_but_never_used_as_tumor_target(document, finding):
    document.pages[0].text += "\nClonal Hematopoiesis"
    finding.origin = "clonal_hematopoiesis"
    finding.section_evidence.quote = "Clonal Hematopoiesis"
    raw = extraction([finding])
    profile, _, _ = normalize_report(
        raw, review(raw.findings), document, get_registry()
    )
    assert profile.biomarkers.snv_indel[0].potential_ch
    assert not actionable_findings(profile)


def test_protein_notation():
    assert protein_notation("p.Leu858Arg") == "L858R"
    assert protein_notation("p.G12C") == "G12C"


def test_scalar_anchor_does_not_invent_source(document):
    raw = extraction()
    raw.diagnosis.evidence.quote = "Diagnosis: \nintervening fake label NSCLC"
    assert anchor_scalar_evidence(raw, document) == ["diagnosis"]
    assert raw.diagnosis.evidence.quote == "NSCLC"
    raw.diagnosis.value = "Melanoma"
    raw.diagnosis.evidence.quote = "Diagnosis: Melanoma"
    assert anchor_scalar_evidence(raw, document) == []


def test_pdf_reader_and_invalid_files(tmp_path):
    path = tmp_path / "report.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text(
            (40, 40), "Diagnosis: NSCLC. Somatic Findings. KRAS G12C Pathogenic."
        )
        pdf.save(path)
    doc = read_document(path)
    assert len(doc.pages) == 1 and doc.pages[0].blocks
    assert doc.sha256 and "KRAS" in doc.text
    with pytest.raises(PDFReadError):
        read_document(path, max_pages=0)
    bad = tmp_path / "bad.pdf"
    bad.write_text("not a PDF")
    with pytest.raises(PDFReadError):
        read_document(bad)
    assert read_document(path, mode="fast").reader_version == "pymupdf-blocks-fast-1.0"
    assert read_document(path, mode="safe").reader_version.startswith(
        "dual-native-safe"
    )
    with pytest.raises(ValueError, match="mode"):
        read_document(path, mode="invalid")
    blank = tmp_path / "blank.pdf"
    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.save(blank)
    assert read_document(blank).pages[0].extraction_method == "unreadable"
    with pytest.raises(ExtractionError, match="unreadable"):
        ingest_report(blank)


def test_safe_mode_deduplicates_duplicate_glyphs(tmp_path):
    path = tmp_path / "duplicate.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((40, 40), "KRAS G12C pathogenic molecular finding")
        page.insert_text((40, 40), "KRAS G12C pathogenic molecular finding")
        pdf.save(path)
    fast = read_document(path, mode="fast")
    safe = read_document(path, mode="safe")
    row_order = safe.text.split("[ORIGINAL BLOCK-ORDER TEXT]")[0]
    assert row_order.count("KRAS G12C") == 1
    assert fast.text.count("KRAS G12C") == 2


def test_pipeline_two_passes(document, finding):
    class FakeExtractor:
        model = "fake-for-tests"

        def extract(self, document, pdf_path=None):
            return extraction([finding])

        def review(self, document, extracted):
            return review(extracted.findings)

    with patch("ingestion.pipeline.read_document", return_value=document):
        result = ingest_report("unused", extractor=FakeExtractor())
    profile = MolecularProfile.model_validate(result.profile)
    assert profile.ingestion_provenance["source_sha256"] == "abc"
    assert profile.biomarkers.snv_indel[0].hgnc_id


def test_fast_pipeline_uses_one_model_pass_and_requires_review(document, finding):
    class FakeExtractor:
        model = "fake-for-tests"
        reasoning_effort = "low"
        service_tier = "priority"
        vision_pages = 0

        def __init__(self):
            self.review_called = False

        def extract(self, document, pdf_path=None):
            return extraction([finding])

        def review(self, document, extracted):
            self.review_called = True
            return review(extracted.findings)

    extractor = FakeExtractor()
    with patch("ingestion.pipeline.read_document", return_value=document):
        result = ingest_report("unused", extractor=extractor, extraction_mode="fast")
    profile = MolecularProfile.model_validate(result.profile)
    assert not extractor.review_called
    assert profile.biomarkers.snv_indel[0].gene == "KRAS"
    assert profile.ingestion_provenance["extraction_mode"] == "fast"
    assert profile.ingestion_provenance["requires_review"] is True
    assert (
        profile.ingestion_provenance["independent_completeness_review_performed"]
        is False
    )


def test_model_request_schema_and_result(document):
    calls = []

    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert payload["model"] == "gpt-5.6-sol" and payload["store"] is False
        assert payload["text"]["format"]["strict"]
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": extraction().model_dump_json(),
                            }
                        ],
                    }
                ],
            },
        )

    client = SolExtractor(
        api_key="test-only",
        http=httpx.Client(
            base_url="https://example.test", transport=httpx.MockTransport(handler)
        ),
    )
    assert not client.extract(document).findings
    assert len(calls) == 1
    schema = strict_schema(ExtractedReport)
    assert set(schema["required"]) == set(schema["properties"])


@pytest.mark.parametrize(
    "response",
    [
        {"status": "incomplete"},
        {
            "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "refusal", "refusal": "No"}]}
            ],
        },
        {"status": "completed", "output": []},
    ],
)
def test_model_incomplete_refusal_malformed_fail_closed(document, response):
    client = SolExtractor(
        api_key="test-only",
        http=httpx.Client(
            base_url="https://example.test",
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)),
        ),
    )
    with pytest.raises(ExtractionError):
        client.extract(document)


def test_corpus_native_reader():
    files = list((Path(__file__).parents[1] / "evaluation" / "corpus").glob("*.pdf"))
    if not files:
        pytest.skip("Local public report corpus is not distributed")
    for path in files:
        doc = read_document(path)
        assert doc.pages and all(p.extraction_method == "native" for p in doc.pages)


@pytest.mark.parametrize("appendix_failure", [False, True])
def test_parallel_appendix_preserves_vus_and_fails_closed(finding, appendix_failure):
    document = PDFDocument(
        sha256="test",
        pages=[
            PDFPage(
                number=1,
                text="Foundation patient result KRAS G12C",
                extraction_method="native",
                blocks=[],
            ),
            PDFPage(
                number=2,
                text="APPENDIX\nVariants of unknown significance\nA100C A101C A102C A103C",
                extraction_method="native",
                blocks=[],
            ),
        ],
    )
    barrier = threading.Barrier(2, timeout=5)
    requests = []

    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        barrier.wait()
        appendix = "[PAGE 2]" in payload["input"][1]["content"][0]["text"]
        output = (
            extraction(
                [
                    finding.model_copy(
                        update={"classification": "VUS", "report_category": "VUS"}
                    )
                ]
            )
            if appendix
            else extraction([finding])
        )
        return httpx.Response(
            200,
            json={
                "status": "incomplete"
                if appendix and appendix_failure
                else "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": output.model_dump_json()}
                        ],
                    }
                ],
            },
        )

    client = SolExtractor(
        api_key="test",
        select_patient_sections=True,
        vision_pages=0,
        http=httpx.Client(
            base_url="https://example.test", transport=httpx.MockTransport(handler)
        ),
    )
    if appendix_failure:
        with pytest.raises(ExtractionError):
            client.extract(document)
    else:
        result = client.extract(document)
        assert [f.report_category for f in result.findings] == ["detected", "VUS"]
        assert (
            client.section_selection["execution"]
            == "parallel_main_results_and_vus_appendix"
        )
    assert len(requests) == 2
    assert all(
        not (
            "[PAGE 1]" in p["input"][1]["content"][0]["text"]
            and "[PAGE 2]" in p["input"][1]["content"][0]["text"]
        )
        for p in requests
    )
