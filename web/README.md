# OncoMatchMaker web workspace

React + Vite + Tailwind v4 client for the OncoMatchMaker pipeline, built on the Astra Precision UI
design system (tokens, layout, and the Three.js molecular scene) with components adapted from
21st.dev (animated sidebar, stepper, file dropzone, score ring, number ticker, border beam,
animated tabs).

## Run

```sh
# Terminal 1 — API (from the repository root)
uvicorn app.api:app --reload

# Terminal 2 — UI with hot reload; /api is proxied to 127.0.0.1:8000
cd web
npm install
npm run dev
```

`npm run build` writes `web/dist`. When that folder exists, `uvicorn app.api:app` also serves the
built workspace at http://127.0.0.1:8000. Set `ONCO_API_URL` to proxy to a different API.

PDF extraction requires `OPENAI_API_KEY` in the environment or the project `.env`; the API returns a
clear 422 when it is missing.

## Layout

- `src/features/*` — one folder per workspace view (intake, overview, profile, therapies, trials,
  eligibility, locations) plus the shell and the molecular scene.
- `src/features/scene/molecular-scene.js` — the Astra Three.js controller, vendored with npm
  `three` imports. Geometry never encodes VAF, tumour burden, clonality or response probability.
- `src/components/ui/*` — design-system primitives; files adapted from 21st.dev name their source.
- `src/lib/*` — API client, types mirroring `schemas/`, formatting and status vocabularies.
- `src/state/case-store.tsx` — the single case store (profile, results, busy/error state).

The Streamlit app (`streamlit run app/main.py`) remains available as a fallback.
