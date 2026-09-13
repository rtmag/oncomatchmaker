# Full-pipeline integration POC

Run date: 2026-09-13
Snapshot: `oncology-snapshot-2026-09-13-v1`

The integration run read three unchanged local public sample PDFs, validated
recorded molecular profiles from the earlier matching spike, loaded nine complete
registry records from SQLite, passed each through the frozen six-role ASTRA
contract and safety consensus, calculated a clinical composite with no geography,
then independently scored proximity to the nearest explicitly recruiting site.

| Case | Test city | PDF pages | Trials | Plottable | High match / high access |
|---|---|---:|---:|---:|---:|
| EGFR L858R lung | Singapore | 37 | 3 | 2 | 0 |
| MET exon 14 NSCLC | New York | 32 | 3 | 2 | 2 |
| MSI-high metastatic colon | Paris | 5 | 3 | 1 | 1 |

Five of nine trials were plottable. Three hard molecular conflicts were correctly
unrankable. One upcoming trial had no confirmed open site and therefore received
no geographic score. The New York MET candidates and Paris MSI-high candidate
landed in the high-clinical-match/high-access quadrant.

This is a reproducibility and interface test, not a clinical validation. Candidate
IDs and model reviews are recorded fixtures, not a fresh exhaustive search or six
new model calls. Eligibility remains undetermined. The detailed generated JSON is
kept outside git because it is a test artifact; rerun with:

```bash
python evaluation/run_full_pipeline_poc.py \
  data/snapshots/2026-09-13-v1/oncology.sqlite \
  --output /tmp/oncomatchmaker-full-pipeline-results.json
```
