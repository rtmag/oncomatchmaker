"""Download and verify the released oncology SQLite snapshot for deployment."""

from __future__ import annotations

import gzip
import hashlib
import os
import shutil
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data" / "snapshots" / "2026-09-13-v1" / "oncology.sqlite"
URL = "https://github.com/rtmag/oncomatchmaker/releases/download/oncology-snapshot-2026-09-13-v1/oncology.sqlite.gz"
SHA256 = "d08b631bb7ab5a871b0b883d36d6c1a74a3097a700eb4cf6255a0f4794df501e"


def ensure_snapshot(target: Path = TARGET) -> Path:
    if target.is_file() and target.stat().st_size > 1_000_000:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    archive = target.with_suffix(".sqlite.gz.part")
    database = target.with_suffix(".sqlite.part")
    digest = hashlib.sha256()
    url = os.environ.get("ONCOMATCH_SNAPSHOT_URL", URL)
    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
        response.raise_for_status()
        with archive.open("wb") as output:
            for chunk in response.iter_bytes():
                digest.update(chunk)
                output.write(chunk)
    expected = os.environ.get("ONCOMATCH_SNAPSHOT_SHA256", SHA256)
    if digest.hexdigest() != expected:
        archive.unlink(missing_ok=True)
        raise RuntimeError("Oncology snapshot checksum verification failed.")
    with gzip.open(archive, "rb") as source, database.open("wb") as output:
        shutil.copyfileobj(source, output)
    database.replace(target)
    archive.unlink(missing_ok=True)
    return target


if __name__ == "__main__":
    print(ensure_snapshot())
