"""ClinicalTrials.gov v2 adapter. Cache contains public responses only."""

from __future__ import annotations

import time
from copy import deepcopy
from datetime import datetime, timezone

import httpx


class TrialServiceError(RuntimeError):
    pass


class ClinicalTrialsClient:
    def __init__(self, http=None, max_pages=3, cache_seconds=900, sleep=time.sleep):
        self.http = http or httpx.Client(
            base_url="https://clinicaltrials.gov/api/v2", timeout=20
        )
        self.max_pages = max_pages
        self.cache_seconds = cache_seconds
        self.sleep = sleep
        self.cache = {}
        self.warnings = []

    def close(self):
        self.http.close()

    def _get(self, path, params=None):
        key = (path, tuple(sorted((params or {}).items())))
        if key in self.cache:
            saved, payload, retrieved = self.cache[key]
            if time.monotonic() - saved < self.cache_seconds:
                return deepcopy(payload), retrieved, True
        for attempt in range(3):
            try:
                response = self.http.get(path, params=params)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < 2:
                        self.sleep(0.5 * 2**attempt)
                        continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("Expected a JSON object")
                retrieved = datetime.now(timezone.utc).isoformat()
                self.cache[key] = (time.monotonic(), deepcopy(payload), retrieved)
                return payload, retrieved, False
            except httpx.TransportError as exc:
                if attempt < 2:
                    self.sleep(0.5 * 2**attempt)
                    continue
                raise TrialServiceError("Trial service connection failed") from exc
            except (httpx.HTTPStatusError, ValueError) as exc:
                raise TrialServiceError(
                    "Trial service returned an invalid or unsuccessful response"
                ) from exc
        raise TrialServiceError("Trial service retries exhausted")

    def search_trials(self, disease, term=""):
        params = {
            "query.cond": disease,
            "query.term": term,
            "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
            "pageSize": 100,
            "format": "json",
        }
        records, tokens = [], set()
        for page in range(self.max_pages):
            try:
                payload, retrieved, cached = self._get("/studies", params)
                studies = payload.get("studies")
                if not isinstance(studies, list) or any(
                    not isinstance(s, dict) for s in studies
                ):
                    raise TrialServiceError("Missing or malformed studies list")
            except TrialServiceError:
                if not records:
                    raise
                self.warnings.append(
                    "A later results page failed; results are incomplete."
                )
                break
            records.extend(
                {**s, "_retrieved_at": retrieved, "_cached": cached} for s in studies
            )
            token = payload.get("nextPageToken")
            if not token:
                break
            if not isinstance(token, str):
                self.warnings.append(
                    "Invalid pagination token; results are incomplete."
                )
                break
            if token in tokens or page == self.max_pages - 1:
                self.warnings.append(
                    "Search pagination limit reached; results are incomplete."
                )
                break
            tokens.add(token)
            params["pageToken"] = token
        return records

    def get_trial(self, nct_id):
        import re

        if not re.fullmatch(r"NCT\d{8}", nct_id):
            raise ValueError("Invalid NCT ID")
        data, retrieved, cached = self._get(f"/studies/{nct_id}")
        return {**data, "_retrieved_at": retrieved, "_cached": cached}
