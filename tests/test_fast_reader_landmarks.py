from pathlib import Path

import pytest

from evaluation.validate_fast_reader import run


def test_fast_reader_preserves_all_developer_reviewed_landmarks():
    corpus = Path(__file__).resolve().parents[1] / "evaluation" / "corpus"
    if len(list(corpus.glob("*.pdf"))) != 12:
        pytest.skip("Local public report corpus is intentionally not distributed")
    rows = run()
    assert len(rows) == 12
    assert all(row["passed"] for row in rows), [
        row for row in rows if not row["passed"]
    ]
