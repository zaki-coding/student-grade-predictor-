"""The calculator is exact arithmetic, independent of all model artifacts."""
import math

import pytest

from src.calculator import calculate, classify


def assessment(weight, mark=None, name="Assessment"):
    return {"name": name, "weight": weight, "mark": mark}


def test_weighted_contributions_and_outstanding_target():
    result = calculate([assessment(30, 80), assessment(20, 60), assessment(50)], 70)
    assert result["contribution"] == pytest.approx(36)
    assert result["completed_weight"] == 50
    assert result["completed_average"] == pytest.approx(72)
    assert result["remaining_weight"] == 50
    assert result["required_average"] == pytest.approx(68)
    assert result["target_possible"]


def test_unallocated_weight_is_included_in_target_assumption():
    result = calculate([assessment(20, 50), assessment(30)], 70)
    assert result["unallocated_weight"] == 50
    assert result["remaining_weight"] == 80
    assert result["required_average"] == pytest.approx(75)


def test_empty_records_are_valid_and_uncompleted():
    result = calculate([], 70)
    assert result["contribution"] == 0
    assert result["completed_average"] is None
    assert result["required_average"] == 70


def test_impossible_target():
    result = calculate([assessment(80, 40), assessment(20)], 90)
    assert result["maximum_final"] == pytest.approx(52)
    assert result["required_average"] > 100
    assert not result["target_possible"]


def test_completed_course_has_no_remaining_required_average():
    result = calculate([assessment(100, 75)], 70)
    assert result["remaining_weight"] == 0
    assert result["required_average"] is None
    assert result["target_reached"]
    assert calculate([assessment(100, 75)], 80)["target_possible"] is False


@pytest.mark.parametrize("records", [
    [assessment(60, 50), assessment(41, 50)],
    [assessment(-1, 50)], [assessment(101, 50)],
    [assessment(10, -1)], [assessment(10, 101)],
    [assessment(math.nan, 50)], [assessment(10, math.inf)],
    [assessment(True, 50)], [assessment(10, False)],
])
def test_invalid_records_rejected(records):
    with pytest.raises((ValueError, TypeError)):
        calculate(records)


@pytest.mark.parametrize("target", [-1, 101, math.nan, math.inf, True])
def test_invalid_targets_rejected(target):
    with pytest.raises((ValueError, TypeError)):
        calculate([], target)


def test_configurable_thresholds():
    thresholds = {"Distinction": 85, "Pass": 50, "Below pass": 0}
    assert classify(85, thresholds) == "Distinction"
    assert classify(84.9, thresholds) == "Pass"
    assert classify(30, thresholds) == "Below pass"
