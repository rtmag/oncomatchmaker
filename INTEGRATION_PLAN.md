# OncoMatchmaker full-pipeline integration plan

## Integration principles

1. The PDF-ingestion pipeline ends at a versioned canonical molecular profile.
2. Trial discovery uses the complete local ClinicalTrials.gov snapshot, not a
   page-limited live keyword search.
3. Model experts reason only over supplied profile, registry, and evidence data.
4. Molecular, disease, eligibility, and safety conflicts are deterministic gates.
5. Clinical match and geographic access are independent outputs.
6. Every conclusion retains evidence, registry dates, model/prompt versions,
   uncertainty, and missing information.
7. Approved therapy evidence remains separate from experimental trials.

## Pipeline and interfaces

```text
parse_report(pdf) -> MolecularProfile
validate/profile-QC -> ProfileReview
retrieve_candidates(profile, snapshot) -> CandidateTrial[]
assemble_evidence(profile, candidate) -> EvidenceBundle
run_expert_team(profile, candidate, evidence) -> ExpertAssessment[]
reach_consensus(assessments) -> ConsensusResult
clinical_trial_score(dimensions) -> ClinicalTrialScore
nearest_recruiting_sites(candidate_ids, patient_location) -> RecruitingSite[]
geographic_access_score(nearest_open_site) -> GeographyScore
trial_plot_position(clinical, geography) -> TrialPlotPosition
assemble_report(...) -> MatchReport
```

Candidate retrieval may be broad, but only trials surviving expert and hard-gate
review become ranked candidates. Geography runs after molecular/clinical review
and can never rescue a biologically unsuitable trial.

## Canonical-profile reconciliation

Abhishek's profile schema is the starting implementation. Before integration it
should add or explicitly derive:

- the originally reported gene token and canonical HGNC symbol,
- gene and disease retrieval synonyms,
- structured detected, negative, VUS, germline, and CH categories,
- copy-number zygosity when reported and explicit unknown otherwise,
- structured assay limitations and finding-level review state,
- provenance for every normalized value.

The current ingestion revision must be rerun over all 12 local reports. Saved
audits remain local and ignored; aggregate, non-identifying evaluation results can
be committed.

## Score architecture

The clinical composite contains molecular fit, disease fit, mechanistic fit,
evidence strength, eligibility compatibility, and trial-design relevance. It
contains no distance, country, site, or recruitment bonus.

Recruitment is a gate: geography is calculated only from a site where both the
study and site are explicitly `RECRUITING`. Geographic access is then scored from
the nearest open site independently from the clinical composite.

The future 2D plot uses:

- x-axis: conservative clinical composite,
- y-axis: geographic-access score,
- color: direct, mechanistic, exploratory, or eligibility-review tier,
- size: evidence coverage or confidence.

Unresolved clinical conflicts, inadequate clinical coverage, no confirmed open
site, or unknown distance keep a trial off the plot and place it in an explicitly
labeled review list.

## Report-ready result

The frozen `schemas/integrated_results.py` v0.1 result includes:

- source report and extraction provenance,
- normalized disease and molecular profile,
- finding-by-finding biological interpretation,
- approved therapy evidence in a separate section,
- ranked experimental trial candidates,
- all clinical component scores and rationales,
- independent geographic score and nearest/alternative open sites,
- the 2D plot coordinates and quadrant,
- known eligibility conflicts and missing facts,
- questions for the oncologist and trial coordinator,
- registry/evidence retrieval dates and source URLs,
- safety limitations and confidence/coverage indicators.

Actionable insights are verification or discussion steps, not autonomous treatment
or enrollment instructions.

## GitHub integration order

1. Merge the snapshot foundation (PR #2).
2. Split or revise PR #5 so the source-grounded ingestion implementation is
   separate from its earlier trial, ranking, geography, evidence, and UI prototype.
3. Rebase and merge the molecular matching evaluation (PR #3).
4. Rebase and merge the ASTRA expert contracts (PR #4).
5. Rebase and merge recruiting-site geography (PR #6).
6. Merge this independent clinical/geographic scorecard contract.
7. Create `integration/full-pipeline-poc` from the updated `main` branch.
8. Add adapters rather than duplicating profile, trial, or geography models.
9. Run end-to-end EGFR, MET, BRCA2, MSI-high, and negative-report scenarios.
10. Freeze the report-result schema before implementing final UI or report export. (Done on the integration branch.)

## Integration POC boundary

`evaluation/run_full_pipeline_poc.py` reads each selected public PDF locally,
records its byte hash and page count, validates its recorded molecular profile,
loads complete trial records from the local snapshot, enforces the six-expert
contract and deterministic consensus gates, computes the clinical score, then
finds only explicitly recruiting sites and computes the independent geography
axis. The emitted JSON validates against result schema v0.1.

The current run uses profiles and expert reviews recorded during the earlier
public-sample POC because no API credential is supplied to the integration job.
It therefore proves the local pipeline and contracts, not fresh model inference
or exhaustive candidate retrieval. The output labels this limitation directly.

## Sign-off gates

- Current ingestion revision evaluated on all 12 reports.
- No invalid or ambiguous gene is silently promoted.
- Exact, gene-level, mechanistic, and basket relationships remain distinguishable.
- Explicit inclusion/exclusion conflicts always win over model support.
- Unknown patient facts remain unknown.
- Only explicitly recruiting sites receive a geography score.
- Geography never changes the clinical composite.
- Every score exposes rationale, confidence, coverage, and sources.
- The four-quadrant position is reproducible from the structured JSON.
- Public sample reports only until a real-patient privacy pathway is approved.
