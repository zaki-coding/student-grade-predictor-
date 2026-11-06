"""Remaining-mark scenarios are arithmetic projections, never ML predictions."""
import pytest


def test_projection_includes_unallocated_and_unfinished_weight():
    from src.calculator import project
    records = [{"name": "Quiz", "weight": 20, "mark": 80},
               {"name": "Exam", "weight": 50, "mark": None}]
    result = project(records, 75)
    assert result["contribution"] == 16
    assert result["remaining_weight"] == 80
    assert result["remaining_average"] == 75
    assert result["final_grade"] == 76


def test_completed_course_projection_cannot_change_earned_grade():
    from src.calculator import project
    records = [{"name": "Course", "weight": 100, "mark": 67}]
    for assumed in [0, 100]:
        assert project(records, assumed)["final_grade"] == 67


@pytest.mark.parametrize("assumed", [-1, 101, float("nan"), float("inf"), True, "75"])
def test_invalid_scenario_marks_rejected(assumed):
    from src.calculator import project
    with pytest.raises((ValueError, TypeError)):
        project([], assumed)


def test_projection_uses_grade_calculator_validation():
    from src.calculator import project
    with pytest.raises(ValueError):
        project([{"name": "Exam", "weight": 120, "mark": None}], 80)
