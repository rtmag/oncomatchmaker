# Basket-trial retrieval regression

The original local filter required a named disease text hit. This could discard
solid-tumor basket trials before ASTRA reviewed their actual cohort criteria.

The revised screen permits molecularly relevant solid-tumor basket text for a
recognizable solid-tumor diagnosis, and prioritizes explicit protein substitution
mentions outside the labeled exclusion section. This remains a retrieval
heuristic, not an eligibility decision. Broad titles can coexist with restricted
cohorts; all shortlisted trials still require six independent expert assessments
and unchanged deterministic hard-conflict gates. Unknown diagnoses and blood
cancers are not assumed to be solid tumors. This is not a complete ontology or
semantic eligibility parser; spelling variants and unlabeled exclusions still
need expert review and future retrieval evaluation.

Cross-disease variant text leads are returned separately (up to 12 displayed),
without clinical/geography scores or a claim of expert review. Their tumor-type
compatibility is unconfirmed. The full preliminary landscape still represents
all snapshot studies, not confirmed matches. Explicit disease-context conflicts
are flagged on reviewed cards; their null-score exclusion behavior is unchanged.

Expanded-access true/false/missing values, registry update date, retrieval time,
and registry links are preserved. Expanded access is not a waiver of enrollment
criteria and is never inferred from a mutation match. See
[FDA patient guidance](https://www.fda.gov/news-events/expanded-access/expanded-access-information-patients).

## Checks

- Synthetic cholangiocarcinoma/KRAS G12D profile, local snapshot 2026-09-13-v1:
  26,423 studies screened in approximately 2.9 seconds, 181 retrieval candidates,
  22 separate exploratory leads. These counts are not eligibility counts.
- [NCT06040541](https://clinicaltrials.gov/study/NCT06040541), the RMC-9805 solid-tumor
  study, enters the expert-review pool at position 3 for that test profile.
- Regression cases cover basket retrieval, pancreatic-only leads, G12C versus
  G12D prioritization, labeled exclusions, inactive studies, unknown diagnoses,
  hematologic diagnoses, VUS, and expanded-access true/false/missing values.
- Snapshot pipeline test verifies JSON roundtrip and unscored exploratory
  separation using explicitly stubbed expert responses. It is not a live expert
  review or an extraction test of the original PDF.
- Expert prompt provenance advances to `astra-expert-0.2-basket-context`.
  Old demo fixtures are unchanged and must not be represented as new reviews.

Restart the local backend and run a new search to obtain the new fields;
previously loaded results do not retroactively change.
