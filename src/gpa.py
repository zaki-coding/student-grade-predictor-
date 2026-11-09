"""Calculate credit-weighted GPA on a configurable scale."""

from math import fsum

from src.calculator import validate_number

MAX_CREDITS = 1_000_000


def positive_credits(value, name="Credits") -> float:
    credits = validate_number(value, name, high=MAX_CREDITS)
    if credits <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return credits


def _maximum(value) -> float:
    maximum = validate_number(value, "GPA scale maximum")
    if maximum <= 0:
        raise ValueError("GPA scale maximum must be greater than zero")
    return maximum


def validate_scale(scale: dict) -> dict:
    if not isinstance(scale, dict) or set(scale) != {"maximum", "points"}:
        raise ValueError("A GPA scale needs a maximum and a grade-to-points mapping")
    maximum = _maximum(scale["maximum"])
    points = scale["points"]
    if not isinstance(points, dict) or not 1 <= len(points) <= 20:
        raise ValueError("Enter between 1 and 20 grade labels for the GPA scale")
    if any(not isinstance(label, str) or not label.strip() or len(label) > 100 for label in points):
        raise ValueError("GPA grade labels must have 1 to 100 characters")
    return {
        "maximum": maximum,
        "points": {label: validate_number(point, "Grade points", high=maximum) for label, point in points.items()},
    }


def points_for_grade(grade: str, scale: dict) -> float:
    points = validate_scale(scale)["points"]
    if not isinstance(grade, str) or grade not in points:
        raise ValueError(f"Add grade points for {grade!r} to the GPA scale")
    return points[grade]


def gpa_summary(entries: list[dict], maximum: float = 4.0) -> dict:
    """Combine course or semester GPAs by credit hours."""
    maximum = _maximum(maximum)
    credit_hours = []
    weighted_gpas = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Each GPA entry needs credits and a GPA")
        credits = positive_credits(entry.get("credits"))
        gpa = validate_number(entry.get("gpa"), "GPA", high=maximum)
        credit_hours.append(credits)
        weighted_gpas.append(credits * gpa)
    credits = fsum(credit_hours)
    quality_points = fsum(weighted_gpas)
    return {
        "credits": credits,
        "quality_points": quality_points,
        "gpa": min(maximum, quality_points / credits) if credits else None,
    }


def required_future_gpa(
    completed: list[dict], future_credits: float, target: float, maximum: float = 4.0
) -> dict:
    """Find the future GPA needed to reach the target cumulative GPA."""
    maximum = _maximum(maximum)
    target = validate_number(target, "Target GPA", high=maximum)
    future_credits = positive_credits(future_credits, "Future credits")
    previous = gpa_summary(completed, maximum)
    total_credits = previous["credits"] + future_credits
    remaining_points = max(0.0, target * total_credits - previous["quality_points"])
    return {
        "required_gpa": remaining_points / future_credits,
        "target_possible": target <= (
            previous["quality_points"] + maximum * future_credits
        ) / total_credits + 1e-9,
    }
