"""Refresh the bundled, reproducible HGNC snapshot from the official complete set."""

import argparse
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from normalization.genes import SNAPSHOT, HGNCRegistry

URL = "https://storage.googleapis.com/public-download-files/hgnc/json/json/hgnc_complete_set.json"


def write_snapshot(raw: bytes, target=SNAPSHOT):
    upstream = json.loads(raw)
    docs = upstream["response"]["docs"]
    records = [
        {
            key: row[key]
            for key in ("symbol", "hgnc_id", "status", "alias_symbol", "prev_symbol")
            if key in row
        }
        for row in docs
        if row.get("status") == "Approved"
    ]
    HGNCRegistry(records)
    metadata = {
        "source": URL,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "upstream_sha256": hashlib.sha256(raw).hexdigest(),
        "upstream_header": upstream.get("responseHeader", {}),
        "approved_gene_count": len(records),
    }
    payload = json.dumps(
        {"metadata": metadata, "records": sorted(records, key=lambda r: r["symbol"])},
        separators=(",", ":"),
    ).encode()
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_bytes(gzip.compress(payload, mtime=0))
    temporary.replace(target)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-file", type=Path)
    args = parser.parse_args()
    if args.from_file:
        raw = args.from_file.read_bytes()
    else:
        response = httpx.get(URL, timeout=180, follow_redirects=True)
        response.raise_for_status()
        raw = response.content
    print(json.dumps(write_snapshot(raw), indent=2))


if __name__ == "__main__":
    main()
