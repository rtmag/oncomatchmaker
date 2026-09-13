# Fixed-support / geographic review-allocation experiment

## Decision

**Do not roll out this proposal as a complete matching fix yet.** Fixed-denominator
support solves the demonstrated arithmetic inflation. Geography-aware review
allocation improves domestic representation, but still admits unsupported
cohort/allele matches and does not improve the small regression-reference set.
The application policy was not changed by this experiment.

## Scope and reproducibility

Run `.venv/bin/python -m evaluation.test_support_strategy` from the repository root.
It prints complete metrics and both selected ID sets. It reads the original local
26,423-study snapshot and its existing feature companion without editing either.

Inputs: four saved profiles from `evaluation/matching_spike/profiles.json` (EGFR,
MET exon 14, BRCA2 loss, MSI-high), plus explicitly synthetic cholangiocarcinoma
KRAS G12D and negative controls. Each was evaluated for Daegu, Singapore, Sydney,
New York and Paris: 30 profile/location scenarios. This was **not** a new extraction
of all 12 PDFs and made no new LLM calls.

Reference labels are seven previously model-identified candidate trials and
three previously identified conflicts, not an independently adjudicated clinical
gold standard. Saved demo expert arrays were not treated as fresh independent
six-agent assessments. The current candidate pool was held constant to isolate
score/display changes and review allocation, not to claim complete retrieval.

Baseline: current score × coverage selection, up to 20 reviews. Proposal: eight
support-priority slots, six access-priority slots with a provisional disease and
molecular signal (or a negative profile), six uncertainty-priority slots; dedupe
and fill to 20. These quotas are an uncalibrated experimental choice.

## Results

| Check | Result |
|---|---|
| Disease-only score, 15% coverage | 90 before → 13.5 fixed support |
| All-unknown or hard conflict | Remains null |
| Six hypothetical caution assessments | 60 fixed support |
| Scores ≥80 with ≤45% coverage across the six profiles | 4,745 patient–trial pairs before → 0 after (an arithmetic property, not clinical validation) |
| Synthetic G12D cholangiocarcinoma, Daegu: domestic-site trials in review set | 3/20 → 9/20 |
| RMC-9805 in G12D review set | Retained in both policies in all five cities |
| Seven earlier candidate references selected | 2/7 per city under both policies; not improved |
| Earlier MET exon 14 candidate references | Both retrieved, neither selected under either policy |
| Earlier MSI-high candidate references | Both retrieved, neither selected under either policy |
| Earlier MSI-high conflict reference | Selected for review under both policies in all five cities |
| Budget/deduplication/exclusion mechanics | Assertions passed; synthetic replacement helper tested, not a live sequential expert run |

The EGFR experiment swapped one reference candidate for another, while the BRCA2
reference remained selected. More domestic sites does not establish better
clinical compatibility. These are selection-for-review results, not recommended
or eligible patients. The experiment took 67.19 seconds total, with each profile
screening pass taking 3.29–5.10 seconds; it excludes extraction and model latency.

## Manual checks of newly selected G12D/Daegu leads

The preserved snapshot eligibility text exposed concrete feature problems:

- NCT05067283 (MK-1084): the broad title says KRAS mutant, but the inspected
  enrollment arms specify **KRAS G12C**. The local title-level gene signal earned
  positive credit for the synthetic G12D profile without establishing G12C.
- NCT06162221 (RAS inhibitors): Subprotocol A requires G12C solid tumors;
  the G12D Subprotocol C/D entries require **NSCLC**. Combining broad solid-tumor
  wording with G12D text across subprotocols does not establish a cholangiocarcinoma
  cohort. It still entered the experimental uncertainty review allocation.
- NCT06031688 and NCT07619339 explicitly describe MET exon 14 skipping, but the
  local scoring implementation does not adequately score that event representation.
- NCT05310643 and NCT07807800 specify MSI/dMMR context, while NCT07446322 specifies
  non-MSI-high/non-dMMR status. The current local scorer lacks the needed phenotype
  assessment to prioritize those positive references and hold the contradictory one.

These observations concern the local snapshot, not independently reverified
current availability. Inspect original registry records before clinical use.

## Interpretation and next steps

1. Retain fixed-denominator support as a candidate **display and allocation**
   metric, with unknown dimensions and score bounds visible. It does not guarantee
   reviewed scores are always higher; unfavorable new evidence can lower them.
2. Improve source-linked **cohort-scoped** features before using geography to
   prioritize trials: pair gene + exact allele + disease within the same cohort,
   preserve AND/OR clauses, and do not allow broad titles to override restrictions.
3. Add explicit MET exon 14, MSI/dMMR and loss-event handling with positive and
   negative fixtures. Unknown applicability must not become positive compatibility.
4. Re-test recall on independently reviewed cases rather than optimizing just
   these seven model-derived references. Audit a sample of newly selected trials.
5. Only then validate sequential expert review/replacement within the total
   call budget. Report promising unreviewed candidates honestly when that budget
   is exhausted; the present offline experiment does not validate this outcome.

No live-app files, PDFs, registry records or expert assessments were changed.
