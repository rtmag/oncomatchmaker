"""Conservative NCIt normalization from a source-backed, bounded synonym snapshot."""

import json
import re
import unicodedata
from pathlib import Path


def normalized_key(value):
    return re.sub(
        r"[^a-z0-9]+", " ", unicodedata.normalize("NFKC", value).lower()
    ).strip()


class DiseaseRegistry:
    def __init__(self, records=None):
        if records is None:
            records = json.loads(
                (Path(__file__).with_name("resources") / "ncit.json").read_text()
            )["records"]
        self.records = records

    def resolve(self, raw):
        key = normalized_key(raw)
        # Prefer an exact preferred label over potentially overloaded synonyms.
        exact = [r for r in self.records if normalized_key(r["label"]) == key]
        candidates = exact or [
            r for r in self.records if key in {normalized_key(s) for s in r["synonyms"]}
        ]
        unique = {r["id"]: r for r in candidates}
        if len(unique) == 1:
            record = next(iter(unique.values()))
            return {
                "normalized": record["label"],
                "ontology_id": record["id"],
                "normalization_status": "exact_label" if exact else "exact_synonym",
            }
        # Do not strip stage/site qualifiers or infer a primary from a metastasis.
        return {
            "normalized": None,
            "ontology_id": None,
            "normalization_status": "ambiguous" if unique else "unmapped",
        }
