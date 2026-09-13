# ASTRA Hackathon Execution Plan — Roberto & Abhishek

## 1. Objective

Build the ASTRA Precision Oncology Trial Matchmaker POC in parallel, minimizing blocking dependencies.

The system has two major halves:

```text
PDF report
   ↓
[TRACK A]
Report understanding + normalization
   ↓
Canonical Molecular Profile JSON
   ↓
[TRACK B]
Therapy/trial search + ranking + presentation
   ↓
Ranked evidence-backed results
```

The shared contract is the **Canonical Molecular Profile JSON**.

As long as both tracks obey that contract, each person can build and test independently.

---

# 2. Recommended Ownership Split

## Roberto — Track A: Report Intelligence + Molecular Normalization + Evaluation Corpus

Primary responsibility:

> Convert heterogeneous vendor PDFs into reliable, validated canonical molecular profiles.

Roberto owns everything from uploaded report to normalized JSON.

### Core responsibilities

- organize the PDF corpus,
- create corpus manifest,
- define canonical molecular-profile schema jointly,
- implement PDF ingestion,
- identify vendor/assay,
- extract tumor diagnosis,
- extract biomarkers,
- normalize findings,
- distinguish tumor findings from VUS/CH where reported,
- create ground-truth annotations,
- test extraction accuracy,
- expose a clean function/API to Track B.

---

## Abhishek — Track B: Actionability + Trial Retrieval + Ranking + Geography + UI

Primary responsibility:

> Convert the canonical molecular profile into approved-treatment evidence and ranked recruiting clinical trials.

Abhishek owns everything after normalized JSON is produced.

### Core responsibilities

- build BioMCP/ClinicalTrials.gov integration,
- build therapy-evidence retrieval,
- generate trial queries,
- retrieve candidate trials,
- parse trial metadata,
- parse trial locations,
- calculate distance,
- implement eligibility prescreening,
- implement trial scoring/ranking,
- create result data structures,
- build main POC UI,
- connect Track A output during integration.

---

# 3. Shared Interface Contract

This must be agreed first.

Neither track should depend on the other's internal implementation.

The only required interface is:

```python
profile = parse_report(pdf_path)
results = match_patient(profile)
```

Where:

```python
parse_report(pdf_path) -> MolecularProfile
```

belongs to Track A.

And:

```python
match_patient(profile) -> MatchResults
```

belongs to Track B.

---

# 4. Canonical Molecular Profile

Recommended initial schema:

```json
{
  "schema_version": "0.1",

  "report": {
    "vendor": "Caris",
    "assay": "Caris Assure",
    "sample_type": "plasma",
    "report_date": null
  },

  "disease": {
    "raw_text": "Metastatic lung carcinoma",
    "normalized": "non-small cell lung cancer",
    "histology": null,
    "stage": "metastatic"
  },

  "patient_context": {
    "age": null,
    "sex": null,
    "prior_therapies": [],
    "ecog": null,

    "location": {
      "city": "Singapore",
      "country": "Singapore",
      "latitude": null,
      "longitude": null
    }
  },

  "biomarkers": {
    "snv_indel": [
      {
        "gene": "KRAS",
        "protein_change": "G12C",
        "hgvs_c": null,
        "hgvs_p": null,
        "vaf": null,
        "classification": "pathogenic",
        "source_text": "KRAS G12C",
        "potential_ch": false
      }
    ],

    "copy_number": [],

    "fusions": [],

    "msi": {
      "status": "stable"
    },

    "tmb": {
      "value": 8.0,
      "unit": "mut/Mb",
      "classification": null
    },

    "tumor_fraction": null
  },

  "technical_notes": [],

  "extraction_confidence": {
    "overall": 0.95
  }
}
```

---

# 5. Shared Python Models

Create these first.

Suggested:

```text
schemas/
  molecular_profile.py
  match_results.py
```

Possible Pydantic models:

```python
class Variant(BaseModel):
    gene: str
    protein_change: str | None
    hgvs_c: str | None
    hgvs_p: str | None
    vaf: float | None
    classification: str | None
    source_text: str
    potential_ch: bool = False


class Disease(BaseModel):
    raw_text: str
    normalized: str | None
    histology: str | None
    stage: str | None


class MolecularProfile(BaseModel):
    schema_version: str
    report: ReportMetadata
    disease: Disease
    patient_context: PatientContext
    biomarkers: Biomarkers
    technical_notes: list[str]
    extraction_confidence: ExtractionConfidence
```

Both people should import the same model.

---

# 6. Repository Structure

Recommended repository:

```text
astra-trial-matchmaker/

  README.md
  PROJECT.md

  app/
    main.py

  schemas/
    __init__.py
    molecular_profile.py
    match_results.py

  ingestion/
    __init__.py
    pdf_reader.py
    classify_report.py
    extract_report.py
    normalize_report.py

  trials/
    __init__.py
    biomcp_client.py
    search.py
    trial_parser.py
    eligibility.py
    geography.py
    ranking.py

  evidence/
    __init__.py
    actionability.py

  ui/
    upload.py
    profile.py
    therapies.py
    trials.py

  evaluation/
    corpus/
    corpus_manifest.json
    ground_truth.json
    evaluate_extraction.py
    evaluate_trials.py

  tests/
    test_schema.py
    test_ingestion.py
    test_trial_search.py
    test_ranking.py
```

---

# 7. Day 1 Morning — Shared Setup

Do this together before splitting.

Maximum target: 30–60 minutes.

## Task 1 — initialize repository

Create:

```text
astra-trial-matchmaker
```

Add:

```text
PROJECT.md
requirements.txt / pyproject.toml
.gitignore
```

---

## Task 2 — agree canonical JSON

Both people must agree on:

- disease fields,
- variant fields,
- fusion representation,
- copy-number representation,
- MSI,
- TMB,
- patient location,
- prior therapy representation.

Do not change the schema casually after splitting.

If changes are needed:

```text
schema_version 0.1 → 0.2
```

---

## Task 3 — build one hard-coded fixture

Create:

```text
tests/fixtures/kras_nsclc.json
```

Example:

```json
{
  "schema_version": "0.1",
  "report": {
    "vendor": "TEST",
    "assay": "TEST",
    "sample_type": "plasma",
    "report_date": null
  },
  "disease": {
    "raw_text": "Metastatic NSCLC",
    "normalized": "non-small cell lung cancer",
    "histology": "adenocarcinoma",
    "stage": "IV"
  },
  "patient_context": {
    "age": 61,
    "sex": null,
    "prior_therapies": [],
    "ecog": 1,
    "location": {
      "city": "Singapore",
      "country": "Singapore",
      "latitude": 1.3521,
      "longitude": 103.8198
    }
  },
  "biomarkers": {
    "snv_indel": [
      {
        "gene": "KRAS",
        "protein_change": "G12C",
        "hgvs_c": null,
        "hgvs_p": null,
        "vaf": 0.12,
        "classification": "pathogenic",
        "source_text": "KRAS G12C",
        "potential_ch": false
      }
    ],
    "copy_number": [],
    "fusions": [],
    "msi": {
      "status": "stable"
    },
    "tmb": {
      "value": 7.0,
      "unit": "mut/Mb",
      "classification": null
    },
    "tumor_fraction": null
  },
  "technical_notes": [],
  "extraction_confidence": {
    "overall": 1.0
  }
}
```

Abhishek can develop the entire downstream pipeline using this fixture while Roberto works on real PDF parsing.

That removes the main dependency.

---

# 8. Roberto — Detailed Track A Tasks

## A1. Create corpus manifest

Input:

```text
14 vendor PDFs
```

Create:

```text
evaluation/corpus_manifest.json
```

For each case record:

```json
{
  "case_id": "CASE_001",
  "filename": "...pdf",
  "vendor": "Foundation Medicine",
  "assay": "FoundationOne Liquid CDx",
  "tumor_type": "NSCLC",
  "sample_type": "plasma"
}
```

Do not modify the PDFs.

---

## A2. Ground-truth annotations

Create:

```text
evaluation/ground_truth.json
```

Manually record the important findings for each PDF.

Example:

```json
{
  "CASE_001": {
    "disease": "non-small cell lung cancer",
    "key_findings": [
      {
        "gene": "EGFR",
        "protein_change": "L858R",
        "type": "SNV"
      }
    ],
    "msi": "stable",
    "tmb": null
  }
}
```

Ground truth does not need every footnote in the report.

Focus on clinically relevant fields.

---

## A3. Implement PDF text extraction

Create:

```text
ingestion/pdf_reader.py
```

Interface:

```python
def read_pdf(path: str) -> str:
    ...
```

Prefer native PDF text.

Fallback to vision/OCR only if required.

Return:

```text
full textual representation
```

---

## A4. Implement vendor classifier

Create:

```text
ingestion/classify_report.py
```

Interface:

```python
def classify_report(text: str) -> dict:
    ...
```

Example output:

```json
{
  "vendor": "Foundation Medicine",
  "assay": "FoundationOne Liquid CDx",
  "confidence": 0.99
}
```

Recognize at least:

```text
Foundation Medicine
Tempus
Caris
TSO500/PierianDx
UNKNOWN
```

---

## A5. ASTRA extraction prompt/workflow

Create:

```text
ingestion/extract_report.py
```

Interface:

```python
def extract_report(text: str) -> dict:
    ...
```

ASTRA should return structured JSON.

Explicit prompt requirements:

```text
Extract only information explicitly present in the report.

Do not infer a mutation that is not written.

Do not convert a VUS into pathogenic.

Do not classify CH as a tumor alteration if the report labels it clonal hematopoiesis.

Return null when information is absent.
```

---

## A6. Normalize report

Create:

```text
ingestion/normalize_report.py
```

Interface:

```python
def normalize_report(extracted: dict) -> MolecularProfile:
    ...
```

Responsibilities:

- uppercase gene symbols,
- standardize mutation notation,
- standardize MSI values,
- convert percentages,
- normalize cancer terms.

---

## A7. Main Track A API

Create:

```text
ingestion/pipeline.py
```

Public function:

```python
def parse_report(pdf_path: str) -> MolecularProfile:
    text = read_pdf(pdf_path)
    metadata = classify_report(text)
    extracted = extract_report(text)
    profile = normalize_report(extracted)
    return profile
```

Abhishek should not need to know anything about the internals.

---

## A8. Extraction evaluation

Create:

```text
evaluation/evaluate_extraction.py
```

Metrics:

```text
Vendor accuracy
Disease accuracy
Variant precision
Variant recall
Variant F1
MSI accuracy
TMB accuracy
```

Important safety metrics:

```text
CH false positive count
VUS actionable false positive count
```

---

## A9. Test at least five representative reports

Recommended:

```text
FMI liquid
Tempus
Caris
TSO500/PierianDx
negative report
```

Then test all 14 if time permits.

---

# 9. Abhishek — Detailed Track B Tasks

Abhishek should begin entirely from:

```text
tests/fixtures/kras_nsclc.json
```

No need to wait for PDF parsing.

---

## B1. BioMCP / ClinicalTrials.gov client

Create:

```text
trials/biomcp_client.py
```

Functions should be narrowly scoped.

Example:

```python
def search_trials(
    disease: str,
    gene: str | None = None,
    variant: str | None = None
) -> list[dict]:
    ...
```

And:

```python
def get_trial(nct_id: str) -> dict:
    ...
```

---

## B2. Trial query generator

Create:

```text
trials/search.py
```

Given:

```text
NSCLC
KRAS G12C
```

generate multiple searches:

```text
NSCLC KRAS G12C
NSCLC KRAS
KRAS G12C solid tumor
```

For a fusion:

```text
NSCLC RET fusion
RET fusion solid tumor
```

Merge results.

Deduplicate by:

```text
NCT ID
```

---

## B3. Recruitment filtering

Prioritize:

```text
RECRUITING
NOT_YET_RECRUITING
```

Potentially retain:

```text
ACTIVE_NOT_RECRUITING
```

but don't rank these above recruiting trials.

---

## B4. Trial parser

Create:

```text
trials/trial_parser.py
```

Convert ClinicalTrials.gov/BioMCP output to shared TrialCandidate schema.

Recommended:

```json
{
  "nct_id": "NCT01234567",
  "title": "...",
  "phase": "PHASE2",
  "status": "RECRUITING",
  "conditions": [],
  "interventions": [],
  "eligibility_text": "...",
  "sites": []
}
```

---

## B5. Actionability layer

Create:

```text
evidence/actionability.py
```

Input:

```python
MolecularProfile
```

Output:

```text
ApprovedOption[]
```

Each option:

```json
{
  "biomarker": "KRAS G12C",
  "therapy": "example",
  "context": "same_disease",
  "evidence_level": "approved",
  "sources": []
}
```

Important:

```text
Approved therapies must remain separate from trial rankings.
```

---

## B6. Eligibility parser

Create:

```text
trials/eligibility.py
```

Input:

```python
profile
trial
```

Output:

```json
{
  "status": "POSSIBLE_MATCH",
  "criteria": [
    {
      "criterion": "Age >= 18",
      "status": "MATCH"
    },
    {
      "criterion": "ECOG 0-1",
      "status": "UNKNOWN"
    }
  ],
  "missing_information": [
    "ECOG status",
    "prior targeted therapy"
  ]
}
```

ASTRA is useful here.

Prompt principle:

```text
Never infer unknown patient information.
```

---

## B7. Geographic module

Create:

```text
trials/geography.py
```

Functions:

```python
def haversine_distance(
    lat1,
    lon1,
    lat2,
    lon2
) -> float:
    ...
```

Then:

```python
def find_nearest_site(
    patient_location,
    sites
):
    ...
```

Output:

```json
{
  "site": "...",
  "city": "...",
  "country": "...",
  "distance_km": 8.2
}
```

---

## B8. Trial scoring

Create:

```text
trials/ranking.py
```

Suggested weights:

```text
Molecular match       30
Disease match         15
Eligibility           20
Trial evidence        10
Recruitment           10
Geography             15
```

Public API:

```python
def score_trial(
    profile: MolecularProfile,
    trial: TrialCandidate
) -> TrialScore:
    ...
```

Avoid asking the LLM for one opaque score.

Calculate component scores separately.

---

## B9. Main matching API

Create:

```text
trials/pipeline.py
```

Public function:

```python
def match_patient(
    profile: MolecularProfile
) -> MatchResults:
    ...
```

Pseudo-flow:

```python
approved = find_approved_options(profile)

queries = generate_queries(profile)

trials = retrieve_trials(queries)

trials = deduplicate(trials)

for trial in trials:
    eligibility = evaluate_eligibility(profile, trial)
    geography = evaluate_geography(profile, trial)
    score = score_trial(profile, trial)

ranked = sort_trials(trials)

return MatchResults(
    approved_options=approved,
    trials=ranked
)
```

---

# 10. Abhishek — UI Tasks

If using Streamlit, Gradio, or similar:

Create:

```text
app/main.py
```

Minimum interface:

```text
[Upload report]

[Patient location]

[Analyze]
```

Results:

```text
Extracted Molecular Profile

Approved / Established Options

Clinical Trial Matches
```

Trial cards should show:

```text
NCT ID
Title
Phase
Recruitment
Match score
Molecular score
Eligibility score
Distance
Nearest site
Why matched
Missing eligibility data
```

---

# 11. Shared Match Results Schema

Suggested:

```json
{
  "profile": {},
  "approved_options": [],
  "trials": [
    {
      "nct_id": "NCT...",
      "title": "...",
      "status": "RECRUITING",
      "phase": "PHASE2",

      "match": {
        "overall_score": 91,
        "molecular_score": 30,
        "disease_score": 15,
        "eligibility_score": 15,
        "evidence_score": 8,
        "recruitment_score": 10,
        "geography_score": 13
      },

      "nearest_site": {
        "name": "...",
        "distance_km": 18.4
      },

      "eligibility": {
        "status": "POSSIBLE_MATCH",
        "missing_information": []
      },

      "rationale": "...",

      "sources": []
    }
  ]
}
```

---

# 12. Day 1 Afternoon — Parallel Development

## Roberto

Goal by end of Day 1:

```text
PDF → valid canonical JSON
```

Minimum:

- 3 vendors working,
- 5 reports tested.

Stretch:

- all vendors,
- all 14 reports.

---

## Abhishek

Goal by end of Day 1:

```text
fixture JSON → real trial search → ranked results
```

Minimum:

- BioMCP/ClinicalTrials.gov search working,
- trial parsing,
- basic ranking.

Stretch:

- geography,
- eligibility reasoning,
- UI.

---

# 13. First Integration Checkpoint

Integration should happen as soon as:

```python
parse_report("report.pdf")
```

returns the agreed schema.

Test:

```python
profile = parse_report("case.pdf")
results = match_patient(profile)
```

Do not wait until everything is polished.

Use one simple report first.

Recommended:

```text
KRAS G12C NSCLC
```

Expected behavior:

```text
PDF
↓
KRAS G12C extracted
↓
NSCLC extracted
↓
relevant approved evidence
↓
KRAS G12C trials
↓
ranked recruiting trials
```

---

# 14. Day 2 Morning — Integration

## Task 1

Wire:

```text
UI → parse_report()
```

## Task 2

Show extracted profile before trial search.

This is important because users need to verify extraction.

## Task 3

Wire:

```text
parse_report()
→ match_patient()
```

## Task 4

Add location.

Minimum:

```text
city + country
```

Better:

```text
latitude + longitude
```

## Task 5

Render trial cards.

---

# 15. Day 2 Midday — Evaluation

Run the PDF corpus.

Track:

```text
Case
Vendor
Disease correct?
Key mutations correct?
Critical error?
Trial retrieval successful?
```

Create a small summary such as:

```text
14 reports tested

Vendor identification:
14/14

Key molecular findings:
XX/YY recovered

Critical CH mistakes:
0

Trial search:
XX/14 produced relevant recruiting trials
```

Never invent metrics.

Only show actual measured performance.

---

# 16. Day 2 Afternoon — Demo Preparation

Choose 3–4 demo cases.

Recommended sequence:

## Demo 1

Simple driver.

Shows the system works.

## Demo 2

Different vendor.

Shows vendor independence.

## Demo 3

Complex liquid report.

Shows sophisticated extraction.

## Demo 4

Negative or low-information case.

Shows safety.

---

# 17. Final Integration Checklist

Before demo:

### Report ingestion

- [ ] PDF upload works
- [ ] vendor displayed
- [ ] assay displayed
- [ ] disease displayed
- [ ] variants displayed
- [ ] MSI displayed when present
- [ ] TMB displayed when present
- [ ] CH findings are not treated as tumor targets
- [ ] VUS not falsely treated as established actionable findings

### Trial search

- [ ] at least one real ClinicalTrials.gov query works
- [ ] results deduplicated
- [ ] recruitment status shown
- [ ] NCT ID shown
- [ ] phase shown
- [ ] molecular match explained

### Geography

- [ ] patient location captured
- [ ] nearest site displayed
- [ ] distance displayed
- [ ] missing location handled gracefully

### Eligibility

- [ ] known criteria compared
- [ ] unknown information remains UNKNOWN
- [ ] no definitive eligibility claim

### Safety

- [ ] approved therapies separate from trials
- [ ] trials labeled experimental
- [ ] medical decision disclaimer present
- [ ] citations/source links shown

### UI

- [ ] loading states
- [ ] failure states
- [ ] readable cards
- [ ] report extraction visible before results
- [ ] demo cases pre-tested

---

# 18. Demo Rehearsal Script

## Step 1

Open platform.

Say:

> Molecular oncology reports contain powerful information, but converting that information into a current clinical-trial opportunity is still fragmented and manual.

## Step 2

Upload report.

Say:

> ASTRA understands the report regardless of the reporting vendor and converts it into a standardized molecular profile.

## Step 3

Show extracted profile.

Emphasize:

```text
disease
driver
VAF
MSI
TMB
```

where available.

## Step 4

Show approved evidence.

Say:

> Approved treatment evidence is deliberately separated from experimental clinical trials.

## Step 5

Show trial list.

Say:

> ASTRA searches current recruiting trials using both the disease and the molecular profile.

## Step 6

Open top trial.

Show:

```text
molecular rationale
eligibility
unknown criteria
nearest site
distance
```

## Step 7

Close with:

> The goal is not to replace an oncologist. It is to turn a static molecular report into a continuously searchable precision-oncology navigation layer.

---

# 19. Git Collaboration Strategy

Recommended branches:

```text
main

roberto-ingestion

abhishek-trials
```

Roberto modifies primarily:

```text
ingestion/
normalization/
evaluation/
schemas/molecular_profile.py
```

Abhishek modifies primarily:

```text
trials/
evidence/
ui/
schemas/match_results.py
```

Shared changes:

```text
schemas/
app/
```

should be coordinated.

---

# 20. Merge Order

Recommended:

### Merge 1

Shared schemas.

### Merge 2

Abhishek downstream pipeline using fixture JSON.

### Merge 3

Roberto ingestion pipeline.

### Merge 4

End-to-end connection.

### Merge 5

UI polish and evaluation.

This minimizes merge conflicts.

---

# 21. ASTRA/Codex Task Prompts

Both developers should give ASTRA/Codex narrow tasks rather than:

```text
Build the whole app.
```

Better:

### Roberto example

```text
Implement ingestion/classify_report.py.

Input is extracted PDF text.

Return vendor, assay, sample_type, and confidence.

Support Foundation Medicine, Tempus, Caris,
and TSO500/PierianDx reports.

Add unit tests using the provided fixtures.
Do not modify other modules.
```

### Abhishek example

```text
Implement trials/ranking.py.

Use the existing MolecularProfile and TrialCandidate models.

Calculate component scores for:
molecular match,
disease match,
eligibility,
phase/evidence,
recruitment,
geography.

Do not use an opaque LLM-generated total score.
Return the component scores and weighted total.

Add unit tests.
```

Small explicit tasks make parallel development much safer.

---

# 22. Critical Rule for Both Tracks

Do not allow an LLM to silently invent missing data.

Examples:

If the report does not contain ECOG:

```text
ECOG = null
```

not:

```text
ECOG = 0
```

If the trial does not list a site as recruiting:

do not assume the site is active.

If a report contains a VUS:

do not promote it to pathogenic.

If evidence is unavailable:

say evidence unavailable.

This rule should be enforced throughout the POC.

---

# 23. Definition of Done

The hackathon POC is complete when:

```text
real vendor PDF
      ↓
ASTRA extraction
      ↓
canonical molecular profile
      ↓
approved-treatment evidence
      ↓
live recruiting trial search
      ↓
eligibility prescreen
      ↓
nearest trial site
      ↓
ranked explainable result
```

works end-to-end for at least several reports from different vendors.

The project does not need to solve every oncology edge case.

The demo should prove that the architecture works and that ASTRA can bridge the gap between molecular diagnostic reporting and practical clinical-trial discovery.
