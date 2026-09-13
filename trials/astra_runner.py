"""Six isolated, concurrent GPT-6 Astra expert calls with fail-closed validation."""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable, Mapping

import httpx
from dotenv import load_dotenv

from schemas.astra_contracts import EXPERT_ROLES, ExpertAssessment
from trials.astra_team import build_expert_packets, reach_consensus

MODEL = "gpt-6-astra"
REASONING_EFFORT = "medium"
PROMPT_VERSION = "astra-expert-0.2-basket-context"


class ExpertTeamError(RuntimeError):
    """Raised when a complete, validated six-expert result is unavailable."""


def expert_assessment_schema() -> dict[str, Any]:
    string_array = {"type": "array", "items": {"type": "string"}}
    properties = {
        "trial_id": {"type": "string", "pattern": "^NCT[0-9]{8}$"},
        "expert_role": {"type": "string", "enum": list(EXPERT_ROLES)},
        "assessment": {
            "type": "string",
            "enum": ["support", "caution", "conflict", "unknown"],
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "relationships": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "direct_variant",
                    "gene_level",
                    "phenotype_biomarker",
                    "pathway_mechanism",
                    "resistance_strategy",
                    "broad_basket",
                    "not_applicable",
                ],
            },
        },
        "supporting_facts": string_array,
        "conflicting_facts": string_array,
        "missing_information": string_array,
        "evidence_references": string_array,
        "reasoning_summary": {"type": "string", "minLength": 1},
    }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


class AstraExpertRunner:
    def __init__(self, *, api_key=None, model=None, http=None):
        load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ExpertTeamError(
                "OPENAI_API_KEY is not configured; six-agent matching was not run."
            )
        self.model = model or os.environ.get("ONCOMATCH_ASTRA_MODEL", MODEL)
        self._owned = http is None
        self._http = http or httpx.Client(
            base_url="https://api.openai.com/v1",
            timeout=180,
            headers={"Authorization": f"Bearer {key}"},
        )

    def close(self):
        if self._owned:
            self._http.close()

    def _call(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        role = packet["expert_role"]
        trial_id = packet["trial"]["nct_id"]
        allowed_references = {
            packet["trial"].get("source_url"),
            trial_id,
            packet["profile"].get("case_id"),
            packet["profile"].get("source_pdf"),
        }
        allowed_references.update(
            reference
            for evidence in packet.get("evidence", [])
            for key in ("source_url", "url", "reference")
            if (reference := evidence.get(key))
        )
        allowed_references = {
            reference for reference in allowed_references if reference
        }
        schema = expert_assessment_schema()
        schema["properties"]["evidence_references"]["items"]["enum"] = sorted(
            allowed_references
        )
        payload = {
            "model": self.model,
            "store": False,
            "reasoning": {"effort": REASONING_EFFORT},
            "max_output_tokens": 4000,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are one isolated ASTRA oncology trial-review expert. "
                        "Use only the supplied packet. Preserve unknowns, never determine "
                        "eligibility, select evidence references exactly from the allowed "
                        "source identifiers, and return only the requested structured assessment."
                    ),
                },
                {"role": "user", "content": json.dumps(packet)},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "ExpertAssessment",
                    "strict": True,
                    "schema": schema,
                }
            },
            "metadata": {
                "expert_role": role,
                "trial_id": trial_id,
                "prompt_version": PROMPT_VERSION,
            },
        }
        started = time.perf_counter()
        try:
            response = self._http.post("/responses", json=payload)
            response.raise_for_status()
            result = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ExpertTeamError(
                f"ASTRA expert {role} failed; no team result was accepted."
            ) from exc
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        if result.get("status") != "completed":
            raise ExpertTeamError(
                f"ASTRA expert {role} was incomplete; no team result was accepted."
            )
        output_text = []
        for item in result.get("output", []):
            if item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if part.get("type") == "refusal":
                    raise ExpertTeamError(
                        f"ASTRA expert {role} refused; no team result was accepted."
                    )
                if part.get("type") == "output_text":
                    output_text.append(part.get("text", ""))
        try:
            raw = json.loads("".join(output_text))
            assessment = ExpertAssessment.from_dict(raw)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ExpertTeamError(
                f"ASTRA expert {role} returned malformed output; no team result was accepted."
            ) from exc
        if assessment.expert_role != role or assessment.trial_id != trial_id:
            raise ExpertTeamError(
                f"ASTRA expert {role} returned mismatched identity; no team result was accepted."
            )
        if not assessment.evidence_references or any(
            reference not in allowed_references
            for reference in assessment.evidence_references
        ):
            raise ExpertTeamError(
                f"ASTRA expert {role} returned unsupported evidence references; no team result was accepted."
            )
        usage = result.get("usage") or {}
        raw["execution"] = {
            "model": result.get("model") or self.model,
            "reasoning_effort": REASONING_EFFORT,
            "prompt_version": PROMPT_VERSION,
            "latency_ms": latency_ms,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "status": "live",
            "response_id": result.get("id"),
        }
        return raw

    def run_team(
        self,
        profile: Mapping[str, Any],
        trial: Mapping[str, Any],
        evidence: Iterable[Mapping[str, Any]],
    ) -> dict[str, Any]:
        packets = build_expert_packets(profile, trial, evidence)
        completed = {}
        with ThreadPoolExecutor(max_workers=len(EXPERT_ROLES)) as pool:
            futures = {
                pool.submit(self._call, packet): packet["expert_role"]
                for packet in packets
            }
            try:
                for future in as_completed(futures):
                    assessment = future.result()
                    completed[assessment["expert_role"]] = assessment
            except Exception:
                for future in futures:
                    future.cancel()
                raise
        if set(completed) != set(EXPERT_ROLES):
            raise ExpertTeamError("The complete six-agent team did not return.")
        assessments = [completed[role] for role in EXPERT_ROLES]
        return {
            "model": self.model,
            "reasoning_effort": REASONING_EFFORT,
            "prompt_version": PROMPT_VERSION,
            "execution": "concurrent_isolated_responses",
            "assessments": assessments,
            "consensus": reach_consensus(assessments),
        }
