"""Page-preserving native text extraction with optional local Tesseract OCR."""

import hashlib
import io
import re
from pathlib import Path

import pdfplumber
import pymupdf

from schemas.extraction import PDFDocument, PDFPage


class PDFReadError(ValueError):
    pass


def read_document(
    path,
    *,
    ocr=False,
    max_pages=100,
    max_bytes=40 * 1024 * 1024,
    row_order_pages=(),
):
    """Read native blocks; optionally enrich selected 1-based pages (None = all)."""
    path = Path(path)
    if path.stat().st_size > max_bytes:
        raise PDFReadError("PDF exceeds the 40 MB ingestion limit")
    raw = path.read_bytes()
    if not raw.startswith(b"%PDF-"):
        raise PDFReadError("File is not a PDF")
    try:
        doc = pymupdf.open(stream=raw, filetype="pdf")
    except (RuntimeError, ValueError) as exc:
        raise PDFReadError("Cannot open damaged PDF") from exc
    pages = []
    with doc:
        if doc.needs_pass:
            raise PDFReadError("Encrypted PDF requires an unlocked copy")
        if not 0 < len(doc) <= max_pages:
            raise PDFReadError(f"PDF must contain 1–{max_pages} pages")
        for index, page in enumerate(doc):
            textpage = page.get_textpage()
            method, warnings = "native", []
            if len(textpage.extractText().strip()) < 40:
                if ocr:
                    try:
                        textpage = page.get_textpage_ocr(
                            language="eng", dpi=200, full=True
                        )
                        method = "ocr"
                        warnings.append(
                            "OCR text requires visual review for gene/variant transcription errors."
                        )
                    except (RuntimeError, ValueError) as exc:
                        raise PDFReadError(
                            "OCR unavailable; install Tesseract English data or supply a searchable PDF"
                        ) from exc
                else:
                    method = "unreadable"
                    warnings.append(
                        "Little extractable text; enable OCR or supply a searchable PDF."
                    )
            # Block order preserves table fragments without the huge whitespace of layout text.
            raw_blocks = page.get_text("blocks", textpage=textpage, sort=True)
            blocks = [
                {"bbox": list(b[:4]), "text": b[4]} for b in raw_blocks if b[6] == 0
            ]
            text = "\n".join(b["text"].strip() for b in blocks)
            pages.append(
                PDFPage(
                    number=index + 1,
                    text=text,
                    extraction_method=method,
                    blocks=blocks,
                    warnings=warnings,
                )
            )
    warnings = [f"Page {p.number}: {w}" for p in pages for w in p.warnings]
    # A second, geometric view removes duplicated print glyphs and preserves rows.
    # Keep the original block view too: neither linearization is perfect for every table.
    selected = [
        p.number
        for p in pages
        if p.extraction_method == "native"
        and (row_order_pages is None or p.number in row_order_pages)
    ]
    try:
        if selected:
            with pdfplumber.open(io.BytesIO(raw), pages=selected) as layout_pdf:
                for layout_page in layout_pdf.pages:
                    p = pages[layout_page.page_number - 1]
                    _add_row_text(p, layout_page)
    except (ValueError, RuntimeError, OSError):
        warnings.append(
            "Secondary row-order extraction failed; original page text retained."
        )
    printed_totals = [
        int(total)
        for p in pages
        for total in re.findall(r"\bPAGE\s+\d+\s+of\s+(\d+)", p.text, re.I)
    ]
    if printed_totals and max(printed_totals) > len(pages):
        warnings.append(
            f"Possible report excerpt: {len(pages)} PDF pages, but printed pagination refers to {max(printed_totals)} pages. Findings on missing pages cannot be evaluated."
        )
    return PDFDocument(
        sha256=hashlib.sha256(raw).hexdigest(),
        reader_version="selective-native-1.2:rows=" + ",".join(map(str, selected)),
        pages=pages,
        warnings=warnings,
    )


def _add_row_text(p, layout_page):
    if p.extraction_method == "native":
        cleaned = (
            layout_page.dedupe_chars(tolerance=1, extra_attrs=()).extract_text(
                x_tolerance=2, y_tolerance=3
            )
            or ""
        )
        if cleaned.strip():
            p.text = (
                "[ROW-ORDER TEXT]\n"
                + cleaned
                + "\n[ORIGINAL BLOCK-ORDER TEXT]\n"
                + p.text
            )
    layout_page.close()


def read_pdf(path: str) -> str:
    return read_document(path).text
