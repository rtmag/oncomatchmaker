# BioMCP clinical-trial access spike

## Purpose

This spike verifies that OncoMatchmaker can reach public clinical-trial data through BioMCP before the Track B client is designed. It does not implement matching, ranking, eligibility conclusions, geography scoring, or the application integration.

Tested on 2026-09-13 with BioMCP 0.8.25.

## Connection model

BioMCP runs as a local read-only MCP server over standard input/output:

```text
OncoMatchmaker or an agent
        ↓ MCP JSON-RPC over stdio
BioMCP (`biomcp serve`)
        ↓ HTTPS
ClinicalTrials.gov API v2
```

The default ClinicalTrials.gov backend does not require an API key. BioMCP also supports the oncology-focused NCI Clinical Trials Search API, but that optional backend requires `NCI_API_KEY`.

The MCP handshake negotiated protocol version `2025-03-26`. BioMCP exposed three MCP tools:

- `biomcp`: the complete command grammar, including filtered trial searches;
- `search`: a smaller typed search surface;
- `get`: typed retrieval for a known entity such as an NCT record.

See the official [BioMCP trial guide](https://biomcp.org/user-guide/trial/) and [data-source reference](https://github.com/genomoncology/biomcp/blob/main/docs/reference/data-sources.md).

## Live observations

The BioMCP health check reported both ClinicalTrials.gov and CIViC as available. No API key was needed for either check. NCI CTS was correctly reported as excluded because no NCI key was configured.

Three recruiting NSCLC mutation searches returned live ClinicalTrials.gov results:

| Search term | Reported total | First page requested |
|---|---:|---:|
| KRAS G12C | 66 | 5 |
| EGFR L858R | 10 | 5 |
| MET exon 14 | 37 | 5 |

These totals are transient observations, not fixtures or clinical claims. They will change as registry records change.

Retrieving `NCT05920356` through the typed `get` tool returned:

- recruitment status and phase;
- conditions and interventions;
- registry eligibility text and structured age/sex fields;
- central contact information;
- recruiting locations with coordinates;
- pagination metadata for additional locations;
- a ClinicalTrials.gov evidence URL and per-section provenance.

## Important finding

BioMCP documents mutation filtering as discovery-oriented free-text search. The KRAS G12C search returned broad NSCLC candidates whose summary rows did not all demonstrate a KRAS G12C requirement.

Therefore, OncoMatchmaker must not interpret a search result as a molecular match. The eventual Track B pipeline must retrieve full trial records and independently verify that the biomarker appears as an inclusion requirement or relevant cohort criterion. Exclusion-only mentions and absent molecular criteria must not produce a positive match.

## Reproduce the smoke test

Install BioMCP outside the project environment so the spike does not add an application dependency:

```bash
python3 -m venv /tmp/oncomatchmaker-biomcp
/tmp/oncomatchmaker-biomcp/bin/python -m pip install biomcp-cli==0.8.25
```

Run the opt-in live tests:

```bash
RUN_BIOMCP_LIVE=1 \
BIOMCP_BIN=/tmp/oncomatchmaker-biomcp/bin/biomcp \
python3 tests/test_biomcp_connectivity.py
```

The test creates a temporary writable BioMCP cache directory. Normal test runs skip these checks because they require a local BioMCP executable, network access, and live upstream services.

## Recommended handoff for Track B

Before building `trials/biomcp_client.py`, Roberto and Abhishek should agree on:

1. whether the application will use a long-running MCP process or an HTTP sidecar;
2. timeout, retry, pagination, and rate-limit behavior;
3. the exact mapping from BioMCP output into the shared `TrialCandidate` schema;
4. deterministic molecular-criteria verification after broad discovery;
5. provenance fields that must be retained for every result.

This spike deliberately stops before those architectural decisions.
