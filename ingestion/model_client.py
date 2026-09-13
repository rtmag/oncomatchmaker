"""Sol extraction via Responses API; all output validated and independently reviewed."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Protocol

import httpx
import pymupdf
from dotenv import load_dotenv
from pydantic import ValidationError

from schemas.extraction import ExtractedReport, ExtractionReview

PROMPT_VERSION = "ingestion-0.2.2"
PROMPTS = Path(__file__).with_name("prompts")


class ExtractionError(RuntimeError):
    pass


class Extractor(Protocol):
    model: str

    def extract(self, document, pdf_path=None) -> ExtractedReport: ...
    def review(self, document, extracted) -> ExtractionReview: ...


def strict_schema(model):
    schema = model.model_json_schema()

    def walk(node):
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(schema)
    return schema


class SolExtractor:
    def __init__(self, *, api_key=None, model=None, http=None, vision_pages=3):
        load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ExtractionError(
                "Set OPENAI_API_KEY in the environment or project .env to enable Sol PDF extraction."
            )
        self.model = model or os.environ.get(
            "ONCOMATCH_EXTRACTION_MODEL", "gpt-5.6-sol"
        )
        self.vision_pages = vision_pages
        self.owned = http is None
        self.http = http or httpx.Client(
            base_url="https://api.openai.com/v1",
            timeout=180,
            headers={"Authorization": f"Bearer {key}"},
        )

    def close(self):
        if self.owned:
            self.http.close()

    def _call(self, prompt, content, output_model):
        payload = {
            "model": self.model,
            "store": False,
            "reasoning": {"effort": "medium"},
            "max_output_tokens": 16000,
            "input": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": content},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": output_model.__name__,
                    "strict": True,
                    "schema": strict_schema(output_model),
                }
            },
        }
        try:
            response = self.http.post("/responses", json=payload)
            response.raise_for_status()
            result = response.json()
            if result.get("status") != "completed":
                raise ExtractionError(
                    "Model response incomplete; extraction not accepted. Retry or review the report."
                )
            text = []
            for item in result.get("output", []):
                if item.get("type") == "message":
                    for part in item.get("content", []):
                        if part.get("type") == "refusal":
                            raise ExtractionError(
                                "Model declined extraction; no profile was generated."
                            )
                        if part.get("type") == "output_text":
                            text.append(part["text"])
            return output_model.model_validate_json("".join(text))
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            ValidationError,
        ) as exc:
            # Never expose API keys, report payloads or API error bodies in UI errors.
            raise ExtractionError(
                "Sol request failed or returned invalid structured data; no profile was accepted."
            ) from exc

    def extract(self, document, pdf_path=None):
        if len(document.text) > 600_000:
            raise ExtractionError(
                "Report exceeds the extraction text limit; split and review it explicitly."
            )
        content = [{"type": "input_text", "text": document.text}]
        if pdf_path and self.vision_pages:
            with pymupdf.open(pdf_path) as pdf:
                for page in list(pdf)[: self.vision_pages]:
                    image = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5))
                    encoded = base64.b64encode(image.tobytes("png")).decode()
                    content.extend(
                        [
                            {
                                "type": "input_text",
                                "text": f"Layout image for page {page.number + 1}",
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:image/png;base64,{encoded}",
                                "detail": "high",
                            },
                        ]
                    )
        return self._call(
            (PROMPTS / "extract.txt").read_text(), content, ExtractedReport
        )

    def review(self, document, extracted):
        content = [
            {
                "type": "input_text",
                "text": document.text
                + "\n\nPROPOSED EXTRACTION (untrusted):\n"
                + extracted.model_dump_json(),
            }
        ]
        return self._call(
            (PROMPTS / "review-v2.txt").read_text(), content, ExtractionReview
        )

    def repair(self, document, extracted, errors):
        prompt = (
            (PROMPTS / "extract.txt").read_text()
            + "\nCorrect the listed extraction/quote errors using the source text. Quotes must follow actual text order, not reconstructed visual row order. Choose short, exact alteration tokens, not combined annotations. Do not guess corrections to unknown genes. Preserve all source-supported findings and leave unresolved items for review. Return the full corrected extraction."
        )
        content = [
            {
                "type": "input_text",
                "text": document.text
                + "\nPROPOSAL:\n"
                + extracted.model_dump_json()
                + "\nVALIDATION ERRORS:\n"
                + str(errors),
            }
        ]
        return self._call(prompt, content, ExtractedReport)
