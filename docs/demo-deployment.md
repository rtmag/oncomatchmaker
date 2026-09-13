# Hackathon demo deployment

The presentation-safe app is cached-first and does not contact ClinicalTrials.gov,
BioMCP, or a geocoder:

```bash
streamlit run app/demo.py
```

The checked-in public-sample fixtures currently retain a visible legacy warning.
They must not be described as genuine multi-agent results until regenerated with
the six-call Astra implementation.

Configure the API key only in the deployment platform's server-side secret
manager as `OPENAI_API_KEY`. Do not add a `.env` file to git and never expose the
key in browser JavaScript. Then generate genuine cached Astra results:

```bash
python evaluation/generate_astra_demo_fixtures.py \
  data/snapshots/2026-09-13-v1/oncology.sqlite \
  evaluation/demo_fixtures
```

The generator makes six isolated concurrent Responses API calls per trial using
`gpt-6-astra` with medium reasoning, validates every response, records provenance,
and writes a fixture only after the complete team and deterministic consensus
succeed. The UI also offers a live six-agent run for the top candidate in each
golden report when the server key is present.

Sol remains exclusive to live PDF extraction. Both model paths use `store: false`,
strict structured output, sanitized errors, and server-side credentials.

## Current React workspace on Render

The repository root `Dockerfile` builds the React frontend and serves it with the
FastAPI backend as one web service. At startup it downloads and verifies the
released oncology SQLite snapshot, builds `trial_features.sqlite`, then starts
Uvicorn on the platform-provided `PORT`. The feature build is required for
preliminary clinical scores on fresh deployments.

1. Connect `rtmag/oncomatchmaker`, branch `main`, in Render and create a Blueprint
   using the checked-in `render.yaml` (or a Docker web service from the root).
2. Set `OPENAI_API_KEY` in Render's secret environment settings. The local `.env`
   is ignored and is not deployed. The key must have access to both model names
   configured in `render.yaml`.
3. Deploy and verify `/api/health`, the intake page and city search. Run a report
   through extraction, profile review and trial matching to verify model access.
4. Add your purchased `.site` domain under the service's Custom Domains settings,
   then add the DNS records Render supplies at your domain registrar. Render
   provisions HTTPS after domain verification.

A `.site` name is a domain, not a Python hosting service. A static-only host cannot
run this app's extraction and trial-matching endpoints. Render supports the
existing Docker runtime and custom domains:
https://render.com/docs/docker and https://render.com/docs/custom-domains.

The current deployment uses ephemeral storage and restores the registry at
startup when missing. An optional persistent disk mounted at `/app/data/snapshots`
can retain the snapshot across deployments. Do not mount over `/app` itself.
Report files are temporary; extracted profiles are cached in process memory.
The API currently has no application authentication or request rate limiting;
use restricted access for a hosted demonstration with a shared model API key.

The optional MSI/ECOG/context review and linked clinical-distance explorer run
against live API results. Map outlines are served locally and need no map API key.
The clinical score remains a prototype weighted heuristic, not a validated
clinical benefit or eligibility probability.
