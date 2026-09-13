"""Conservative local routing of original report text, never a report rewrite.

Only positively recognized educational sections are omitted. Original documents
remain the sole source for grounding. Unknown layouts and amendments retain all
text. The decision ledger makes every omission inspectable.
"""

import re

VERSION = "patient-sections-1"


def compact(text):
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def original_block_spans(page, blocks):
    """Keep contiguous original runs quoteable; explicitly mark removed spans."""
    selected_ids = {id(block) for block in blocks}
    parts, gap = [], False
    for block in page.blocks:
        if id(block) not in selected_ids:
            gap = True
            continue
        if gap and parts:
            parts.append("[NON-RESULT BLOCKS OMITTED]")
        parts.append(block["text"].strip())
        gap = False
    return "\n".join(parts)


def select_result_sections(document):
    whole = document.text
    recognized = any(
        token in compact(whole[:12000]) for token in ("foundation", "tempus", "caris")
    )
    amended = any(
        re.search(r"amend|supersed|corrected\s+report|addendum", page.text[:600], re.I)
        for page in document.pages
    )
    foundation = "foundation" in compact(whole[:12000])
    ledger, selected = [], []
    for page in document.pages:
        text = page.text
        # Foundation's section title is in the top margin. A general keyword
        # search would mistake 'see clinical trials' on a results page for a heading.
        heading_text = (
            "\n".join(b["text"] for b in page.blocks if b["bbox"][3] < 100)
            if foundation
            else "\n".join(text.splitlines()[:12])
        )
        heading = compact(heading_text)
        all_text = compact(text)
        reason = "patient_results_or_uncertain"
        kept = text
        protected = any(
            token in all_text
            for token in (
                "variantsofunknownsignificance",
                "variantsofuncertainsignificance",
                "clonalhematopoiesis",
                "lowcoverageregions",
                "clinicalhistory",
                "notesofsignificance",
                "indeterminateresults",
                "noreportable",
            )
        )
        if not recognized or amended or page.number == 1:
            reason = (
                "full_text_fallback"
                if not recognized or amended
                else "report_identity_and_results"
            )
        elif not protected and (
            re.search(r"^References\s*$", heading_text, re.M | re.I)
            or (text.count("PMID:") >= 6 and "appendix" in heading)
            or "genesassayed" in heading
            or "genesreported" in heading
        ):
            kept, reason = "", "references_or_assay_gene_inventory"
        elif foundation and not protected and "clinicaltrials" in heading:
            kept, reason = "", "vendor_trial_listing"
        elif (
            foundation
            and not protected
            and "assayfindingsassociation" in all_text
            and "supportingdata" in all_text
        ):
            # These are drug monographs with repeated associations. Retain the
            # left association sidebar; drop the educational narrative columns.
            blocks = [
                b
                for b in page.blocks
                if b["bbox"][1] < 100 or (b["bbox"][2] < 165 and b["bbox"][3] < 700)
            ]
            if blocks:
                kept = original_block_spans(page, blocks)
                reason = "therapy_monograph_patient_association_only"
        elif (
            foundation
            and not protected
            and any(
                token in heading
                for token in (
                    "genomicfindings",
                    "biomarkerfindings",
                    "genealterations",
                    "genomicsignatures",
                )
            )
        ):
            # Recognize the Foundation three-column result + commentary layout.
            # Do not apply this to result summary tables or unfamiliar geometry.
            labels = [
                b
                for b in page.blocks
                if b["bbox"][0] < 60
                and re.match(r"^(GENE|BIOMARKER|GENOMIC SIGNA)\b", b["text"])
            ]
            narrative = any(
                "potentialtreatment" in compact(b["text"])
                or "findingsummary" in compact(b["text"])
                for b in page.blocks
            )
            three_columns = any(210 < b["bbox"][0] < 240 for b in page.blocks) and any(
                390 < b["bbox"][0] < 420 for b in page.blocks
            )
            if labels and narrative and three_columns:
                blocks = [
                    b
                    for b in page.blocks
                    if b["bbox"][3] < 100
                    or (
                        b["bbox"][0] < 60
                        and b["bbox"][2] < 215
                        and b["bbox"][3] < 700
                        and not any(
                            token in compact(b["text"][:180])
                            for token in ("potentialtrea", "findingsummar", "frequenc")
                        )
                    )
                ]
                kept = original_block_spans(page, blocks)
                reason = "patient_result_sidebar_without_biology_narrative"
        ledger.append(
            {
                "page": page.number,
                "reason": reason,
                "original_characters": len(text),
                "selected_characters": len(kept),
            }
        )
        if kept:
            # Preserve page IDs. Grounding uses the complete original PDFDocument.
            selected.append(f"[PAGE {page.number}]\n{kept}")
    payload = "\n\n".join(selected)
    return payload, {
        "version": VERSION,
        "original_characters": len(whole),
        "selected_characters": len(payload),
        "original_pages": len(document.pages),
        "selected_pages": len(selected),
        "pages": ledger,
        "amendment_full_text_fallback": amended,
    }
