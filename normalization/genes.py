"""Deterministic HGNC lookup. Never fuzzy-correct an unknown gene symbol."""

from __future__ import annotations

import gzip
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field

from schemas.molecular_profile import Model

SNAPSHOT = Path(__file__).with_name("resources") / "hgnc.json.gz"


class GeneResolution(Model):
    raw: str
    status: Literal["approved", "alias", "previous", "ambiguous", "unknown"]
    symbol: str | None = None
    hgnc_id: str | None = None
    candidates: list[str] = Field(default_factory=list)


class HGNCRegistry:
    def __init__(self, records, metadata=None):
        self.metadata = metadata or {}
        self.approved = {}
        self.aliases = defaultdict(set)
        self.previous = defaultdict(set)
        for record in records:
            if record.get("status") != "Approved":
                continue
            symbol = record["symbol"]
            self.approved[symbol.upper()] = record
            for term in record.get("alias_symbol", []):
                self.aliases[term.upper()].add(symbol)
            for term in record.get("prev_symbol", []):
                self.previous[term.upper()].add(symbol)
        if not self.approved:
            raise ValueError("HGNC registry contains no approved genes")

    @classmethod
    def load(cls, path=SNAPSHOT):
        with gzip.open(path, "rt") as handle:
            data = json.load(handle)
        return cls(data["records"], data["metadata"])

    def resolve(self, value: str) -> GeneResolution:
        key = value.strip().upper()
        if key in self.approved:
            record = self.approved[key]
            return GeneResolution(
                raw=value,
                status="approved",
                symbol=record["symbol"],
                hgnc_id=record["hgnc_id"],
            )
        candidates = self.aliases[key] | self.previous[key]
        if len(candidates) == 1:
            symbol = next(iter(candidates))
            return GeneResolution(
                raw=value,
                status="previous" if symbol in self.previous[key] else "alias",
                symbol=symbol,
                hgnc_id=self.approved[symbol.upper()]["hgnc_id"],
            )
        return GeneResolution(
            raw=value,
            status="ambiguous" if candidates else "unknown",
            candidates=sorted(candidates),
        )


@lru_cache(maxsize=1)
def get_registry():
    return HGNCRegistry.load()
