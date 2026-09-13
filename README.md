# OncoMatchmaker

**From molecular report to matched therapies and clinical trials.**

OncoMatchmaker is a clinical decision-support project that helps users move from a molecular oncology report to relevant treatment evidence and clinical-trial opportunities.

Users upload a molecular oncology report, and GPT-5.6 Sol extracts and reviews the molecular profile. Local HGNC and NCIt checks validate gene nomenclature and supported cancer names. The downstream trial-discovery prototype remains rule based; biological interpretation of trial eligibility is a separate, deferred task.

Approved therapies and experimental clinical trials are intentionally presented separately. OncoMatchmaker supports informed discussion with qualified clinicians and trial teams; it does not provide medical advice or determine treatment or trial eligibility.

See [PROJECT.md](PROJECT.md) for the full project specification and [TASKS_ROBERTO_ABHISHEK.md](TASKS_ROBERTO_ABHISHEK.md) for the development work split.

## Run the app

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/streamlit run app/main.py
```

Choose a PDF report, a synthetic demo, or canonical JSON, review the profile, then search.
Patient location coordinates are optional; city/country alone does not produce a
distance. The app queries live ClinicalTrials.gov v2 records, which needs no credentials.
PDF extraction uses the OpenAI API key described below. Reports and patient profiles
are not written to a persistent cache by the UI.
Queries send disease and molecular search terms to ClinicalTrials.gov; age,
coordinates, and other context stay in the local matching process.

For machine-readable output:

```sh
.venv/bin/python -m app.match tests/fixtures/kras_nsclc.json
```

## Integration contract

`schemas.molecular_profile.MolecularProfile` accepts versions `0.1` and `0.2`.
`ingestion.pipeline.parse_report(pdf_path) -> MolecularProfile` now performs real
Sol extraction, an optional single repair pass, independent review and deterministic
source/registry checks. New profiles use `0.2`, with HGNC IDs, finding origin,
source pages, raw alterations, NCIt mappings and ingestion audit metadata. Existing
`0.1` fixtures remain readable. The matching interface is:

```python
from trials.pipeline import match_patient

results = match_patient(profile)
```

Schemas reject unrecognized fields rather than silently dropping clinical data.
The new optional `prior_therapies_known` field distinguishes a known empty history
from the original schema's empty/unrecorded list. Fusion entries use `gene` and
optional `partner`; copy-number entries use `gene` and `alteration`. Both retain
classification, source text, and a possible-CH flag. Coordinate pairs and numeric
ranges are validated. Review these contracts with Roberto before merging.

## Matching behavior and limits

- Search uses disease/variant, disease/gene, and solid-tumor queries, deduplicated
  by NCT ID. Negative reports use disease-only search. Unknown classification,
  VUS, and possible CH do not create molecular targets. HGVS long protein names,
  disease ontology mapping, and complex biomarkers require upstream normalization.
- The direct API adapter supports pagination (three pages of 100 per query),
  20-second request timeouts, three attempts for transient failures, and a
  15-minute in-memory public-response cache per client. Truncation or failed
  pages are reported as partial results. No stale-cache fallback is automatic.
- Molecular scoring measures **title relevance**, not satisfaction of molecular
  inclusion criteria. It awards 30 for gene and exact alteration mentions and 20
  for a gene mention. Trial-title negation/cohort interpretation is not automated.
- Disease scoring awards 15 for canonical disease equality and 8 for explicitly
  broad solid-tumor conditions. Unconfirmed disease compatibility goes into the
  review group, outside primary recruiting candidates.
- Eligibility resolves structured age (years) and sex criteria only. Free-text
  ECOG, therapy, CNS, organ-function, molecular and cohort rules remain UNKNOWN
  for trial-team review, even when some patient context is available. A known
  mismatch excludes the candidate from the primary list.
- Eligibility contributes up to 20 based on matched/all recorded criteria;
  unresolved criteria cannot earn points. Development contributes up to 10 using
  phase only (I: 2.5, II: 5, III: 7.5, IV: 10; early I: 1).
- Recruitment contributes 10 for a recruiting study with an explicitly recruiting
  site, 5 if site status is uncertain, 2 for not-yet-recruiting, otherwise 0.
  Geography contributes `15 * exp(-distance_km / 250)` using the nearest explicitly
  recruiting site. Unknown distance or other unknown components earn no points
  and reduce displayed component coverage. Totals are not rescaled.
- Recruiting, not-yet-recruiting, review, and known-mismatch groups stay separate.
  Phase and total scores do not estimate benefit or eligibility probability.
- The curated evidence dataset covers two demo associations (KRAS G12C and EGFR
  L858R in NSCLC). FDA source links, restrictions, jurisdiction and verification
  dates are included. It is not a comprehensive or automatically refreshed
  knowledgebase. Other-disease evidence is labeled separately; local approval
  and full patient applicability are not inferred.

## Tests and demo

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
ONCOMATCH_LIVE=1 .venv/bin/python -m pytest -q -m live
```

Offline tests use synthetic boundary cases and a recorded public API response.
The opt-in live test checks actual connectivity and response structure.
Demo sequence: KRAS profile → evidence and trial cards; EGFR profile → different
biomarker evidence; negative profile → disease-only trials without invented
targets. These are synthetic demos, not vendor extraction evaluations.

The local corpus contains 12 public sample PDFs from Foundation Medicine, Tempus
and Caris. It includes tissue as well as liquid-biopsy reports. PDFs are ignored by
Git; the checked-in CSV identifies the authorized local files.

## Intelligent PDF ingestion

Configure the ignored `.env` file (or environment):

```dotenv
OPENAI_API_KEY=your-key-here
ONCOMATCH_EXTRACTION_MODEL=gpt-5.6-sol
```

Select **PDF report** in the UI, upload a sample, and click **Extract profile**.
The document's text and images of its first three pages are sent to OpenAI for
extraction. The review pass reads the full extracted text. Requests set `store=false`;
this setting is not a claim of zero provider retention. No credentials or report
payloads are included in application error messages.

```sh
# Profile JSON to stdout, suitable for the downstream matcher
.venv/bin/python -m app.ingest evaluation/corpus/12_Tempus_xF_negative.pdf

# Full audit, including rejected findings and their reasons
.venv/bin/python -m app.ingest evaluation/corpus/13_Caris_Assure_metastatic_lung.pdf --output evaluation/runs/caris.json

# Live evaluation of all local PDFs; makes paid API calls, two reports at a time
.venv/bin/python -m app.ingest evaluation/corpus --batch --output evaluation/runs/sol-corpus-v1

# Local-only evaluation of the saved results; no API calls
.venv/bin/python -m evaluation.evaluate_ingestion evaluation/runs/sol-corpus-v1
```

The extraction pipeline:

1. Reads every PDF page with PyMuPDF and retains text blocks, coordinates and a
   document hash. A second pdfplumber view deduplicates overlapping glyphs and
   preserves row order. Scanned/unreadable pages fail closed unless local OCR is enabled
   with `--ocr` (requires Tesseract English language data). Limits: 40 MB, 100 pages,
   600,000 extracted characters. It never silently truncates the report.
2. Sol returns structured findings and scalar fields with page/quote evidence,
   preserving negative results, VUS, germline, CH and amended-report context.
3. HGNC checks symbols against the full bundled approved-gene snapshot. Unique
   previous symbols and aliases resolve to an approved symbol and HGNC ID;
   ambiguous/unknown names are held out. There is no fuzzy gene correction.
4. Finding quotes must occur on the stated page and contain the reported gene and
   alteration. Classification and numeric evidence are checked separately. Invalid
   findings receive at most one model repair pass, then are validated again.
   Scalar quotes may be narrowed to an exact value already present on the same page;
   this is recorded in the audit. Finding quotes are not heuristically reconstructed.
5. A separate Sol call audits the proposal against the source, including amended
   findings, assay gene lists and the distinction between tumor, germline and CH.
   Unsupported/uncertain core findings are excluded from the profile and shown for
   review. Optional values such as uncertain VAF can be withheld while retaining
   supported core findings; origin/classification review flags prevent targeting.
6. Normalization uses a bounded NCIt preferred-name/synonym snapshot for diseases.
   Unknown or ambiguous cancers keep their raw text and an explicit review warning.
   It does not infer NSCLC from a lung specimen or use HGNC for cancer names.

HGNC verifies **gene identity**, not variant existence, pathogenicity, somatic
origin or treatment relevance. Source checks and a second model pass reduce errors
but do not establish clinical validity; the reviewer is the same model in a separate
request, not an independent clinical expert. Unknown pathology classifications
remain unknown. Missing/held findings must not be interpreted as a negative report.
The initial extractor supports genomic variants, copy number, fusions/splice,
MSI, TMB, ctDNA fraction and technical notes; it is not a comprehensive IHC/MMR/HRD
interpretation system. Protein-name conversion is notation normalization, not
reference-genome or transcript validation.

`evaluation/ingestion_landmarks.json` contains non-exhaustive developer annotations.
The evaluator reports recovery of those specific landmarks and targeted error
checks, not whole-report precision/recall or clinical accuracy. Full clinician-reviewed
ground truth is still needed before clinical use.

See [the validation record](evaluation/INGESTION_VALIDATION.md) for measured results
and the distinction between the live baseline and the current revision.

## Reference snapshots

The compressed HGNC snapshot contains 45,054 approved genes and records its upstream
SHA-256 and retrieval time. Refresh explicitly (changes the bundled snapshot):

```sh
.venv/bin/python -m normalization.update_hgnc
```

Sources: [HGNC official downloads](https://www.genenames.org/download/),
[NCIt through EBI OLS](https://www.ebi.ac.uk/ols4/ontologies/ncit),
[Sol model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-sol),
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
