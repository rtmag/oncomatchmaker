# Matching fixtures

`kras_nsclc.json`, `egfr_nsclc.json`, and `negative.json` are synthetic patient profiles, not extracted vendor reports.

`ctgov_recorded.json` is a public ClinicalTrials.gov v2 response retrieved on 2026-09-13 using condition NSCLC, term KRAS G12C, status RECRUITING, and pageSize 2. It is retained for reproducible parser tests, not used as current trial availability. Its pagination token is an archival artifact; tests do not follow it.

Handcrafted trial records in `conftest.py` are boundary-test data and are not displayed in the app.
