# Patient-result extraction optimization

The interactive fast extractor now selects original patient-result text locally
before calling Sol. Recognized Foundation drug monographs retain their patient
association sidebar; educational narrative columns, explicit trial-list pages and
reference pages are omitted. Unknown layouts and amended reports retain full text.
No PDF is modified. Grounding always uses the full original document, never the
filtered packet. Page and block omissions are recorded in ingestion provenance.

Recognized, separate Foundation VUS appendices are extracted concurrently with
the main result packet. Their findings must retain VUS classification and category.
Both responses must complete and validate; either failure rejects the extraction.
There is no independent completeness audit in interactive fast mode.

## Live paired measurements

Measured on the same local sample PDFs with Sol, low reasoning and priority
processing, bypassing the application extraction cache. One run per configuration;
network and API latency vary. This is not a statistical performance benchmark.

| Report | Previous full-text path | Selected main + parallel VUS | Reduction |
| --- | ---: | ---: | ---: |
| 37-page EGFR lung report | 36.91 s | 27.39 s | 26% |
| 32-page MET lung report | 31.69 s | 17.80 s | 44% |

Selected-input sequential calls alone took 29.35 s and 37.55 s respectively,
demonstrating why input reduction alone does not guarantee faster generation.
The selected packets remove approximately 70–74% of input characters for these
two reports. The parallel mode makes two calls, with some duplicated instruction
and schema overhead, rather than one call.

The final runs retained EGFR L858R / A289V, MET exon-14 splice finding,
MSI stable and TMB 24 / 8 respectively. Two EGFR findings and five MET findings
were held by grounding validation. Findings vary between model runs; these checks
do not establish whole-report recall or equivalence with a reviewed clinical profile.

Local tests verify complete preservation of specified patient-result pages across
all 12 corpus PDFs, including VUS appendices, amended/original sequences, CH,
negative findings, indeterminate results and late sequencing/IHC pages. Unit tests
also cover immutable sources, unknown-layout fallback, mixed result/reference
pages, concurrent appendix calls and failure of either response.
