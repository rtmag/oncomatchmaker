"""Offline full-snapshot regression; no PDF changes or new LLM assessments."""

import json
import sqlite3
import time
from pathlib import Path

from schemas.molecular_profile import Location
from trials.candidate_retrieval import screen_trials
from trials.pipeline import SNAPSHOT, attach_screening_geography
from trials.registry_features import load
from trials.review_selection import select_for_review


def run():
    profiles = json.loads(
        (Path(__file__).parent / "matching_spike/profiles.json").read_text()
    )["cases"]
    profiles.append(
        {
            "case_id": "synthetic-cholangi-kras-g12d",
            "disease": {"raw_text": "cholangiocarcinoma"},
            "biomarkers": {"snv_indel": [{"gene": "KRAS", "protein_change": "G12D"}]},
        }
    )
    reference_ids = {
        "NCT06040541",
        "NCT05067283",
        "NCT06162221",
        "NCT06031688",
        "NCT07619339",
        "NCT05310643",
        "NCT07807800",
        "NCT07446322",
        "NCT06641609",
        "NCT04181060",
        "NCT06952803",
    }
    features = load(SNAPSHOT)
    assert len(features) == 26423
    results = []
    for profile in profiles:
        start = time.perf_counter()
        with sqlite3.connect(f"file:{SNAPSHOT}?mode=ro", uri=True) as db:
            screening = screen_trials(db, profile, features)
            points = list(screening.landscape)
            attach_screening_geography(
                db,
                points,
                Location(
                    city="Daegu",
                    country="South Korea",
                    latitude=35.8714,
                    longitude=128.6014,
                ),
            )
        selected = {
            c.nct_id for c in select_for_review(screening.candidates, points, 20)
        }
        results.append(
            {
                "case_id": profile["case_id"],
                "seconds": round(time.perf_counter() - start, 2),
                "screened": screening.total_screened,
                "pool": len(screening.candidates),
                "selected": len(selected),
                "high_score_low_coverage": sum(
                    (p["clinical_score"] or 0) >= 80
                    and p["clinical_assessment"]["coverage"] <= 0.45
                    for p in points
                ),
                "references": {
                    p["nct_id"]: {
                        "score": p["clinical_score"],
                        "molecular": p["clinical_assessment"]["components"][
                            "molecular"
                        ],
                        "selected": p["nct_id"] in selected,
                        "status": p["clinical_assessment"]["status"],
                    }
                    for p in points
                    if p["nct_id"] in reference_ids
                },
            }
        )
    cholangi = results[-1]["references"]
    assert cholangi["NCT06040541"]["selected"]
    for nct in ("NCT05067283", "NCT06162221"):
        assert cholangi[nct]["score"] is None and not cholangi[nct]["selected"]
    msi = next(r for r in results if "msih" in r["case_id"])["references"]
    assert not msi["NCT07446322"]["selected"] and msi["NCT07446322"]["score"] is None
    assert msi["NCT05310643"]["molecular"] is not None
    assert msi["NCT07807800"]["molecular"] is not None
    for row, expected in zip(
        results[:4],
        [
            {"NCT06641609", "NCT04181060"},
            {"NCT06031688", "NCT07619339"},
            {"NCT06952803"},
            {"NCT05310643", "NCT07807800"},
        ],
    ):
        assert all(row["references"][nct]["selected"] for nct in expected)
    assert all(r["high_score_low_coverage"] == 0 for r in results)
    return results


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
