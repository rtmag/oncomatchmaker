# Ingestion validation — 2026-09-13

## Selective reader update

`selective-native-1.2` uses native blocks initially and enriches pages cited by
invalid findings with pdfplumber before the existing model repair call. The CLI
offers `--full-layout` to enrich all native pages before initial extraction.
No extracted-text cache or new persistent report storage was added.

A single sequential local benchmark of the same 12 PDFs took 1.176 seconds
total (0.017–0.260 seconds per file), versus 63.6 seconds with the previous
all-page dual reader. This measures local reading only, not model latency.
Tests verify selected-page glyph deduplication, the real RAD51C row on page 7
of the stomach report, and enrichment before model repair. A fresh live model
evaluation remains outstanding; omitted findings cannot themselves trigger
the validation-based fallback.

## Prior live baseline

The live baseline completed extraction and review for all 12 locally available
sample reports using `gpt-5.6-sol` and prompt version `ingestion-0.2.1`.
These reports include both tissue and liquid assays.

The saved audits, evaluated with `evaluation.evaluate_ingestion`, recovered 21 of
23 developer-annotated landmarks. No accepted findings had an invalid HGNC ID,
and no explicitly prohibited molecular targets were produced. These annotations
are non-exhaustive; the numbers do not measure whole-report precision, recall,
clinical accuracy, or biological suitability for a trial.

Two missed landmarks motivated subsequent changes: uncertain VAF information
caused otherwise supported TP53 and DNMT3A findings to be held for review.
Overlapping PDF glyphs also corrupted gene text in proposed extractions; registry
validation rejected the invalid name.

The current revision uses prompt `ingestion-0.2.2`, a dual native-text reader
(`dual-native-1.1`), and separates optional metadata review from core finding
review. Batch extraction now uses separate worker processes. These latest changes
have not yet completed a fresh live corpus run. The baseline metrics above must
not be attributed to the current revision.

Current local verification: 44 automated tests passed, 4 opt-in live tests skipped;
Ruff lint and formatting checks passed. PDF-reader coverage includes all 12 local
reports. Model calls in the automated suite are mocked.

PDFs, extraction audits, and credentials are ignored by Git and are not included
in this PR. To reproduce with the local corpus and a configured `OPENAI_API_KEY`:

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
# Paid model calls; use a new output directory to preserve baseline audits.
.venv/bin/python -m app.ingest evaluation/corpus --batch --output evaluation/runs/sol-corpus-v2
.venv/bin/python -m evaluation.evaluate_ingestion evaluation/runs/sol-corpus-v2
```

HGNC validates gene nomenclature, not variant existence, pathogenicity, or trial
eligibility. Clinician-reviewed ground truth and biological matching remain open
work.
