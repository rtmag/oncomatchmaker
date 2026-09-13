# Registry features and unified clinical scoring

## Building / updating

Run from the repository root after downloading or updating a registry snapshot:

```sh
.venv/bin/python -m trials.registry_features data/snapshots/2026-09-13-v1/oncology.sqlite
```

This creates `trial_features.sqlite` beside the snapshot. Source access is read-only;
the preserved JSON, eligibility text, locations and dates are not edited. The
companion database is a derived, ignored local artifact; regenerate it on another
machine rather than committing a large binary. Publish it with the snapshot
release only when the release workflow is explicitly requested.

Each feature row has an NCT ID, extractor version, generation timestamp and a
source-content fingerprint. Features include registry conditions, biomarker
mentions (gene/variant pairs, fusion/amplification event text), criterion lines
with inclusion/exclusion scope, cohort/prior-therapy/ECOG context, source-field
references, source URL and original registry update/retrieval/JSON-hash metadata.
The complete feature JSON remains available for audit. A compact scoring JSON
column keeps request-time loading fast. A changed feature file invalidates the
patient-independent in-memory cache. Source mismatches fail closed to unknown.

## Deliberately bounded interpretation

This first version is deterministic and conservative. It does **not** claim to
have semantically interpreted every registry criterion. A condition tag is not
proof of an accepted cohort. A biomarker mention is not automatically required,
accepted, excluded, or actionable. Negated, excluded and unscoped clauses do not
earn positive molecular credit. Explicit gene/variant pairs prevent attributing
one gene's allele to another gene in the same line. Complex multi-cohort logic,
prior-treatment exceptions, ECOG thresholds and staging remain source-linked
text for expert interpretation, not fabricated booleans.

Coverage is currently bounded to molecular and disease dimensions. Actionability
evidence, mechanism/resistance, individual eligibility and safety remain unknown
in the local estimator. No-match is not a proven exclusion. A mutation-targeted
title without an established patient molecular match is unscored rather than
given a high disease-only score. Unrecognized aliases, HGVS forms, broader
biomarker phenotypes and complex criteria require further extractor coverage and
evaluation. These limitations are intentional and must remain visible.

## Every new patient

Every report's freshly normalized profile is compared against all 26,423 studies.
No patient score is cached in the feature database. Existing broad candidate
retrieval protects recall; among retrieved candidates, review allocation uses
clinical score × coverage first, then score and molecular retrieval evidence.
This avoids favoring a high score supported by just one weakly covered dimension.
The existing six independent ASTRA calls per selected trial still receive the
complete original registry records. There are no additional model calls for
feature preparation or provisional scoring.

## Score contract: clinical-fit-v2

Both provisional and new expert scores share weights: molecular 30, disease 15,
evidence 15, mechanism 15, eligibility 20, safety 5. The score is the weighted mean
over assessed dimensions, scaled to 100. Coverage is assessed weight / 100.
All-unknown or hard-conflict results have a null score. The former expert formula
used the full denominator even for unknown dimensions; v2 is explicitly versioned
and legacy results are not silently relabeled or plotted on the new scale.

Uncertainty bounds show the weighted score range if every unassessed dimension
were 0 or 1. These are **not statistical confidence intervals**. A 90 score at 15%
coverage is not equivalent evidence to a 90 score at 100% coverage. The scores
have not been empirically calibrated and are not probabilities of eligibility,
response, benefit or acceptance. No claim of best-trial superiority is justified.

Expert results replace the provisional scalar in the API landscape and in the
single plot; the provisional assessment remains separately preserved for audit.
Refusal/validation failure removes the provisional score for that attempted
review rather than silently falling back. Clinical hard conflicts remain null.
All/shortlist only filters the same points. Unscored studies are counted and
listed separately, never plotted as invented zeros. Geography is unchanged and
remains a separate axis. Current requests still wait for the existing expert
review phase; progressive result streaming is not implemented in this change.

## Local checks

- Built 26,423 companion records from the local snapshot.
- Compact feature load: ~0.52 s cold, ~0.0003 s cached on this laptop.
- Full-registry patient scoring (not PDF extraction, geography, JSON serialization
  or model review): cholangiocarcinoma/KRAS G12D ~4.36 s; NSCLC/EGFR L858R ~4.38 s;
  melanoma/BRAF V600E ~4.52 s. These are single-run observations, not an SLA.
- RMC-9805: provisional 80 with 45% coverage for the KRAS G12D test patient;
  unscored molecular applicability for EGFR/BRAF test patients. This is not an
  eligibility or treatment recommendation.
- Regression tests cover source immutability, stale fingerprints, distinct
  patient profiles, gene/allele cross-contamination, VUS, negative/unscoped
  clauses, fusions, amplifications, null scores, shared aggregation, expert
  replacement and fail-closed review behavior. Pipeline tests use stubbed
  experts; no fresh paid expert run is represented by these tests.

Next validation work: expand and manually audit cohort-level feature extraction,
calibrate provisional versus expert assessments on diverse held-out reports,
and measure retrieval recall rather than promising recommendations for everyone.
