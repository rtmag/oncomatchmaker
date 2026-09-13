# ASTRA Precision Oncology Trial Matchmaker

## 1. Project Summary

ASTRA Precision Oncology Trial Matchmaker is an AI-assisted platform that converts molecular oncology reports into evidence-backed treatment and clinical-trial recommendations.

The long-term product vision is simple:

> A patient, oncologist, healthcare provider, or clinical research team uploads a molecular profiling report, and the platform identifies the most relevant approved targeted therapies and recruiting clinical trials based on the patient's tumor type, molecular alterations, clinical context, and geographic location.

The platform is designed around the reality that modern molecular oncology reports are heterogeneous. Reports from Foundation Medicine, Tempus, Caris, TSO500-based laboratories, and other genomic testing providers use different layouts, terminology, tables, annotations, and reporting conventions. Despite these differences, they ultimately describe a common set of concepts: disease context, detected molecular alterations, biomarkers, assay limitations, and sometimes treatment associations.

ASTRA acts as the reasoning and orchestration layer that transforms these heterogeneous reports into a common molecular representation and then connects that representation to current precision-oncology evidence and clinical-trial opportunities.

The hackathon proof-of-concept focuses on the core end-to-end workflow:

1. Upload a molecular oncology PDF report.
2. Identify the assay/vendor and report type.
3. Extract the tumor type and clinically relevant molecular findings.
4. Normalize findings into a canonical structured representation.
5. Identify potentially actionable biomarkers.
6. Separate approved standard-of-care treatment options from experimental clinical-trial opportunities.
7. Query recruiting clinical trials using molecular and disease context.
8. Evaluate molecular fit, disease fit, likely eligibility, and geographic accessibility.
9. Rank the most relevant trials.
10. Present transparent recommendations with rationale, evidence, source citations, and uncertainty.

The platform is not intended to replace an oncologist, molecular tumor board, genetic counselor, or clinical-trial coordinator. It is a decision-support and navigation system that helps users discover relevant options faster and understand why they may be relevant.

---

## 2. Problem Statement

Precision oncology has created a new information bottleneck.

A patient may receive a molecular profiling report containing findings such as:

- EGFR L858R
- KRAS G12C
- BRAF V600E
- PIK3CA H1047R
- BRCA1/2 loss
- MET amplification
- MET exon 14 skipping
- ERBB2 amplification
- ALK, RET, ROS1, NTRK, or FGFR fusions
- MSI-high
- tumor mutational burden
- homologous recombination deficiency
- clonal hematopoiesis-associated variants
- variants of uncertain significance

The report may already mention therapies associated with some findings, but the report is a snapshot. Clinical-trial availability changes continuously, trial eligibility criteria are complex, and the best experimental option may depend on combinations of disease type, molecular alteration, prior therapy, geography, performance status, organ function, and other factors.

The current process is fragmented across:

- molecular pathology reports,
- ClinicalTrials.gov,
- clinical-trial sponsor pages,
- CIViC and other variant knowledgebases,
- FDA and other regulatory sources,
- scientific literature,
- institutional trial websites,
- geographic site information,
- manual physician review.

This creates several problems:

1. **Report heterogeneity**  
   Different laboratories describe the same underlying molecular event in different ways.

2. **Information overload**  
   A report may contain many pathogenic, likely pathogenic, VUS, germline, clonal hematopoiesis, and technical findings.

3. **Context dependency**  
   The same alteration may be actionable in one cancer type but not another.

4. **Rapidly changing trial availability**  
   Trial status, sites, cohorts, and eligibility criteria change frequently.

5. **Geographic barriers**  
   A molecularly ideal trial may be inaccessible because the nearest recruiting site is far away.

6. **Eligibility complexity**  
   A patient may molecularly match a trial but fail eligibility because of prior therapy, ECOG status, laboratory values, CNS disease, organ function, age, or other factors.

7. **Lack of transparent prioritization**  
   Search engines can return hundreds of trials without explaining which are truly relevant.

ASTRA Precision Oncology Trial Matchmaker addresses this by creating an agentic workflow that connects molecular interpretation, clinical evidence, trial discovery, eligibility reasoning, and geographic accessibility.

---

## 3. Target Users

### 3.1 Patients and caregivers

Primary needs:

- understand whether a molecular report contains actionable findings,
- discover clinical trials relevant to the molecular profile,
- understand where those trials are located,
- generate a concise list to discuss with the treating oncologist,
- avoid manually searching hundreds of ClinicalTrials.gov records.

The patient-facing experience must use plain language and clearly distinguish between established therapies and experimental options.

### 3.2 Oncologists and healthcare providers

Primary needs:

- rapidly identify relevant trials,
- verify whether a genomic alteration is likely to be actionable,
- see concise evidence supporting the match,
- understand eligibility gaps,
- identify nearby recruiting centers,
- reduce manual search time.

The clinician-facing experience should expose more technical information and evidence provenance.

### 3.3 Molecular tumor boards

Primary needs:

- review complex profiles,
- evaluate multiple alterations,
- distinguish drivers from passengers or VUS,
- compare standard-of-care options with investigational strategies,
- review trial evidence systematically.

### 3.4 Clinical research teams and trial coordinators

Primary needs:

- identify patients who may fit an active trial,
- understand the molecular basis for a match,
- identify missing eligibility information,
- reduce prescreening workload.

### 3.5 Future institutional users

Potential users include:

- cancer centers,
- diagnostic laboratories,
- genomic testing providers,
- pharmaceutical clinical-development teams,
- CROs,
- patient advocacy groups,
- national precision-oncology programs.

---

## 4. Core Product Principle

The platform should be **report-vendor agnostic**.

The system should not contain separate downstream logic for Foundation Medicine, Tempus, Caris, TSO500, or other assays.

Instead:

```text
Heterogeneous report
        ↓
ASTRA report understanding
        ↓
Canonical molecular profile
        ↓
Shared therapy/trial matching pipeline
```

Once a report has been normalized, the trial-matching engine should operate independently of the original report format.

This separation is critical for scalability.

---

## 5. Hackathon Proof-of-Concept Scope

The POC should demonstrate the complete workflow on a curated corpus of approximately 14 publicly available vendor-issued clinical molecular oncology PDF reports.

The current corpus spans multiple report ecosystems, including:

- Foundation Medicine / FoundationOne,
- Tempus,
- Caris,
- TSO500/PierianDx-style clinical reporting.

The POC corpus includes a mixture of liquid-biopsy and tissue molecular oncology reports and covers diverse tumors and molecular scenarios.

Representative use cases include:

- NSCLC with EGFR mutation,
- NSCLC with KRAS G12C,
- NSCLC with MET exon 14 alteration,
- colorectal cancer with MSI-high,
- prostate cancer with BRCA2 alteration,
- breast cancer with PIK3CA alteration,
- tumors with BRAF V600E,
- fusion-driven disease,
- low tumor fraction,
- negative molecular reports,
- clonal hematopoiesis findings,
- multiple potentially actionable alterations.

The POC should focus on report understanding and trial matching rather than raw sequencing.

### In scope

- PDF upload,
- report classification,
- extraction of disease and molecular findings,
- canonical normalization,
- actionable-biomarker reasoning,
- approved therapy retrieval,
- recruiting trial retrieval,
- trial-site retrieval,
- geographic ranking,
- lightweight eligibility reasoning,
- evidence-backed ranking,
- clear UI,
- citations and provenance,
- evaluation against known report content.

### Out of scope for the hackathon

- FASTQ/BAM/CRAM processing,
- variant calling,
- germline interpretation,
- formal clinical eligibility determination,
- autonomous treatment recommendations,
- integration with EHR systems,
- production authentication,
- billing,
- HIPAA/GDPR production deployment,
- direct patient enrollment,
- contacting trial sites automatically,
- comprehensive global regulatory coverage,
- exhaustive molecular tumor board reasoning.

---

## 6. User Journey

### 6.1 Minimal POC journey

1. User opens the platform.
2. User uploads a molecular oncology PDF.
3. ASTRA recognizes the report provider and assay.
4. ASTRA extracts:
   - diagnosis,
   - sample type,
   - key biomarkers,
   - variants,
   - fusions,
   - CNVs,
   - MSI,
   - TMB,
   - relevant report warnings.
5. User confirms or edits the extracted diagnosis.
6. User provides optional clinical context:
   - age,
   - location,
   - disease stage,
   - prior therapies,
   - ECOG performance status,
   - major exclusions.
7. The system generates a standardized molecular profile.
8. The system identifies approved therapies relevant to the molecular context.
9. The system searches active recruiting clinical trials.
10. The system evaluates each trial.
11. The system ranks trials.
12. The UI shows:
    - approved therapies,
    - best clinical-trial matches,
    - molecular rationale,
    - likely eligibility,
    - unknown eligibility fields,
    - nearest recruiting site,
    - approximate distance,
    - phase,
    - recruitment status,
    - evidence sources.
13. The user can open the source trial or evidence record.

---

## 7. Functional Requirements

### FR-1: PDF ingestion

The platform must accept a clinical molecular oncology report in PDF format.

The system should support:

- native digital PDFs,
- scanned PDFs when readable,
- multi-page reports,
- different vendor layouts.

### FR-2: Vendor/assay recognition

The system should infer, when possible:

- vendor,
- assay name,
- sample type,
- report type,
- tissue versus liquid biopsy.

Example:

```json
{
  "vendor": "Foundation Medicine",
  "assay": "FoundationOne Liquid CDx",
  "sample_type": "plasma",
  "report_type": "comprehensive_genomic_profiling"
}
```

### FR-3: Disease extraction

The system should extract:

- primary diagnosis,
- histology,
- anatomical site,
- stage if available,
- metastatic status if available.

### FR-4: Molecular finding extraction

The system should extract relevant categories:

- SNVs,
- indels,
- copy-number alterations,
- fusions/rearrangements,
- splice alterations,
- MSI,
- TMB,
- HRD if present,
- tumor fraction if present,
- ctDNA fraction if present,
- VAF when reported.

### FR-5: Classification of report findings

Findings should be labeled where possible as:

- pathogenic,
- likely pathogenic,
- actionable,
- VUS,
- germline-associated,
- clonal hematopoiesis-associated,
- negative/not detected,
- technical limitation.

### FR-6: Normalization

The system should normalize:

- gene symbols,
- HGVS notation,
- common protein notation,
- cancer terminology,
- biomarker terminology.

Example:

```text
EGFR exon 21 L858R
EGFR p.Leu858Arg
EGFR L858R
```

should map to one normalized event.

### FR-7: Approved therapy retrieval

The system should identify therapy associations while distinguishing:

1. approved in the same indication,
2. tumor-agnostic approval,
3. approved in another indication,
4. investigational evidence only.

### FR-8: Clinical-trial retrieval

The system should search active trials using combinations of:

- cancer type,
- gene,
- variant,
- biomarker,
- therapeutic class,
- drug,
- pathway.

### FR-9: Recruitment filtering

Default trial filtering should prioritize:

- Recruiting,
- Not Yet Recruiting when useful,
- Active, Not Recruiting only as a secondary informational category.

Primary recommendations should emphasize currently recruiting opportunities.

### FR-10: Trial site extraction

For each trial, identify:

- recruiting sites,
- city,
- region/state,
- country,
- contact details when available.

### FR-11: Geographic ranking

Given a patient location, rank sites by distance or travel accessibility.

Initial POC:

- latitude/longitude,
- straight-line distance,
- nearest recruiting location.

Future:

- travel time,
- flight availability,
- cross-border burden,
- visa requirements,
- trial-related travel support.

### FR-12: Eligibility reasoning

The system should compare known patient information with trial inclusion/exclusion criteria.

Possible statuses:

```text
LIKELY_MATCH
POSSIBLE_MATCH
INSUFFICIENT_INFORMATION
LIKELY_NOT_ELIGIBLE
```

The system must never claim definitive eligibility unless formally confirmed by the trial site.

### FR-13: Explainability

Every recommendation should include:

- why the molecular profile matches,
- why the cancer context matches,
- key eligibility conditions,
- unresolved eligibility questions,
- evidence source,
- recruitment status,
- nearest site.

### FR-14: Citation/provenance

Every external claim should be traceable to the source used.

---

## 8. Canonical Molecular Profile

All reports should be transformed into a shared JSON structure.

Example:

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
    "normalized": "Non-small cell lung cancer",
    "histology": null,
    "stage": "metastatic"
  },
  "patient_context": {
    "age": null,
    "sex": null,
    "location": {
      "city": null,
      "country": null,
      "latitude": null,
      "longitude": null
    },
    "prior_therapies": [],
    "ecog": null
  },
  "biomarkers": {
    "snv_indel": [
      {
        "gene": "KRAS",
        "protein_change": "p.G12C",
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
      "value": null,
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

The schema should retain both:

- normalized interpretation,
- original source text.

This is essential for auditability.

---

## 9. Report Ingestion Pipeline

### Stage 1: Document intake

Input:

```text
PDF
```

Output:

```text
document representation
```

ASTRA determines:

- page structure,
- report provider,
- assay,
- likely key result sections.

### Stage 2: Report classification

Identify:

```text
FoundationOne
Tempus
Caris
TSO500/PierianDx
unknown
```

Vendor detection should help parsing but should not lock the system into hard-coded templates.

### Stage 3: Result extraction

ASTRA should locate sections such as:

- genomic findings,
- biomarkers,
- therapies,
- variants of unknown significance,
- assay limitations,
- clonal hematopoiesis,
- tumor fraction,
- diagnosis.

### Stage 4: Schema conversion

Convert extracted content into canonical JSON.

### Stage 5: Validation

Run deterministic checks:

- gene symbol exists,
- variant syntax plausible,
- VAF range valid,
- TMB numeric,
- MSI category recognized,
- diagnosis non-empty.

### Stage 6: Confidence estimation

Low-confidence extractions should be surfaced to the user.

Example:

```text
Tumor type: "Adenocarcinoma" — confidence 0.64
Please confirm primary site.
```

---

## 10. Actionability Layer

The system should not equate every detected variant with a therapeutic target.

For each molecular finding, ASTRA should determine:

### 10.1 Biological relevance

Possible categories:

- established oncogenic driver,
- likely oncogenic,
- resistance alteration,
- predictive biomarker,
- prognostic biomarker,
- uncertain significance,
- likely passenger,
- possible clonal hematopoiesis.

### 10.2 Disease-context relevance

Actionability depends on tumor context.

Example:

```text
BRAF V600E
```

has different therapeutic implications in:

- melanoma,
- colorectal cancer,
- NSCLC,
- thyroid cancer.

Therefore the matching unit should be:

```text
disease + molecular alteration
```

not simply:

```text
molecular alteration
```

### 10.3 Evidence hierarchy

Evidence should be grouped into:

#### Level A — approved therapy in the same disease

Highest clinical relevance.

#### Level B — tumor-agnostic approved therapy

Example classes include biomarkers such as NTRK fusion or MSI-high when applicable.

#### Level C — approved therapy in another disease

Potential biological relevance but not standard treatment for the current tumor.

#### Level D — clinical-trial evidence

Investigational treatment.

#### Level E — preclinical/biological evidence

Should not be presented as a clinical recommendation.

---

## 11. Separation of Standard-of-Care and Clinical Trials

This is a core safety and UX requirement.

The interface must not mix approved therapies and experimental trials into one ranking.

Recommended structure:

```text
Approved / Established Treatment Options

Clinical Trial Opportunities

Other Molecular Findings
```

A Phase I trial must never appear to outrank an approved therapy merely because the trial is geographically close.

Clinical trials are experimental opportunities and should be labeled accordingly.

---

## 12. Trial Retrieval

The trial search engine should generate multiple queries from the molecular profile.

Example patient:

```text
NSCLC
EGFR L858R
MET amplification
```

Possible searches:

```text
NSCLC EGFR L858R
NSCLC EGFR mutation
NSCLC MET amplification
EGFR inhibitor resistance MET
EGFR MET combination
```

ASTRA should consolidate duplicated trial results.

### Sources

Primary:

- ClinicalTrials.gov via BioMCP or equivalent structured access.

Potential supporting sources:

- CIViC,
- regulatory databases,
- PubMed,
- sponsor trial pages,
- other authoritative precision-oncology knowledgebases.

---

## 13. BioMCP Role

BioMCP can act as the biomedical retrieval layer.

Potential functions include:

- variant lookup,
- drug lookup,
- disease context,
- trial search,
- trial details,
- trial locations,
- biomedical literature retrieval.

The design should keep BioMCP behind an abstraction layer so another data source can be substituted later.

Example:

```python
search_trials(profile)
get_trial_details(nct_id)
get_variant_evidence(variant, disease)
get_drug_evidence(drug, disease, biomarker)
```

---

## 14. Trial-Matching Logic

Each candidate trial receives component scores rather than a single opaque LLM judgment.

### 14.1 Molecular Match Score

Questions:

- Is the exact variant required?
- Is the gene sufficient?
- Is the pathway sufficient?
- Is the trial biomarker-specific?
- Does the patient have an exclusionary resistance mutation?

Example scale:

```text
30 exact variant match
25 exact biomarker class
20 same gene
10 related pathway
0 no meaningful molecular match
```

### 14.2 Disease Match Score

Example:

```text
15 exact histology
12 exact disease family
8 basket/pan-tumor trial
0 incompatible disease
```

### 14.3 Eligibility Compatibility Score

Known inclusion/exclusion fields can contribute positively or negatively.

Potential fields:

- age,
- stage,
- prior therapy,
- line of therapy,
- ECOG,
- measurable disease,
- organ function,
- CNS metastases,
- prior targeted therapy.

Unknown variables should reduce confidence rather than being treated as failures.

### 14.4 Trial Evidence / Development Score

Possible considerations:

- phase,
- biomarker specificity,
- published activity,
- regulatory status of the agent,
- expansion cohort versus dose-escalation.

This score should not imply therapeutic effectiveness.

### 14.5 Recruitment Score

```text
Recruiting at nearest site
Recruiting but site status uncertain
Not yet recruiting
Active but not recruiting
```

### 14.6 Geography Score

Initial POC:

```text
distance_km
```

Example continuous function:

```text
distance_score = exp(-distance_km / 250)
```

Alternative human-readable bands:

```text
0–25 km       Excellent
25–100 km     Very good
100–300 km    Moderate
300–1000 km   Difficult
>1000 km      Very difficult
```

### 14.7 Composite Trial Score

Example:

```text
Molecular match       30
Disease match         15
Eligibility           20
Trial evidence        10
Recruitment           10
Geography             15
                      ---
Total                100
```

Weights should remain configurable.

The UI should display the component scores so the ranking is interpretable.

---

## 15. Geographic Accessibility

Location is a major differentiator of the platform.

The same trial may recruit at many sites.

For every candidate trial:

1. retrieve all recruiting sites,
2. geocode them,
3. calculate distance from patient location,
4. identify the nearest recruiting site,
5. retain alternative sites.

Example:

```json
{
  "nct_id": "NCT01234567",
  "nearest_site": {
    "name": "Example Cancer Centre",
    "city": "Singapore",
    "country": "Singapore",
    "distance_km": 8.4
  }
}
```

Future versions could account for:

- direct flights,
- domestic versus international travel,
- travel time,
- visa requirements,
- lodging burden,
- trial reimbursement.

---

## 16. Eligibility Reasoning

Eligibility analysis should be treated as **prescreening**, never final eligibility determination.

ASTRA can map each criterion to:

```text
MATCH
MISMATCH
UNKNOWN
NOT_APPLICABLE
```

Example:

```text
Age >= 18                    MATCH
Metastatic NSCLC             MATCH
EGFR mutation                MATCH
Prior osimertinib required   UNKNOWN
ECOG 0–1                     UNKNOWN
No untreated CNS disease     UNKNOWN
```

Result:

```text
Likely molecular match.
Additional clinical screening required.
```

The system should generate a list of missing information that would improve screening.

---

## 17. ASTRA Agent Architecture

A modular agent structure is preferable to a monolithic prompt.

### Agent 1 — Report Interpreter

Responsibilities:

- identify vendor,
- identify assay,
- extract diagnosis,
- extract findings,
- distinguish report sections,
- build canonical JSON.

### Agent 2 — Molecular Normalizer

Responsibilities:

- normalize gene names,
- normalize variants,
- normalize disease terminology,
- classify biomarker types,
- identify possible CH/VUS warnings.

### Agent 3 — Actionability Agent

Responsibilities:

- query evidence,
- identify approved therapies,
- distinguish same-disease versus cross-disease evidence,
- generate search concepts.

### Agent 4 — Trial Discovery Agent

Responsibilities:

- generate trial queries,
- call ClinicalTrials.gov/BioMCP,
- retrieve candidate trials,
- deduplicate.

### Agent 5 — Eligibility Agent

Responsibilities:

- parse eligibility,
- compare criteria with known patient context,
- identify unknowns,
- generate eligibility confidence.

### Agent 6 — Geographic Agent

Responsibilities:

- retrieve sites,
- identify active locations,
- calculate nearest site,
- compute geographic score.

### Agent 7 — Ranking Agent

Responsibilities:

- combine structured scores,
- rank trials,
- generate explanations.

### Agent 8 — Evidence/Response Agent

Responsibilities:

- present results,
- provide citations,
- maintain clear separation between approved and experimental options,
- communicate uncertainty.

---

## 18. System Architecture

```text
                         ┌────────────────────┐
                         │      Web UI        │
                         └─────────┬──────────┘
                                   │
                             Upload PDF
                                   │
                         ┌─────────▼──────────┐
                         │ Report Interpreter │
                         └─────────┬──────────┘
                                   │
                         Canonical JSON
                                   │
                         ┌─────────▼──────────┐
                         │ Molecular          │
                         │ Normalizer         │
                         └─────────┬──────────┘
                                   │
                  ┌────────────────┴────────────────┐
                  │                                 │
        ┌─────────▼──────────┐            ┌────────▼────────┐
        │ Actionability      │            │ Trial Discovery │
        │ / Evidence         │            │                 │
        └─────────┬──────────┘            └────────┬────────┘
                  │                                │
                  │                       Candidate Trials
                  │                                │
                  │                 ┌──────────────┴─────────────┐
                  │                 │                            │
                  │        ┌────────▼────────┐          ┌────────▼────────┐
                  │        │ Eligibility     │          │ Geography      │
                  │        │ Reasoning       │          │ / Site Match   │
                  │        └────────┬────────┘          └────────┬────────┘
                  │                 │                            │
                  └─────────────────┴────────────┬───────────────┘
                                                 │
                                      ┌──────────▼─────────┐
                                      │ Trial Ranker       │
                                      └──────────┬─────────┘
                                                 │
                                      ┌──────────▼─────────┐
                                      │ Evidence-backed UI │
                                      └────────────────────┘
```

---

## 19. Suggested Software Modules

```text
app/
  main.py

ingestion/
  pdf_reader.py
  report_classifier.py
  report_extractor.py

schemas/
  molecular_profile.py
  trial_candidate.py

normalization/
  genes.py
  variants.py
  disease.py

evidence/
  biomcp_client.py
  civic_client.py
  regulatory.py

trials/
  search.py
  parser.py
  eligibility.py
  geography.py
  ranking.py

ui/
  upload.py
  profile_review.py
  therapy_results.py
  trial_results.py

evaluation/
  corpus_manifest.json
  ground_truth.json
  evaluate_extraction.py
  evaluate_matching.py
```

The actual framework can be adapted to the hackathon tooling.

---

## 20. User Interface

### Screen 1 — Upload

```text
Upload your molecular oncology report
[ Choose PDF ]

Optional:
Location
Age
Previous treatments
```

### Screen 2 — Extracted Profile

The system shows:

```text
Cancer:
Metastatic NSCLC

Report:
Caris Assure

Detected biomarkers:
KRAS G12C
STK11 mutation
KEAP1 mutation

MSI:
Stable

TMB:
8 mut/Mb
```

The user can correct extracted information.

### Screen 3 — Approved Therapy Evidence

Example:

```text
APPROVED THERAPY OPTIONS

KRAS G12C-directed therapy

Why shown:
The report contains KRAS G12C in NSCLC.

Evidence:
[regulatory / clinical evidence links]
```

No direct prescribing advice should be generated.

### Screen 4 — Clinical Trials

Example:

```text
#1 NCT01234567
Next-generation KRAS G12C inhibitor

Molecular match      30/30
Disease match        15/15
Eligibility          12/20
Recruitment          10/10
Geography            14/15

Overall              91/100

Nearest recruiting site:
8.2 km

Potential match because:
KRAS G12C-positive NSCLC is explicitly required.

Missing information:
- prior KRAS G12C inhibitor exposure
- ECOG status
- brain metastasis status
```

### Screen 5 — Trial Detail

Show:

- NCT ID,
- official title,
- phase,
- sponsor,
- intervention,
- molecular inclusion criteria,
- major eligibility criteria,
- locations,
- source link.

---

## 21. Explainability

Every recommendation should answer:

1. **What molecular finding triggered this result?**
2. **Why is it relevant to this cancer?**
3. **Is the therapy approved or experimental?**
4. **Why does this trial match?**
5. **What eligibility criteria are known to match?**
6. **What information is still missing?**
7. **Where is the nearest recruiting site?**
8. **What is the source?**

The system should never produce unexplained rankings.

---

## 22. Safety Requirements

This is a medical decision-support product and must use conservative language.

### Required safety behaviors

The system must not say:

```text
You should take Drug X.
```

It may say:

```text
Drug X is an approved targeted therapy associated with this biomarker and disease context. Treatment decisions should be discussed with the treating oncology team.
```

The system must not say:

```text
You are eligible for this trial.
```

It may say:

```text
This trial appears to be a potential molecular match. Formal eligibility must be confirmed by the study team.
```

### Additional safeguards

- Separate approved therapies from experimental trials.
- Do not interpret VUS as actionable without evidence.
- Do not treat CH-associated variants as tumor targets.
- Surface uncertainty.
- Show evidence provenance.
- Avoid inferring missing clinical information.
- Flag outdated or unavailable evidence.
- State recruitment status and retrieval date.
- Encourage confirmation with treating clinicians.

---

## 23. Privacy and Security

The hackathon POC should use public sample reports.

A production platform would need stronger controls because molecular reports may contain:

- patient name,
- date of birth,
- medical record number,
- accession number,
- physician details,
- institution,
- genomic information.

Future requirements include:

- encryption in transit,
- encryption at rest,
- configurable data retention,
- automatic PHI redaction,
- user-controlled deletion,
- access logs,
- role-based access,
- regional data residency,
- HIPAA/GDPR/PDPA review where applicable.

A privacy-aware future workflow could remove identifying information before sending content to downstream tools.

---

## 24. Evaluation Corpus

The current POC uses approximately 14 public vendor-issued molecular oncology PDF reports.

The corpus should be tracked in a manifest.

Example:

```json
{
  "case_id": "CASE_001",
  "vendor": "Foundation Medicine",
  "assay": "FoundationOne Liquid CDx",
  "tumor_type": "NSCLC",
  "sample_type": "plasma",
  "expected_key_findings": [
    "EGFR L858R"
  ]
}
```

The PDF corpus should remain unchanged.

Ground-truth annotations should be stored separately.

---

## 25. Evaluation Strategy

Evaluation should test the system at multiple stages.

### 25.1 Report classification accuracy

Metric:

```text
correct vendor / total reports
```

### 25.2 Disease extraction accuracy

Compare:

- raw diagnosis,
- normalized cancer type.

### 25.3 Molecular extraction accuracy

Calculate:

- precision,
- recall,
- F1.

Example:

```text
Expected:
EGFR L858R
TP53 R273H

Extracted:
EGFR L858R
TP53 R273H

Precision = 1.0
Recall = 1.0
```

### 25.4 Biomarker-type accuracy

Verify correct distinction between:

- SNV,
- indel,
- CNV,
- fusion,
- MSI,
- TMB.

### 25.5 CH/VUS safety

Important safety metrics:

```text
CH variants incorrectly treated as tumor targets = 0
VUS variants incorrectly treated as established targets = 0
```

### 25.6 Trial retrieval quality

For curated cases, manually define several expected high-value trials where possible.

Evaluate:

- whether relevant trials appear in top 5,
- whether irrelevant trials dominate,
- whether recruiting status is correct.

Potential metric:

```text
Recall@5
```

### 25.7 Ranking quality

Manually compare top-ranked trials against expert expectations.

### 25.8 Citation accuracy

Each recommendation should contain retrievable evidence.

---

## 26. Hackathon Success Metrics

A successful hackathon POC should demonstrate:

### Minimum

- upload at least one vendor PDF,
- extract tumor type,
- extract molecular findings,
- search trials,
- return a ranked list.

### Strong submission

- successfully parse multiple vendors,
- normalize all reports into one schema,
- separate approved therapies and trials,
- rank recruiting trials,
- include location/distance,
- explain eligibility gaps,
- cite sources.

### Exceptional submission

- robust performance across the 14-report benchmark,
- interpretable component-level scoring,
- clear handling of CH/VUS/negative reports,
- transparent agent orchestration,
- strong visual demonstration,
- evaluation metrics,
- seamless end-to-end user experience.

---

## 27. Recommended Demo Cases

The live demo should use cases with obvious but different reasoning pathways.

### Demo A — canonical targeted mutation

Example:

```text
NSCLC + EGFR driver
```

Demonstrates:

- report extraction,
- approved therapy identification,
- trial matching.

### Demo B — trial-rich alteration

Example:

```text
NSCLC + KRAS G12C
```

Demonstrates:

- multiple experimental agents,
- trial ranking,
- prior-treatment eligibility questions.

### Demo C — pan-tumor biomarker

Example:

```text
MSI-high colorectal cancer
```

Demonstrates:

- biomarker-level actionability.

### Demo D — complex safety case

Example:

```text
Caris liquid biopsy with tumor findings + clonal hematopoiesis findings
```

Demonstrates:

- correct exclusion of CH variants.

### Demo E — negative report

Demonstrates:

- graceful handling when no obvious actionable alteration exists,
- disease-driven trial search,
- avoidance of hallucinated biomarkers.

---

## 28. Demo Story

The strongest presentation narrative is:

### Before

A patient receives a 15-page molecular report.

The patient or physician then has to manually:

- interpret molecular findings,
- decide what is actionable,
- search ClinicalTrials.gov,
- read eligibility criteria,
- identify sites,
- determine which trials are realistic.

### After

The report is uploaded to ASTRA.

Within one workflow the system produces:

```text
MOLECULAR PROFILE
       ↓
ACTIONABLE FINDINGS
       ↓
APPROVED OPTIONS
       ↓
RECRUITING TRIALS
       ↓
ELIGIBILITY PRESCREEN
       ↓
NEAREST SITE
       ↓
RANKED EXPLAINABLE RESULTS
```

The key product insight is:

> Precision oncology is no longer limited by the ability to generate genomic data. Increasingly, the bottleneck is converting genomic findings into timely, practical, geographically accessible clinical options.

ASTRA addresses that decision and navigation bottleneck.

---

## 29. Important Edge Cases

The system should be designed to eventually handle:

- no actionable variants,
- low tumor fraction,
- insufficient ctDNA,
- multiple primary tumors,
- unknown primary,
- conflicting disease names,
- multiple driver alterations,
- resistance mutations,
- VUS-only reports,
- clonal hematopoiesis,
- potential germline findings,
- rare fusions,
- unusual transcript notation,
- tumor-agnostic biomarkers,
- trials requiring a specific prior therapy,
- trials restricted to a line of therapy,
- trials with no nearby sites,
- stale recruitment data,
- report therapies that are outdated relative to current evidence.

---

## 30. Future Roadmap

### Phase 1 — Hackathon POC

- PDF ingestion,
- four report ecosystems,
- canonical schema,
- BioMCP/ClinicalTrials.gov retrieval,
- basic therapy evidence,
- ranked trials,
- distance scoring,
- simple UI.

### Phase 2 — Robust clinical prototype

- larger report library,
- stronger variant normalization,
- oncology ontology integration,
- richer eligibility parser,
- trial site contact information,
- automated updates,
- clinician review mode,
- exportable summary.

### Phase 3 — Longitudinal patient profile

Allow users to maintain:

- diagnosis,
- treatments,
- progression events,
- genomic reports over time,
- imaging,
- laboratory values.

The trial matcher could then understand treatment history and resistance evolution.

### Phase 4 — Continuous monitoring

Instead of one-time matching:

```text
Patient profile
      ↓
continuous trial monitoring
      ↓
new relevant trial appears
      ↓
notification
```

### Phase 5 — Clinical integration

Potential integrations:

- EHR,
- laboratory systems,
- molecular tumor board software,
- trial management platforms.

### Phase 6 — Global access intelligence

Add:

- travel time,
- cross-border access,
- visa requirements,
- trial travel reimbursement,
- remote-consent availability,
- decentralized trial elements.

---

## 31. Product Differentiation

Clinical-trial search itself is not novel.

The differentiated product is the entire chain:

```text
unstructured clinical genomic report
             ↓
structured molecular interpretation
             ↓
context-aware actionability
             ↓
live trial retrieval
             ↓
eligibility prescreen
             ↓
geographic accessibility
             ↓
interpretable ranking
```

Key differentiators:

1. vendor-agnostic molecular report ingestion,
2. agentic reasoning rather than keyword search,
3. disease + molecular-context matching,
4. approved-versus-experimental separation,
5. eligibility-aware ranking,
6. geographic accessibility,
7. evidence provenance,
8. patient-friendly and clinician-friendly explanations.

---

## 32. Long-Term Vision

The end-state product is a continuously updated precision-oncology navigation layer.

A user should eventually be able to provide:

```text
molecular report
pathology
treatment history
clinical status
location
```

and receive:

```text
relevant approved options
relevant biomarker-directed trials
eligibility gaps
nearest recruiting locations
evidence
questions to discuss with the treating team
```

The platform should evolve from a report matcher into a longitudinal precision-oncology assistant that continuously reassesses opportunities as the disease, treatment history, molecular profile, and clinical-trial landscape change.

The central principle should remain constant:

> Turn complex molecular oncology information into transparent, evidence-backed, practically accessible clinical options without replacing clinical judgment.

---

## 33. ASTRA Expert-Team Contract

Trial matching will use an evidence-bounded virtual review team rather than a
single keyword query or an unconstrained model response. The shared canonical
molecular profile remains the only interface between report extraction and
downstream matching.

The first expert-team implementation contains six independent roles:

1. molecular-profile quality control,
2. disease-specific oncology review,
3. actionability and evidence review,
4. pathway and resistance review,
5. trial-cohort and eligibility review,
6. safety and contradiction review.

A deterministic consensus layer combines their structured assessments. Explicit
molecular, eligibility, or safety conflicts are hard gates and cannot be
overridden by majority support. Unknown stage, prior therapy, performance status,
laboratory values, germline status, zygosity, and other absent facts remain
unknown and prevent a claim of eligibility.

Candidate retrieval must record whether a study was found through an exact
variant, gene-level relationship, phenotype biomarker, pathway mechanism,
resistance strategy, or broad basket cohort. Direct matches, mechanistic matches,
and exploratory basket matches must remain distinguishable in the result.

Role definitions and the dependency-free executable contracts live in
`trials/astra_team.py` and `schemas/astra_contracts.py`. Model-provider integration,
CIViC retrieval, wider candidate generation, geography, and UI remain separate
implementation phases. All outputs remain clinical-trial prescreening decision
support and never constitute medical advice or a final eligibility determination.

---

## 34. Independent Clinical and Geographic Scores

Geographic accessibility must not be included inside the multidimensional
clinical-trial match score. ASTRA produces two independent values:

1. a clinical composite derived from molecular, disease, mechanistic, evidence,
   eligibility, and trial-design assessments;
2. a geographic-access score derived from the nearest explicitly recruiting site.

Only trials that survive molecular, disease, eligibility, and safety conflict
gates are clinically rankable. Unknown clinical dimensions remain null and reduce
reported evidence coverage. The conservative clinical composite is the observed
weighted score multiplied by coverage.

Geography is calculated only when the study status and individual site status are
both `RECRUITING`. No confirmed open site or no calculable distance produces a
null geography score rather than a false zero.

The two scores can later be plotted with clinical match on the x-axis and
geographic access on the y-axis. High-match, high-access trials occupy the
upper-right quadrant. Nearby but biologically weak trials cannot improve their
clinical score, while biologically strong but distant trials remain visible in a
separate high-match, low-access quadrant.

The POC score and quadrant thresholds are transparent, configurable prioritization
aids. They are not estimates of therapeutic benefit, eligibility probability, or
clinically validated cutoffs.

The staged merge order, component interfaces, report-result requirements, and
integration sign-off gates are maintained in `INTEGRATION_PLAN.md`.
