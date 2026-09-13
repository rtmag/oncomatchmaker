# Demo benchmark and 12-report QA

Date: 2026-09-13

## Preserved baseline

The cold baseline measured all 12 local public reports. PyMuPDF block extraction
took 3.48 seconds, pdfplumber row reconstruction with glyph de-duplication took
156.83 seconds, the prior sequential dual reader took 218.17 seconds, and four
processes reduced that to 83.28 seconds (2.62x). Candidate retrieval for the four
recorded profiles took 11.00 seconds and returned 3,021 broad recall candidates.

The principal local bottleneck was pdfplumber. A native-only experiment changed
the complete extracted text for 8 of 12 reports, so native and dual output must not
be described as identical. The explicit `fast` mode is therefore a demo choice,
not a production-equivalence claim. The separate `safe` mode preserves the dual
view and glyph de-duplication. A linear ordering implementation produces text
identical to the legacy de-duplication on all 12 reports while reducing the
safe-reader comparison pass from 215.83 to 47.60 seconds (4.53x in that run).

## Fast-reader QA matrix

All developer-reviewed source landmarks were present in fast mode. This validates
source availability, not model extraction accuracy or complete clinical results.

| Filename | Pages | Fast seconds | Landmarks | Profile | Trial result | Manual review | Blocker / safety concern |
|---|---:|---:|---|---|---|---|---|
| 01_FMI_F1LCDx_cholangiocarcinoma.pdf | 17 | 0.551 | Pass | Not yet evaluated | Not yet evaluated | Source landmarks reviewed | Low ctDNA fraction; KRAS/TP53 detected; FGFR2/IDH1 are assay-list entries |
| 02_FMI_F1LCDx_lung_high_TF.pdf | 2 | 0.071 | Pass | Not yet evaluated | Not yet evaluated | Source landmarks reviewed | File is a 2-page excerpt of a printed 22-page report |
| 03_FMI_F1LCDx_stomach_TF_CBD.pdf | 13 | 0.386 | Pass | Not yet evaluated | Not yet evaluated | Safety context reviewed | DNMT3A is in a possible-CH section and must not become a tumor target |
| 04_FMI_F1CDx_breast.pdf | 6 | 0.262 | Pass | Not yet evaluated | Not yet evaluated | Source landmarks reviewed | File is a 6-page excerpt of a printed 20-page report |
| 05_FMI_F1CDx_lung_EGFR.pdf | 37 | 1.292 | Pass | Recorded | Available | Pass | Missing stage, prior therapy, ECOG, labs, and confirmation stay unknown |
| 06_FMI_F1CDx_NSCLC_MET.pdf | 32 | 1.092 | Pass | Recorded | Available | Pass | Missing stage, other drivers, prior therapy, ECOG, and labs stay unknown |
| 07_FMI_F1CDx_prostate_BRCA2.pdf | 19 | 0.664 | Pass | Recorded | Available | Pass with cautions | Tumor BRCA2 loss does not establish germline status or zygosity |
| 10_Tempus_xT_lung.pdf | 11 | 0.321 | Pass | Not yet evaluated | Not yet evaluated | Safety context reviewed | Germline ATM and somatic ATM loss must remain distinct; assay-list/VUS genes are not targets |
| 11_Tempus_xF_metastatic_colon.pdf | 5 | 0.108 | Pass | Recorded | Available | Pass | Prior immunotherapy and confirmatory MSI/dMMR remain unknown |
| 12_Tempus_xF_negative.pdf | 4 | 0.110 | Pass | Safety fixture only | Not yet evaluated | Pass | No pathogenic target may be invented; unknown is not negative |
| 13_Caris_Assure_metastatic_lung.pdf | 9 | 0.247 | Pass | Not yet evaluated | Not yet evaluated | Safety context reviewed | DNMT3A/KDM6A CH findings must not become tumor targets |
| 14_Caris_endometrium_MMR_MSI.pdf | 19 | 0.425 | Pass | Not yet evaluated | Not yet evaluated | Safety context reviewed | MSI-stable/MMR-proficient must not become MSI-high/dMMR |

## Four golden-case manual review

The 12 cached trial assessments were checked against the complete local registry
records and report fixtures. Disease and biomarker relationships are supported for
the six direct candidates. Three explicit biomarker conflicts are unrankable. The
two prostate trials requiring germline status or confirmed BRCA2 zygosity are
labelled `needs_review`, not eligible. The upcoming MSI-high study has no geography
score because neither the study nor a site is yet recruiting.

Every result keeps eligibility `not_determined`; missing stage, prior therapy,
ECOG, laboratory, measurable-disease, and confirmatory-testing facts remain listed.
Clinical scores contain no site or distance inputs. Every displayed nearest site
has both study and site status `RECRUITING`. Source URLs and registry update dates
are present. Conflict trials may retain an independently computed access value in
the data, but they are not plotted and the demo UI suppresses their site display.

These are public-sample POC results, not medical advice, treatment recommendations,
or final eligibility determinations.
