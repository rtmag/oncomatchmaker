# Molecular-profile trial matching instructions

Evaluate only molecular and disease fit. Do not use trial locations and do not
make treatment recommendations or final eligibility determinations.

For every profile/trial pair:

1. Read inclusion and exclusion criteria separately. A biomarker mentioned only
   as an exclusion is a conflict, not a match.
2. Distinguish an exact alteration requirement from a gene-level or pathway-level
   relationship.
3. Do not treat a tumor finding as proof of a germline finding. Do not infer
   deletion zygosity, stage, prior treatment, performance status, measurable
   disease, laboratory values, or histology that the profile does not provide.
4. A compatible molecular profile can be a candidate even when clinical facts are
   missing, but the missing criteria must be listed and the result must remain a
   prescreening result.
5. Use `candidate` when disease and molecular requirements are compatible,
   `insufficient_biomarker_evidence` when the report does not establish the exact
   required biomarker, and `conflict` when a known report fact violates a criterion.
6. Cite the NCT identifier and registry source URL. Never imply that registry-wide
   recruiting status means a particular site is recruiting.

Return structured JSON only. Preserve unknowns rather than guessing.
