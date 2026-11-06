"""Exact weighted-grade arithmetic, independent of the prediction service.

Marks and weights are percentages. An unrecorded mark is None, never zero.
"""
from math import isfinite
from numbers import Real


def _number(value, name, low=0, high=100):
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return float(value)


def calculate(assessments: list[dict], target: float = 70) -> dict:
    """Use the weighted mean of all outstanding/unallocated work for targets.

    Contribution is percentage points already earned toward the full course.
    completed_average normalizes only completed work; it is not a final grade.
    """
    target = _number(target, "Target")
    if not isinstance(assessments, list):
        raise ValueError("Assessments must be a list")
    total = completed = contribution = 0.0
    for record in assessments:
        if not isinstance(record, dict):
            raise ValueError("Each assessment must be an object")
        if not isinstance(record.get("name"), str) or not record["name"].strip():
            raise ValueError("Each assessment needs a name")
        weight = _number(record.get("weight"), "Weight")
        mark = record.get("mark")
        total += weight
        if mark is not None:
            mark = _number(mark, "Mark")
            completed += weight
            contribution += weight * mark / 100
    if total > 100 + 1e-9:
        raise ValueError("Assessment weights cannot exceed 100%")
    remaining = max(0.0, 100 - completed)
    unallocated = max(0.0, 100 - total)
    maximum = contribution + remaining
    reached = contribution >= target - 1e-9
    required = None if remaining <= 1e-9 else max(0.0, (target - contribution) * 100 / remaining)
    return {
        "contribution": contribution,
        "completed_weight": completed,
        "remaining_weight": remaining,
        "unallocated_weight": unallocated,
        "completed_average": contribution * 100 / completed if completed > 1e-9 else None,
        "required_average": required,
        "target_possible": target <= maximum + 1e-9,
        "maximum_final": maximum,
        "target_reached": reached,
    }


def classify(grade: float, thresholds: dict[str, float]) -> str:
    """Return the highest satisfied configured percentage boundary."""
    grade = _number(grade, "Grade")
    if not isinstance(thresholds, dict) or not thresholds:
        raise ValueError("Supply at least one grading threshold")
    boundaries = []
    for label, boundary in thresholds.items():
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Threshold labels must be nonempty strings")
        boundaries.append((label, _number(boundary, "Threshold")))
    for label, boundary in sorted(boundaries, key=lambda pair: pair[1], reverse=True):
        if grade >= boundary:
            return label
    return "Below configured thresholds"


def project(assessments: list[dict], remaining_average: float) -> dict:
    """Exact scenario: assume a weighted average across all outstanding work.

    Includes any unallocated assessment weight. This is arithmetic, not ML.
    A complete course ignores the assumed score because no weight remains.
    """
    score = _number(remaining_average, "Remaining average")
    result = calculate(assessments)
    return {
        "final_grade": result["contribution"] + result["remaining_weight"] * score / 100,
        "remaining_average": score,
        "remaining_weight": result["remaining_weight"],
        "contribution": result["contribution"],
    }
