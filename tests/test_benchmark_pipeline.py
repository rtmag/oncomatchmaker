from pathlib import Path

from evaluation.benchmark_full_pipeline import _native_stage


def test_native_stage_reads_a_pdf(tmp_path):
    import pymupdf

    path = tmp_path / "sample.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text(
            (40, 40), "Synthetic benchmark page with enough molecular report text."
        )
        document.save(path)
    pages, characters = _native_stage(Path(path))
    assert pages == 1
    assert characters > 20
