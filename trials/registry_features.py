"""Patient-independent, source-linked features in a companion SQLite database.

Run at snapshot preparation time: python -m trials.registry_features SNAPSHOT.
No registry record is edited. Clause mentions are NOT interpreted as eligibility.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from trials.cohort_matching import DISEASES, SOLID

VERSION = "registry-features-v2"


def fingerprint(title, eligibility, conditions, status):
    return hashlib.sha256(
        json.dumps(
            [title, eligibility, conditions, status], ensure_ascii=False
        ).encode()
    ).hexdigest()


def extract_features(title, eligibility, conditions, status):
    clauses = []
    section = "unscoped"
    cohort_context = ""
    # Keep original lines, positions and surrounding cohort wording for review.
    for offset, line in enumerate((eligibility or "").splitlines()):
        if re.search(r"exclusion(?:\s+criteria)?\s*:", line, re.I) or re.search(
            r"exclusion\s+criteria", line, re.I
        ):
            section = "exclusion"
            cohort_context = ""
        elif re.search(r"inclusion(?:\s+criteria)?\s*:", line, re.I) or re.search(
            r"inclusion\s+criteria", line, re.I
        ):
            section = "inclusion"
            cohort_context = ""
        if re.search(r"\b(?:cohort|arm|subprotocol|group)\s+[A-Z0-9]+", line, re.I):
            cohort_context = line if line.rstrip().endswith(":") else ""
        if line.strip():
            clauses.append(
                {
                    "text": line,
                    "section": "inclusion"
                    if section == "unscoped"
                    and re.search(
                        r"\b(?:patients?|participants?|subjects?)\s+must have\b",
                        line,
                        re.I,
                    )
                    else section,
                    "source_field": "eligibility_text",
                    "line": offset + 1,
                    "cohort_context": cohort_context,
                }
            )
    sources = [
        {"text": title or "", "section": "title", "source_field": "title"},
        *clauses,
    ]
    # Uppercase tokens are lexical index keys, not asserted HGNC gene identities.
    tokens = sorted(
        set(
            re.findall(
                r"\b[A-Z][A-Z0-9-]{1,20}\b", " ".join(s["text"] for s in sources)
            )
        )
    )
    biomarkers = []
    sentence_sources = [
        {
            **source,
            "text": sentence,
            "sentence_index": index,
            "source_line_text": source["text"],
        }
        for source in sources
        for index, sentence in enumerate(
            [source["text"]]
            if source["section"] == "title"
            else re.split(r"(?<=[.!?])\s+(?=[A-Z])", source["text"])
        )
    ]
    for source in sentence_sources:
        variants = re.findall(
            r"(?<![A-Za-z0-9])(?:p\.)?([A-Z]\d+[A-Z])(?![A-Za-z0-9])", source["text"]
        )
        events = re.findall(
            r"fusion|amplification|\bloss\b|deletion|exon[ -]+\d+[ -]+skipping|MSI[ -]high|MSI-H|dMMR|\bMSS\b|\bpMMR\b|microsatellite|mismatch repair",
            source["text"],
            re.I,
        )
        if (
            variants
            or events
            or re.search(r"mutant|mutation|alteration", source["text"], re.I)
        ):
            biomarkers.append(
                {
                    **source,
                    "variants": sorted(set(variants)),
                    "events": sorted(set(events)),
                    "gene_variant_pairs": re.findall(
                        r"\b([A-Z][A-Z0-9]{1,10})[\s:(-]+(?:p\.)?([A-Z]\d+[A-Z])\b",
                        source["text"],
                    ),
                    "interpretation": "mention_requires_cohort_review",
                }
            )
    positive = " ".join(
        s["text"] for s in sources if s["section"] in {"title", "inclusion"}
    )
    inclusion_context = " ".join(
        s["text"] for s in clauses if s["section"] == "inclusion"
    )
    # Precompute bounded disease vocabulary, not a new patient-specific match.
    explicit_disease_context = " ".join(
        match.group(0)
        for match in re.finditer(
            "|".join(DISEASES) + "|" + SOLID, inclusion_context, re.I
        )
    )
    return {
        "feature_version": VERSION,
        "status": status,
        "conditions": json.loads(conditions),
        "title": title or "",
        "lexical_tokens": tokens,
        "biomarker_mentions": biomarkers,
        "criteria": clauses,
        "inclusion_context": explicit_disease_context,
        "multiple_cohorts": len(
            set(
                re.findall(
                    r"\b(?:cohort|arm|subprotocol|group)\s+([A-Z0-9]+)\b",
                    eligibility or "",
                    re.I,
                )
            )
        )
        > 1,
        "broad_solid_mention": bool(
            re.search(r"\bsolid (?:tumou?rs?|malignanc\w*)\b", positive, re.I)
        ),
        "clinical_context_mentions": [
            s
            for s in clauses
            if re.search(
                r"ECOG|prior|previous|treatment.naive|metastatic|advanced|cohort|phase",
                s["text"],
                re.I,
            )
        ],
        "unknowns": [
            "Cohort applicability and logical combinations require review.",
            "No validated accepted/excluded biomarker assertions are inferred from mentions.",
            "No drug actionability, resistance, or treatment benefit is inferred.",
        ],
    }


def feature_path(snapshot):
    return Path(snapshot).with_name("trial_features.sqlite")


def build(snapshot, output=None):
    """Publish a complete companion atomically; active readers keep the old file."""
    snapshot = Path(snapshot).resolve()
    output = Path(output or feature_path(snapshot)).resolve()
    if output == snapshot:
        raise ValueError("Feature output must not overwrite the registry")
    fd, temporary = tempfile.mkstemp(
        prefix=".trial-features-", suffix=".sqlite", dir=output.parent
    )
    os.close(fd)
    try:
        result = _build(snapshot, temporary)
        os.replace(temporary, output)
        return {**result, "path": str(output)}
    finally:
        Path(temporary).unlink(missing_ok=True)


def _build(snapshot, output=None):
    snapshot = Path(snapshot).resolve()
    output = Path(output or feature_path(snapshot)).resolve()
    if output == snapshot:
        raise ValueError("Feature output must not overwrite the registry")
    now = datetime.now(timezone.utc).isoformat()
    with (
        sqlite3.connect(f"file:{snapshot}?mode=ro", uri=True) as source,
        sqlite3.connect(output) as dest,
    ):
        dest.execute(
            "CREATE TABLE IF NOT EXISTS trial_features(nct_id TEXT PRIMARY KEY, source_hash TEXT NOT NULL, feature_version TEXT NOT NULL, generated_at TEXT NOT NULL, features_json TEXT NOT NULL)"
        )
        if "scoring_json" not in {
            r[1] for r in dest.execute("PRAGMA table_info(trial_features)")
        }:
            dest.execute("ALTER TABLE trial_features ADD COLUMN scoring_json TEXT")
        columns = {r[1] for r in source.execute("PRAGMA table_info(studies)")}
        provenance_fields = [
            name
            for name in ("last_update_posted", "retrieved_at", "json_sha256")
            if name in columns
        ]
        provenance = {
            r[0]: dict(zip(provenance_fields, r[1:]))
            for r in source.execute(
                "SELECT nct_id"
                + ("," + ",".join(provenance_fields) if provenance_fields else "")
                + " FROM studies"
            )
        }
        count = 0
        for nct, title, eligibility, conditions, status in source.execute(
            "SELECT nct_id,title,eligibility_text,conditions_json,overall_status FROM studies"
        ):
            features = extract_features(title, eligibility, conditions, status)
            features["source_url"] = f"https://clinicaltrials.gov/study/{nct}"
            features["source_provenance"] = provenance[nct]
            scoring = {
                key: features[key]
                for key in (
                    "title",
                    "conditions",
                    "status",
                    "broad_solid_mention",
                    "lexical_tokens",
                    "biomarker_mentions",
                    "multiple_cohorts",
                    "inclusion_context",
                )
            }
            dest.execute(
                "INSERT OR REPLACE INTO trial_features VALUES(?,?,?,?,?,?)",
                (
                    nct,
                    fingerprint(title, eligibility, conditions, status),
                    VERSION,
                    now,
                    json.dumps(features, separators=(",", ":")),
                    json.dumps(scoring, separators=(",", ":")),
                ),
            )
            count += 1
        # Remove records absent from this snapshot without modifying the source.
        ids = {r[0] for r in source.execute("SELECT nct_id FROM studies")}
        dest.executemany(
            "DELETE FROM trial_features WHERE nct_id=?",
            [
                (r[0],)
                for r in dest.execute("SELECT nct_id FROM trial_features")
                if r[0] not in ids
            ],
        )
    return {"records": count, "feature_version": VERSION, "path": str(output)}


def load(snapshot):
    path = feature_path(snapshot)
    if not path.exists():
        return {}
    stat = path.stat()
    return _load(str(path.resolve()), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=1)
def _load(path, mtime_ns, size):
    """Cache only patient-independent features; file replacement invalidates it."""
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        return {
            nct: (digest, json.loads(payload))
            for nct, digest, payload in db.execute(
                "SELECT nct_id,source_hash,scoring_json FROM trial_features WHERE feature_version=? AND scoring_json IS NOT NULL",
                (VERSION,),
            )
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.snapshot, args.output)))
