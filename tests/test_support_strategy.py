from evaluation.test_support_strategy import invariants, select


def test_fixed_denominator_unknowns_and_conflicts():
    result = invariants()
    assert result["disease_only_fixed"] == 13.5
    assert result["conflict_score"] is None


def test_access_slots_budget_and_replacement():
    rows = []
    for index in range(35):
        rows.append(
            {
                "nct_id": f"NCT{index:08}",
                "support": 40 if index < 20 else 36,
                "exact": ("G12D",),
                "retrieval": 80,
                "geo": 10 if index < 20 else 90,
                "negative_profile": False,
                "assessment": {
                    "components": {"disease": 0.6, "molecular": 0.9},
                    "uncertainty_bounds": [36, 91],
                },
            }
        )
    result = select(rows)
    assert len(result) == len({r["nct_id"] for r in result}) == 20
    assert sum(r["geo"] == 90 for r in result) >= 6
    excluded = {r["nct_id"] for r in result[:3]}
    replacement = select(rows, budget=3, excluded=excluded)
    assert len(replacement) == 3
    assert not excluded.intersection(r["nct_id"] for r in replacement)
