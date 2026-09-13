from pathlib import Path

import pytest

from ingestion.pdf_reader import read_document
from ingestion.result_sections import select_result_sections
from schemas.extraction import PDFDocument, PDFPage


def document(*pages):
    return PDFDocument(
        sha256="original",
        pages=[
            PDFPage(number=i + 1, text=text, extraction_method="native", blocks=[])
            for i, text in enumerate(pages)
        ],
    )


def test_unknown_layout_and_amended_report_keep_all_text():
    for report in (
        document("Unknown vendor results", "References\nEGFR L858R"),
        document("Tempus AMENDED REPORT", "References\nSuperseded findings"),
    ):
        text, audit = select_result_sections(report)
        assert text == report.text
        assert audit["selected_pages"] == 2


def test_mixed_reference_and_result_page_is_not_discarded():
    report = document(
        "Caris Results", "References\nVARIANTS OF UNKNOWN SIGNIFICANCE\nEGFR L858R"
    )
    text, _ = select_result_sections(report)
    assert text == report.text


def test_reference_page_is_removed_without_changing_source_or_page_ids():
    report = document(
        "Caris Results",
        "References\nA publication",
        "Clonal Hematopoiesis\nDNMT3A R882H",
    )
    before = report.model_dump()
    text, audit = select_result_sections(report)
    assert "[PAGE 3]" in text and "DNMT3A R882H" in text
    assert "A publication" not in text
    assert report.model_dump() == before
    assert audit["pages"][1]["selected_characters"] == 0


def test_corpus_result_pages_and_appendices_are_preserved():
    corpus = Path(__file__).resolve().parents[1] / "evaluation/corpus"
    files = list(corpus.glob("*.pdf"))
    if len(files) != 12:
        pytest.skip("Public sample PDFs are local only")
    # Includes VUS appendices, amended+original reports, CH, negative findings,
    # specimen pages, indeterminate findings and late IHC / sequencing results.
    patient_pages = {
        "01_": [1, 2, 3, 10],
        "02_": [1, 2],
        "03_": [1, 2, 3, 4, 7],
        "04_": [1, 2, 3, 4],
        "05_": [1, 2, 3, 4, 28],
        "06_": [1, 2, 3, 4, 23],
        "07_": [1, 2, 11],
        "10_": list(range(1, 12)),
        "11_": list(range(1, 6)),
        "12_": [1, 2],
        "13_": [1, 2, 3, 5, 6, 7],
        "14_": [1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
    }
    for path in files:
        report = read_document(path)
        text, audit = select_result_sections(report)
        for page in patient_pages[path.name[:3]]:
            assert report.pages[page - 1].text in text, (path.name, page)
        if path.name.startswith("05_"):
            assert audit["selected_characters"] < audit["original_characters"] * 0.35
            for token in ("L858R", "E453K", "Q944", "E176K", "24 Muts/Mb", "MS-Stable"):
                assert token in text
