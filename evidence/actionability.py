import json
from pathlib import Path

from schemas.match_results import ApprovedOption
from trials.search import actionable_findings, disease_name


def find_approved_options(profile):
    biomarkers = {
        f"{gene} {variant}".strip() for gene, variant in actionable_findings(profile)
    }
    disease = disease_name(profile.disease.normalized or profile.disease.raw_text)
    options = []
    for raw in json.loads(Path(__file__).with_name("options.json").read_text()):
        if raw["biomarker"] not in biomarkers:
            continue
        option = ApprovedOption.model_validate(raw)
        if option.context != "tumor_agnostic":
            option.context = (
                "same_disease"
                if disease == disease_name(option.disease)
                else "other_disease"
            )
        options.append(option)
    return options
