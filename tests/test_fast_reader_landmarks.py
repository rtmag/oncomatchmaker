from evaluation.validate_fast_reader import run


def test_fast_reader_preserves_all_developer_reviewed_landmarks():
    rows = run()
    assert len(rows) == 12
    assert all(row["passed"] for row in rows), [
        row for row in rows if not row["passed"]
    ]
