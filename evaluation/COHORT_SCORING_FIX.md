# Cohort-aware clinical scoring regression — 2026-09-13

Branch: `fix/cohort-aware-scoring`. Registry snapshot: `2026-09-13-v1`.
Policies: `registry-features-v2`, `clinical-fit-v3`.

## Changes

- Specific inclusion clauses override broad titles. Marker and disease context
  cannot be borrowed from different arms/subprotocols. Unknown cohort applicability
  stays unscored and may appear as an exploratory lead, not a confirmed exclusion.
- Explicit MET exon 14, MSI-H/dMMR versus MSS/pMMR, gene-bound variant lists,
  fusions and copy-number events receive bounded, source-linked interpretation.
  Negation is sentence-local. VUS, potential CH and review-required findings remain
  excluded from positive molecular evidence. MET no longer matches “metastatic”.
- Scores sum supported weighted points on a fixed 100-point denominator. A disease
  signal of 0.9 earns 13.5 points, not 90. Unknown dimensions retain coverage/bounds.
  Expert and provisional coordinates use identical arithmetic; neither is calibrated
  as a probability. Review can legitimately lower a score.
- Clinical support, supported geographic options and exact-marker review queues are
  interleaved within the existing review budget. Geography does not change clinical
  points or rescue missing molecular support. Failed/conflicting reviews trigger
  continued evaluation of remaining allocated candidates, up to the budget.
- UI filters share coordinates; old v2 scores are not silently relabeled. Reasons
  appear for scored/unscored records. Feature rebuilds publish atomically so readers
  never consume a partially rebuilt companion. Original registry/PDF files unchanged.

## Full-snapshot offline replay

Four previously extracted public-report profiles plus one explicitly synthetic
cholangiocarcinoma/KRAS G12D profile; Daegu city coordinates. Each replay screened
all 26,423 studies, attached recruiting-site geography, and allocated 20 reviews.
Times exclude feature loading, extraction and live expert calls.

| Profile | Local screening + geography + selection | Candidate pool | Earlier positive references selected |
| --- | ---: | ---: | --- |
| EGFR L858R lung | 8.25 s | 556 | NCT06641609, NCT04181060 |
| MET exon 14 NSCLC | 8.52 s | 308 | NCT06031688, NCT07619339 |
| BRCA2 loss prostate | 7.18 s | 371 | NCT06952803 |
| MSI-H colon | 7.68 s | 70 | NCT05310643, NCT07807800 |
| Synthetic cholangiocarcinoma KRAS G12D | 7.43 s | 69 | NCT06040541 |

The seven earlier positive reference examples are now selected in this Daegu
replay (previous experiment: 2/7). These are weak regression labels, not independent
clinical ground truth; this small result is not a general accuracy estimate.

NCT05067283 (G12C-specific) and NCT06162221 (G12D NSCLC cohort) receive no supported
score or review slot for the synthetic cholangiocarcinoma profile. The genuine
G12D solid-tumor basket NCT06040541 remains selected. NCT07446322, with its recorded
MSS/non-MSI-H requirement, is not selected for the MSI-H profile. All five replays
had zero provisional scores ≥80 with coverage ≤45% (an arithmetic invariant, not
a clinical validation result).

## Verification and limits

Run `python -m evaluation.cohort_scoring_regression` and `python -m pytest -q`.
Regression tests cover multiple genes/alleles, cross-cohort mixing, positive and
negative MSI wording, sentence-local negation, separate disease criteria, explicit
unscoped requirements, source immutability, atomic rebuild failure, review budget
deduplication, and failure → hard conflict → successful review. Frontend tests cover
coordinate identity, conflict removal, old-score rejection and honest downward
expert refinement; TypeScript and production build succeed.

No fresh Sol extraction or live Astra calls were performed for this change. Pipeline
failure/recovery tests use explicitly synthetic expert outputs. No extra model calls
or dependencies were introduced. The local pass takes approximately 7–9 seconds in
this replay; this is not a claim that full end-to-end processing takes that long.

The parser remains conservative and bounded, not a complete eligibility logic
engine. Complex combinations, unrecognized diseases, assay/germline/biallelic
qualifications and ambiguous cohort context require review and can lose local
support. Registry/site recruitment was not refreshed. These checks do not establish
enrollment eligibility, compassionate access, treatment benefit, or the best trial.
Fresh searches are required to use v3; earlier cached reports are not rewritten.
