# Molecular-profile trial matching spike

This is a small, location-free evaluation of whether a language model can
distinguish plausible molecular trial candidates from misleading registry search
hits. It is not the production matcher and does not replace Track A extraction.

Four report-derived fixtures cover EGFR L858R lung adenocarcinoma, MET exon 14
NSCLC, BRCA2-loss prostate adenocarcinoma, and MSI-high metastatic colon cancer.
Only facts apparent in the public sample reports were transcribed. Unknown stage,
therapy history, performance status, laboratory values, germline status, and
deletion zygosity remain unknown. The PDFs are unchanged and remain ignored by
Git.

Each case is paired with three complete ClinicalTrials.gov records from the local
2026-09-13 snapshot. The set intentionally contains attractive candidates and
hard negatives. The packet builder supplies full eligibility text to the model but
does not supply sites or locations:

```bash
python3 evaluation/run_molecular_matching_spike.py \
  data/snapshots/2026-09-13-v1/oncology.sqlite \
  --output evaluation/matching_spike/generated/model_packet.json
```

## Initial result

The ChatGPT assessment classified 7 of 12 pairs as molecular/disease candidates,
2 as having insufficient biomarker evidence, and 3 as direct conflicts. Every
candidate still requires clinical prescreening; none is labeled eligible.

| Report fixture | Candidate | Insufficient biomarker evidence | Conflict |
|---|---:|---:|---:|
| EGFR L858R NSCLC | 2 | 0 | 1 |
| MET exon 14 NSCLC | 2 | 0 | 1 |
| BRCA2-loss prostate | 1 | 2 | 0 |
| MSI-high metastatic colon | 2 | 0 | 1 |

The pressure tests behaved correctly: EGFR- and MET-excluding lung trials were
rejected; an MSI-high report was not matched to an MSS-only trial; and tumor
BRCA2 loss was not treated as proof of an inherited BRCA2 variant. This supports
using a language model for criterion-aware prescreening, provided deterministic
guardrails retain unknowns and a clinician or trial team verifies eligibility.

`chatgpt_assessments.json` is the auditable result of this one-off model review.
It records rationale, missing clinical facts, and direct registry links for every
profile/trial pair. Geography is deliberately deferred.
