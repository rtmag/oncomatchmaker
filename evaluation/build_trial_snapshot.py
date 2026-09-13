"""Build a complete, versioned CTGov oncology SQLite snapshot (stdlib only)."""
import argparse
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import urllib.parse
import urllib.request

BASE = "https://clinicaltrials.gov/api/v2"
# Condition search uses registry synonym/MeSH expansion. Broad collection is
# intentional; benign tumors and non-treatment research must be filtered later.
TERMS = ["neoplasms", "cancer", "oncology", "tumor", "tumour", "malignancy",
         "leukemia", "leukaemia", "lymphoma", "myeloma", "myelodysplastic",
         "myeloproliferative", "sarcoma", "melanoma", "glioma", "glioblastoma",
         "mesothelioma", "carcinoma", "neuroblastoma", "retinoblastoma",
         "blastoma", "histiocytosis", "mastocytosis", "Waldenstrom",
         "myelofibrosis", "polycythemia vera", "essential thrombocythemia",
         "germ cell", "trophoblastic", "neuroendocrine", "thymoma"]
QUERY = " OR ".join('"' + term + '"' for term in TERMS)

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE studies(
 nct_id TEXT PRIMARY KEY, title TEXT, overall_status TEXT, study_type TEXT,
 primary_purpose TEXT, eligibility_text TEXT, conditions_json TEXT NOT NULL,
 last_update_posted TEXT, status_verified TEXT, retrieved_at TEXT NOT NULL,
 source_url TEXT NOT NULL, raw_json TEXT NOT NULL, json_sha256 TEXT NOT NULL);
CREATE TABLE sites(
 nct_id TEXT REFERENCES studies(nct_id), ordinal INTEGER, facility TEXT,
 status TEXT, city TEXT, region TEXT, country TEXT, latitude REAL, longitude REAL,
 raw_json TEXT NOT NULL, PRIMARY KEY(nct_id, ordinal));
CREATE INDEX sites_status_country ON sites(status,country);
CREATE INDEX study_status ON studies(overall_status);
CREATE VIEW recruiting_sites AS
 SELECT sites.* FROM sites JOIN studies USING(nct_id)
 WHERE studies.overall_status='RECRUITING' AND sites.status='RECRUITING';
CREATE VIEW upcoming_sites AS
 SELECT sites.* FROM sites JOIN studies USING(nct_id)
 WHERE studies.overall_status IN ('RECRUITING','NOT_YET_RECRUITING')
 AND sites.status='NOT_YET_RECRUITING';
"""

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def fetch(url):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OncoMatchmaker-snapshot/0.1"})
            with urllib.request.urlopen(req, timeout=90) as response:
                raw = response.read()
            return raw, json.loads(raw)
        except (OSError, ValueError):
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)

def insert_study(db, study, timestamp):
    protocol = study["protocolSection"]
    ident = protocol["identificationModule"]
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    nct_id = ident["nctId"]
    raw = json.dumps(study, ensure_ascii=False, separators=(",", ":"))
    db.execute("INSERT INTO studies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        nct_id, ident.get("briefTitle"), status.get("overallStatus"),
        design.get("studyType"), design.get("designInfo", {}).get("primaryPurpose"),
        protocol.get("eligibilityModule", {}).get("eligibilityCriteria"),
        json.dumps(protocol.get("conditionsModule", {}).get("conditions", [])),
        status.get("lastUpdatePostDateStruct", {}).get("date"),
        status.get("statusVerifiedDate"), timestamp,
        "https://clinicaltrials.gov/study/" + nct_id,
        raw, hashlib.sha256(raw.encode()).hexdigest()))
    locations = protocol.get("contactsLocationsModule", {}).get("locations", [])
    for ordinal, site in enumerate(locations):
        geo = site.get("geoPoint", {})
        db.execute("INSERT INTO sites VALUES (?,?,?,?,?,?,?,?,?,?)", (
            nct_id, ordinal, site.get("facility"), site.get("status"),
            site.get("city"), site.get("state"), site.get("country"),
            geo.get("lat"), geo.get("lon"), json.dumps(site, ensure_ascii=False)))

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def build(output):
    output.mkdir(parents=True, exist_ok=False)
    _, version = fetch(BASE + "/version")
    manifest = {"schema_version": 1, "started_at": now(), "source": BASE,
                "registry_version": version, "condition_terms": TERMS,
                "query": QUERY, "statuses": ["RECRUITING", "NOT_YET_RECRUITING"],
                "scope": "Broad oncology candidate collection from ClinicalTrials.gov; not guaranteed exhaustive or treatment-specific",
                "pages": []}
    path = output / "oncology.sqlite"
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    token = None
    seen_tokens = set()
    expected = None
    # Preserve byte-exact HTTP JSON bodies as compressed JSONL (one API page/line
    # is not guaranteed: use separate gzip files to retain original formatting).
    raw_dir = output / "registry-pages"
    raw_dir.mkdir()
    while True:
        params = {"query.cond": QUERY, "filter.overallStatus": ",".join(manifest["statuses"]),
                  "pageSize": 1000, "countTotal": "true", "format": "json"}
        if token:
            params["pageToken"] = token
        url = BASE + "/studies?" + urllib.parse.urlencode(params)
        raw, payload = fetch(url)
        timestamp = now()
        expected = payload["totalCount"] if expected is None else expected
        if payload.get("totalCount", expected) != expected:
            raise RuntimeError("Registry count changed during download; rebuild")
        page_name = "page-{:04d}.json.gz".format(len(manifest["pages"]) + 1)
        with gzip.open(raw_dir / page_name, "wb") as stream:
            stream.write(raw)
        rows = payload.get("studies", [])
        with db:
            for study in rows:
                insert_study(db, study, timestamp)
        manifest["pages"].append({"file": "registry-pages/" + page_name,
                                  "url": url, "retrieved_at": timestamp,
                                  "response_sha256": hashlib.sha256(raw).hexdigest(),
                                  "records": len(rows)})
        print("Page {}: {} / {} studies".format(len(manifest["pages"]),
              db.execute("SELECT count(*) FROM studies").fetchone()[0], expected), flush=True)
        token = payload.get("nextPageToken")
        if not token:
            break
        if not rows or token in seen_tokens:
            raise RuntimeError("Invalid/repeated pagination token")
        seen_tokens.add(token)
        time.sleep(0.2)
    _, end_version = fetch(BASE + "/version")
    if version != end_version:
        raise RuntimeError("Registry refreshed during build; rebuild")
    actual = db.execute("SELECT count(*) FROM studies").fetchone()[0]
    if actual != expected:
        raise RuntimeError("Incomplete pagination: {} != {}".format(actual, expected))
    # Verify every raw registry location was copied, including missing statuses.
    for nct_id, raw in db.execute("SELECT nct_id, raw_json FROM studies"):
        count = len(json.loads(raw)["protocolSection"].get("contactsLocationsModule", {}).get("locations", []))
        if db.execute("SELECT count(*) FROM sites WHERE nct_id=?", (nct_id,)).fetchone()[0] != count:
            raise RuntimeError("Location count mismatch: " + nct_id)
    manifest.update({"completed_at": now(), "study_count": actual,
        "site_count": db.execute("SELECT count(*) FROM sites").fetchone()[0],
        "recruiting_site_count": db.execute("SELECT count(*) FROM recruiting_sites").fetchone()[0],
        "site_status_counts": dict(db.execute("SELECT coalesce(status,'MISSING'),count(*) FROM sites GROUP BY status")),
        "study_type_counts": dict(db.execute("SELECT coalesce(study_type,'MISSING'),count(*) FROM studies GROUP BY study_type")),
        "country_count": db.execute("SELECT count(DISTINCT country) FROM sites").fetchone()[0]})
    # Separate condition-query audits show explicit hematologic coverage.
    manifest["coverage_audits"] = {}
    for term in ["leukemia", "lymphoma", "myeloma", "myelodysplastic", "myeloproliferative"]:
        params = {"query.cond": term, "filter.overallStatus": ",".join(manifest["statuses"]),
                  "pageSize": 1000, "format": "json", "fields": "NCTId"}
        ids = set()
        while True:
            _, payload = fetch(BASE + "/studies?" + urllib.parse.urlencode(params))
            ids.update(s["protocolSection"]["identificationModule"]["nctId"] for s in payload.get("studies", []))
            if not payload.get("nextPageToken"):
                break
            params["pageToken"] = payload["nextPageToken"]
        missing = sorted(i for i in ids if not db.execute("SELECT 1 FROM studies WHERE nct_id=?", (i,)).fetchone())
        manifest["coverage_audits"][term] = {"registry_count": len(ids), "missing_ids": missing}
        if missing:
            raise RuntimeError("Coverage gap for " + term)
    if fetch(BASE + "/version")[1] != version:
        raise RuntimeError("Registry refreshed during coverage audit; rebuild")
    db.execute("INSERT INTO metadata VALUES (?,?)", ("manifest", json.dumps(manifest)))
    db.commit()
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("SQLite integrity failure")
    db.close()
    manifest["database"] = {"file": path.name, "sha256": digest(path), "bytes": path.stat().st_size}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k not in ("pages", "query", "condition_terms")}, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New snapshot directory; existing directories are never overwritten")
    build(parser.parse_args().output)
