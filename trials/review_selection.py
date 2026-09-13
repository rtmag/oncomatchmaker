"""Budgeted expert review with clinical and geographic queues, separate axes."""


def select_for_review(candidates, landscape, budget, *, molecular_required=True):
    points = {p["nct_id"]: p for p in landscape}

    def score(candidate):
        value = points[candidate.nct_id].get("clinical_score")
        return value if value is not None else -1

    clinical = sorted(
        candidates,
        key=lambda c: (
            -score(c),
            -len(c.exact_variant_hits),
            -c.preliminary_score,
            c.nct_id,
        ),
    )
    plausible = [
        c
        for c in clinical
        if score(c) >= 0
        and points[c.nct_id]["clinical_assessment"]["components"].get("disease")
        is not None
        and (
            not molecular_required
            or points[c.nct_id]["clinical_assessment"]["components"].get("molecular")
            is not None
        )
    ]
    access = sorted(
        [c for c in plausible if points[c.nct_id].get("geography_score") is not None],
        key=lambda c: (-points[c.nct_id]["geography_score"], -score(c), c.nct_id),
    )
    uncertain = sorted(
        [
            c
            for c in clinical
            if c.exact_variant_hits
            or points[c.nct_id]["clinical_assessment"]["components"].get("molecular")
            is not None
        ],
        key=lambda c: (-len(c.exact_variant_hits), -score(c), c.nct_id),
    )
    chosen, seen = [], set()
    # Interleave, so early stopping after twelve reviews still considers access.
    queues = [
        iter(clinical),
        iter(clinical),
        iter(access),
        iter(uncertain),
        iter(access),
    ]
    while len(chosen) < min(budget, len(candidates)):
        added = False
        for queue in queues:
            for candidate in queue:
                if candidate.nct_id not in seen:
                    chosen.append(candidate)
                    seen.add(candidate.nct_id)
                    added = True
                    break
            if len(chosen) >= budget:
                break
        if not added:
            break
    return chosen
