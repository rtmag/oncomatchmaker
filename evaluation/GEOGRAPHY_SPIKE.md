# Recruiting-site proximity spike

This module ranks geographic proximity only after molecular matching supplies a
patient-specific list of candidate trial identifiers. It never searches all
nearby trials and therefore cannot promote an irrelevant study merely because it
is close to the patient.

Two independent status gates are mandatory:

```text
study overall status = RECRUITING
site status          = RECRUITING
```

A recruiting study with a closed, suspended, withdrawn, not-yet-recruiting, or
missing-status site will not present that site as open. Exact duplicate site rows
are collapsed in the ranked output without modifying the preserved registry
record.

Run the four offline city scenarios against the local snapshot:

```bash
python3 evaluation/run_geography_spike.py \
  data/snapshots/2026-09-13-v1/oncology.sqlite
```

The current test inputs are Singapore, Sydney, New York, and Paris. Their
coordinates are test fixtures standing in for a future geocoder connected to the
city textbox. The module does not persist patient input.

## Snapshot result

Using the 2026-09-13 snapshot and profile-specific trial candidate lists:

| Scenario | Nearest explicitly recruiting site |
|---|---|
| EGFR L858R NSCLC from Singapore | NCT06641609, Zhejiang Cancer Hospital, Hangzhou — 3,651.0 km |
| BRCA2-loss prostate cancer from Sydney | NCT06952803, St Leonards — 5.1 km |
| MET exon 14 NSCLC from New York | NCT06031688 and NCT07619339, New York — approximately 0.2 km |
| MSI-high metastatic colon cancer from Paris | NCT05310643, Hôpital Saint Antoine — 0.4 km |

The Paris scenario also contains NCT07807800 in its molecular candidate list, but
that study was `NOT_YET_RECRUITING`; it produced no open-site result. Synthetic
tests likewise confirm that a closed site is excluded even when its overall study
is recruiting.

Distances use the Haversine great-circle formula. They are approximate geographic
distance, not driving distance, travel time, or proof that a patient can enroll.
ClinicalTrials.gov coordinates may represent a city rather than a precise
facility entrance. Registry status must still be reconfirmed with the trial site
before presenting an enrollment opportunity.
