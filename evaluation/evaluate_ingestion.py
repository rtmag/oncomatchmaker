"""Evaluate saved extraction audits against explicit, non-exhaustive landmarks."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from normalization.genes import get_registry
from schemas.molecular_profile import MolecularProfile
from trials.search import actionable_findings


def evaluate(directory):
    annotations = json.loads(
        Path(__file__).with_name("ingestion_landmarks.json").read_text()
    )
    rows = []
    for case in annotations["cases"]:
        paths = sorted(Path(directory).glob(case["prefix"] + "*.json"))
        if len(paths) != 1:
            rows.append(
                {"prefix": case["prefix"], "status": "missing_or_ambiguous_result"}
            )
            continue
        result = json.loads(paths[0].read_text())
        profile = MolecularProfile.model_validate(result["profile"])
        findings = [
            *profile.biomarkers.snv_indel,
            *profile.biomarkers.copy_number,
            *profile.biomarkers.fusions,
        ]
        recovered = []
        for expected in case["expected"]:
            matches = []
            for f in findings:
                text = " ".join(
                    str(v or "")
                    for k, v in f.model_dump().items()
                    if k
                    in {
                        "raw_alteration",
                        "protein_change",
                        "hgvs_c",
                        "alteration",
                        "partner",
                        "source_text",
                    }
                )
                if (
                    f.gene == expected["gene"]
                    and expected.get("alteration_contains", "").lower() in text.lower()
                    and (
                        not expected.get("partner")
                        or getattr(f, "partner", None) == expected["partner"]
                    )
                    and (
                        not expected.get("non_tumor")
                        or f.origin in {"germline", "clonal_hematopoiesis"}
                        or f.potential_ch
                    )
                ):
                    matches.append(f)
            recovered.append(bool(matches))
        targets = {gene for gene, _ in actionable_findings(profile)}
        rows.append(
            {
                "file": paths[0].stem,
                "status": "evaluated",
                "landmarks_found": sum(recovered),
                "landmarks_expected": len(recovered),
                "missing_landmarks": [
                    e for e, ok in zip(case["expected"], recovered) if not ok
                ],
                "diagnosis_raw_matches": case["disease_contains"].lower()
                in profile.disease.raw_text.lower(),
                "invalid_hgnc_accepted": sum(
                    get_registry().resolve(f.gene).hgnc_id != f.hgnc_id
                    for f in findings
                ),
                "forbidden_targets": sorted(targets & set(case["forbidden_targets"])),
                "negative_pass": not findings if case.get("negative") else None,
                "msi_pass": profile.biomarkers.msi.status == case["msi"]
                if "msi" in case
                else None,
                "accepted_findings": len(findings),
                "held_for_review": len(result["rejected_findings"]),
                "warnings": result["warnings"],
            }
        )
    done = [r for r in rows if r["status"] == "evaluated"]
    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "annotation_scope": annotations["annotation_scope"],
        "reports_evaluated": len(done),
        "reports_expected": len(rows),
        "landmarks_found": sum(r["landmarks_found"] for r in done),
        "landmarks_expected": sum(len(c["expected"]) for c in annotations["cases"]),
        "invalid_hgnc_accepted": sum(r["invalid_hgnc_accepted"] for r in done),
        "forbidden_target_count": sum(len(r["forbidden_targets"]) for r in done),
        "cases": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = evaluate(args.directory)
    text = json.dumps(results, indent=2)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
