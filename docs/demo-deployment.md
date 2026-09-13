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
