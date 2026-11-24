import numpy as np
import pandas as pd
import pytest

from src.university_data import (
    ENTRY, FIRST_TERM, OU_ACTIVITY, PT_FEATURES, assessment_rows, activity_totals,
    chronological_parts, portalegre_rows, verified_zip,
)
from src.university_evaluation import portuguese_parts, predict


def test_marks_require_a_past_deadline_submission_and_feedback_buffer():
    schedule = pd.DataFrame({
        "id_assessment": range(1, 10), "date": [10, 25, 35, 18, 22, 15, 80, 100, 110],
        "code_module": ["A"] * 8 + ["B"], "code_presentation": "2013J", "assessment_type": "TMA",
    })
    scores = pd.DataFrame({
        "id_assessment": range(1, 10), "id_student": 1,
        "date_submitted": [10, 70, 45, 15, 22, 15, 79, 70, 110],
        "score": [0, 100, 95, 90, np.nan, 70, 85, 66, 88],
        "is_banked": [0, 0, 0, 1, 0, 0, 0, 0, 0],
    })
    rows = assessment_rows(schedule, scores).set_index("id_assessment")
    # Day 45 + 28 is the cutoff itself. Only the scores of 0 and 70 qualify.
    assert rows.loc[7, ["last_grade", "mean_grade", "prior_count"]].tolist() == [70, 35, 2]
    assert not {4, 5, 8}.intersection(rows.index)
    assert rows.loc[9, "prior_count"] == 0
    scores.loc[scores.id_assessment.eq(7), "score"] = 12
    changed = assessment_rows(schedule, scores).set_index("id_assessment")
    assert changed.loc[7, "mean_grade"] == rows.loc[7, "mean_grade"]


def test_clicks_use_only_the_previous_fourteen_days_in_the_same_presentation():
    days = [5, 6, 19, 20, 21, 10, 11, 8]
    clicks = pd.DataFrame({
        "code_module": ["A"] * 6 + ["B", "A"], "code_presentation": ["2013J"] * 5 + ["2014J", "2013J", "2013J"],
        "id_student": [1] * 7 + [2], "date": days, "sum_click": [90, 3, 4, 80, 70, 60, 50, 2],
    })
    schedule = pd.DataFrame([["A", "2013J", 20]], columns=ENTRY[:2] + ["cutoff"])
    totals = activity_totals([clicks.iloc[:2], clicks.iloc[2:]], schedule)
    assert totals.set_index("id_student")[OU_ACTIVITY].to_dict() == {1: 7, 2: 2}


def test_later_students_and_unavailable_training_labels_are_excluded():
    rows = pd.DataFrame([
        ("2013B", 1, 175), ("2013B", 2, 179), ("2013B", 3, 181), ("2013B", 6, 1),
        ("2013J", 2, 310), ("2013J", 4, 321), ("2013J", 6, 250),
        ("2014B", 5, 120), ("2014J", 6, 260),
    ], columns=["code_presentation", "id_student", "available"])
    assert [set(part.id_student) for part in chronological_parts(rows)] == [{1}, {2}, {6}]


def test_second_term_eligibility_is_separate_from_the_first_term_inputs():
    frame = pd.DataFrame({field: [1, 2, 3] for field in PT_FEATURES})
    frame[FIRST_TERM[0]] = [0, 12, 13]
    frame["Course"] = 9
    frame["Curricular units 2nd sem (grade)"] = [11, 0, 15]
    frame["Curricular units 2nd sem (approved)"] = [2, 0, 3]
    frame["Target"] = ["Dropout", "Graduate", "Graduate"]
    frame["Tuition fees up to date"] = 1
    rows, coverage = portalegre_rows(frame)
    assert list(rows) == PT_FEATURES + ["Course", "score"]
    assert rows.score.tolist() == [11, 15]
    assert np.isnan(rows.iloc[0][FIRST_TERM[0]])
    assert coverage[False]["Graduate"] == 1
    frame["Target"] = "Enrolled"
    pd.testing.assert_frame_equal(rows, portalegre_rows(frame)[0])


def test_split_and_predictions_reproduce_without_reading_holdout_labels():
    rows = pd.DataFrame({"value": np.arange(100, dtype=float), "score": np.arange(100) % 20})
    parts = portuguese_parts(rows)
    assert [len(part) for part in parts] == [60, 20, 20]
    assert len(set.intersection(set(parts[0].index), set(parts[2].index))) == 0
    train, _, test = parts
    test = test.copy()
    test.iloc[0, 0] = np.nan
    for part, repeat in zip(parts, portuguese_parts(rows)):
        pd.testing.assert_frame_equal(part, repeat)
    for method in ("linear", "boosting"):
        first = predict(train, test, (method, ["value"]), 20)
        second = predict(train, test.drop(columns="score"), (method, ["value"]), 20)
        np.testing.assert_array_equal(first, second)
        assert np.all((first >= 0) & (first <= 20))


def test_unexpected_archive_is_rejected_before_reading_records(tmp_path):
    path = tmp_path / "unexpected.zip"
    path.write_bytes(b"other version")
    with pytest.raises(ValueError, match="SHA-256"):
        verified_zip(path, "0" * 64)
