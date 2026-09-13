# Oncology registry snapshots

GitHub Releases distribute versioned databases; the service downloads and queries SQLite locally. This implements the agreed snapshot storage workflow. The original project specifications are preserved.

## Build and verify

Python 3.8+ standard library only:

```sh
python3 -m unittest discover -s tests -p 'test_trial_snapshot.py'
python3 evaluation/build_trial_snapshot.py data/snapshots/YYYY-MM-DD
```

Use a new output directory. Failed builds remain unpublished and have no completed manifest. The builder downloads full ClinicalTrials.gov API v2 records with no field projection, traverses all study pages, deduplicates by the NCT primary key (duplicates fail the build), and verifies counts and registry version stability. Every original HTTP JSON response is retained byte-for-byte in registry-pages/*.json.gz. SQLite also contains semantically identical per-study JSON, including unfamiliar/future fields, alongside indexed study and site tables. Original formatting is preserved in the response archive, not the reserialized SQLite JSON.

Manifest metadata includes query, source URLs, page retrieval times, registry data timestamp, counts, coverage audits, response hashes and the SQLite hash. Each study stores its own retrieval timestamp and registry update/verification dates. Locations inherit the record's retrieval date, never its recruitment status. There is no separate site last-update timestamp supplied here; do not invent one.

## Coverage

The population is worldwide RECRUITING and NOT_YET_RECRUITING records returned by the broad condition query documented in the builder and manifest. It combines neoplasm terminology with explicit blood cancers, rare tumors and related hematologic conditions. Registry condition/MeSH expansion contributes coverage. Adult/pediatric, observational, prevention and supportive-care records are retained, as are benign-neoplasm false positives. This is an oncology candidate dataset, not a list of treatment recommendations.

Independent leukemia, lymphoma, myeloma, myelodysplastic and myeloproliferative queries are checked for missing NCT IDs before publication. These checks do not prove that every oncology study is captured. Trials absent from ClinicalTrials.gov or not indexed under these terms can be missed; classification and coverage review remain necessary. Include counts in every release.

## Site safety contract

Use the recruiting_sites view for candidate nearby recruiting locations: both overall_status and site.status must equal RECRUITING. Missing statuses stay NULL. Closed sites are retained but excluded. Study/site conflicts are excluded. Upcoming sites have their own view and must be labeled as upcoming, never currently available. Missing coordinates must not be fabricated or assigned zero distance.

The view expresses registry-reported availability, not confirmed enrollment capacity. Refresh shortlisted records before displaying actionable site suggestions, show registry update and retrieval dates, and route unknown site availability for confirmation. Fetching today does not mean the sponsor verified today.

All locations from the full registry response are inserted; there is no BioMCP location cap. Site ordinal identifies a location within a snapshot only and must not be treated as a stable site ID across updates.

## Distribution and consumption

Publish a compressed SQLite asset plus compressed original responses and a small release manifest with SHA-256 and sizes. Keep generated data out of Git commits. Private GitHub release downloads require service credentials with repository read access; keep credentials on the server, never in a browser or the database.

The service should download an explicit release version into a temporary path, verify the published SHA-256, decompress it, verify the database hash and PRAGMA integrity_check, and open it read-only. Switch the local active version atomically only after validation. Preserve the previous good version on download, decompression or validation failure. Production download/activation code is a later integration task.

For contributor access, with the GitHub CLI already authenticated:

```sh
gh release download oncology-snapshot-2026-09-13-v1 --repo rtmag/oncomatchmaker --dir /tmp/oncomatchmaker-snapshot
```

The release includes `oncology.sqlite.gz`, `registry-pages.tar.gz`, `manifest.json`, and `release-manifest.json`. Verify the compressed database hash against release-manifest.json, decompress it, and verify the uncompressed hash against manifest.json before use. The raw response archive is for provenance and reproducibility; the service only needs SQLite and the manifests. A GitHub Release is file distribution, not a database server. Initial snapshots are prereleases pending collaborator review.

Full rebuilds replace the active dataset, so trials that stop recruiting disappear from current suggestions while previous releases retain history. No scheduled job is configured by this change. Proposed operations: weekday/weekly refresh plus monthly reconciliation; immutable snapshots support repeatable evaluation. Preserve snapshot IDs with results and invalidate derived eligibility data when source hashes change.

Source: https://clinicaltrials.gov/data-about-studies/learn-about-api
