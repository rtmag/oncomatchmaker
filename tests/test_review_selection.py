from trials.candidate_retrieval import RetrievedCandidate
from trials.review_selection import select_for_review


def test_selection_deduplicates_and_geography_cannot_rescue_missing_molecular_support():
    candidates, points = [], []
    for i in range(35):
        nct = f"NCT{i:08d}"
        candidates.append(
            RetrievedCandidate(nct, (), (), 80, exact_variant_hits=("G12D",))
        )
        points.append(
            {
                "nct_id": nct,
                "clinical_score": 36 if i < 20 else 27,
                "geography_score": 10 if i < 20 else 90,
                "clinical_assessment": {
                    "components": {"disease": 0.6, "molecular": 0.6}
                },
            }
        )
    points[-1].update(clinical_score=13.5, geography_score=100)
    points[-1]["clinical_assessment"]["components"]["molecular"] = None
    selected = select_for_review(candidates, points, 20)
    ids = [c.nct_id for c in selected]
    assert len(ids) == len(set(ids)) == 20
    assert any(int(c.nct_id[3:]) >= 20 for c in selected[:5])
    assert candidates[-1].nct_id not in ids
    assert select_for_review(candidates, points, 1) == [candidates[0]]
    assert select_for_review(candidates, points, 0) == []
