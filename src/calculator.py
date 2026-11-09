"""Exact weighted-grade arithmetic, independent of the prediction service.

Marks and weights are percentages. An unrecorded mark is None, never zero.
"""
from numbers import Real


def validate_number(value, name, low=0, high=100):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return float(value)


def calculate(assessments: list[dict], target: float = 70) -> dict:
    """Use the weighted mean of all outstanding/unallocated work for targets.

    Contribution is percentage points already earned toward the full course.
    completed_average normalizes only completed work; it is not a final grade.
    """
    target = validate_number(target, "Target")
    if not isinstance(assessments, list):
        raise ValueError("Assessments must be a list")
    total = completed = contribution = 0.0
    for record in assessments:
        if not isinstance(record, dict):
            raise ValueError("Each assessment must be an object")
        if not isinstance(record.get("name"), str) or not record["name"].strip():
            raise ValueError("Each assessment needs a name")
        weight = validate_number(record.get("weight"), "Weight")
        mark = record.get("mark")
        total += weight
        if mark is not None:
            mark = validate_number(mark, "Mark")
            completed += weight
            contribution += weight * mark / 100
    if total > 100 + 1e-9:
        raise ValueError("Assessment weights cannot exceed 100%")
    contribution = min(100.0, contribution)
    remaining = max(0.0, 100 - completed)
    unallocated = max(0.0, 100 - total)
    maximum = min(100.0, contribution + remaining)
    reached = contribution >= target - 1e-9
    required = None if remaining <= 1e-9 else max(0.0, (target - contribution) * 100 / remaining)
    return {
        "contribution": contribution,
        "completed_weight": completed,
        "remaining_weight": remaining,
        "unallocated_weight": unallocated,
        "completed_average": min(100.0, contribution * 100 / completed) if completed > 1e-9 else None,
        "required_average": required,
        "target_possible": target <= maximum + 1e-9,
        "maximum_final": maximum,
        "target_reached": reached,
    }


def classify(grade: float, thresholds: dict[str, float]) -> str:
    """Return the highest satisfied configured percentage boundary."""
    grade = validate_number(grade, "Grade")
    if not isinstance(thresholds, dict) or not thresholds:
        raise ValueError("Supply at least one grading threshold")
    boundaries = []
    for label, boundary in thresholds.items():
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Threshold labels must be nonempty strings")
        boundaries.append((label, validate_number(boundary, "Threshold")))
    for label, boundary in sorted(boundaries, key=lambda pair: pair[1], reverse=True):
        if grade >= boundary - 1e-9:
            return label
    return "Below configured thresholds"


def project(assessments: list[dict], remaining_average: float) -> dict:
    """Exact scenario: assume a weighted average across all outstanding work.

    Includes any unallocated assessment weight. This is arithmetic, not ML.
    A complete course ignores the assumed score because no weight remains.
    """
    score = validate_number(remaining_average, "Remaining average")
    result = calculate(assessments)
    return {
        "final_grade": result["contribution"] + result["remaining_weight"] * score / 100,
        "remaining_average": score,
        "remaining_weight": result["remaining_weight"],
        "contribution": result["contribution"],
    }


def _scenario_records(assessments: list[dict], scores: dict[int, float]) -> list[dict]:
    if not isinstance(scores, dict):
        raise ValueError("Individual scores must be a mapping of assessment positions to marks")
    records = list(assessments)
    for index, score in scores.items():
        _unfinished_assessment(records, index)
        records[index] = {**records[index], "mark": validate_number(score, "Hypothetical mark")}
    return records


def _unfinished_assessment(assessments: list[dict], index: int) -> dict:
    if type(index) is not int or not 0 <= index < len(assessments):
        raise ValueError("Choose a valid assessment position")
    record = assessments[index]
    if record.get("mark") is not None:
        raise ValueError("Choose an assessment without a recorded mark")
    return record


def project_individual(
    assessments: list[dict], scores: dict[int, float], remaining_average: float, target: float = 70
) -> dict:
    """Apply individual marks and use one average for the rest of the course."""
    original = calculate(assessments, target)
    score = validate_number(remaining_average, "Remaining average")
    scenario = calculate(_scenario_records(assessments, scores), target)
    final_grade = min(100.0, scenario["contribution"] + scenario["remaining_weight"] * score / 100)
    return {
        "final_grade": final_grade,
        "remaining_average": score,
        "remaining_weight": original["remaining_weight"],
        "contribution": original["contribution"],
        "assumed_weight": scenario["remaining_weight"],
        "individual_contribution": scenario["contribution"] - original["contribution"],
        "target_met": final_grade >= target - 1e-9,
    }


def required_assessment_score(
    assessments: list[dict], index: int, other_scores: dict[int, float] | None = None,
    remaining_average: float = 0, target: float = 70,
) -> dict:
    """Find the mark needed on one unfinished assessment given the other marks."""
    calculate(assessments, target)
    record = _unfinished_assessment(assessments, index)
    scores = {} if other_scores is None else other_scores
    if isinstance(scores, dict) and index in scores:
        raise ValueError("Leave the assessment you are solving for out of the assumed marks")
    # Count the chosen weight as completed at zero when calculating fixed points.
    records = _scenario_records(assessments, scores)
    records[index] = {**record, "mark": 0}
    fixed = project(records, remaining_average)["final_grade"]
    weight = float(record["weight"])
    required = max(0.0, (target - fixed) * 100 / weight) if weight else None
    return {
        "required_score": required,
        "target_possible": target <= fixed + weight + 1e-9,
        "fixed_contribution": fixed,
        "weight": weight,
    }
