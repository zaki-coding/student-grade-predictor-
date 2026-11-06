"""Validation for user-controlled course exports; no automatic disk persistence."""

from src.calculator import calculate


def validate_courses(payload):
    """Validate the complete import before replacing any session state."""
    if (not isinstance(payload, dict) or set(payload) != {"version", "courses"}
            or type(payload.get("version")) is not int or payload["version"] != 1):
        raise ValueError("Expected a version 1 course export.")
    courses = payload.get("courses")
    if not isinstance(courses, dict) or not 1 <= len(courses) <= 50:
        raise ValueError("An export must contain between 1 and 50 courses.")
    clean = {}
    for name, records in courses.items():
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ValueError("Each course needs a name of 1–100 characters.")
        if not isinstance(records, list) or len(records) > 100:
            raise ValueError("Each course must contain a list of at most 100 assessments.")
        for record in records:
            if not isinstance(record, dict) or set(record) != {"name", "weight", "mark"}:
                raise ValueError("Each assessment needs exactly name, weight and mark.")
        if any(not isinstance(record["name"], str) or len(record["name"]) > 200 for record in records):
            raise ValueError("Assessment names must contain at most 200 characters.")
        calculate(records)
        clean[name] = [dict(record) for record in records]
    return clean


DEFAULT_THRESHOLDS = {"A": 90, "B": 80, "C": 70, "D": 60, "F": 0}


def _thresholds(value):
    from src.calculator import classify
    if not isinstance(value, dict) or not 1 <= len(value) <= 20:
        raise ValueError("Supply between 1 and 20 grading thresholds.")
    if any(not isinstance(k, str) or not k.strip() or len(k) > 100 for k in value):
        raise ValueError("Threshold labels must contain 1–100 characters.")
    classify(0, value)
    return dict(value)


def validate_workspace(payload):
    """Atomically normalize a saved workspace; migrate original version 1 files.

    Version 2 persists targets and grading boundaries as well as assessments.
    This module never writes a user's educational records to server disk.
    """
    if not isinstance(payload, dict) or type(payload.get("version")) is not int:
        raise ValueError("Expected a versioned course workspace.")
    if payload["version"] == 1:
        courses = validate_courses(payload)
        return {"version": 2, "courses": courses,
                "targets": {name: 70.0 for name in courses},
                "thresholds": dict(DEFAULT_THRESHOLDS)}
    if payload["version"] != 2 or set(payload) != {"version", "courses", "targets", "thresholds"}:
        raise ValueError("Expected a version 2 workspace with courses, targets and thresholds.")
    courses = validate_courses({"version": 1, "courses": payload["courses"]})
    targets = payload["targets"]
    if not isinstance(targets, dict) or set(targets) != set(courses):
        raise ValueError("Every course must have exactly one target grade.")
    normalized_targets = {}
    for name, records in courses.items():
        calculate(records, targets[name])  # Includes finite/type/range checks.
        normalized_targets[name] = float(targets[name])
    return {"version": 2, "courses": courses, "targets": normalized_targets,
            "thresholds": _thresholds(payload["thresholds"])}


def workspace_payload(courses, targets=None, thresholds=None):
    """Build a validated portable save from session state, supplying defaults."""
    if not isinstance(courses, dict):
        raise ValueError("Courses must be an object.")
    if targets is None:
        targets = {}
    if not isinstance(targets, dict):
        raise ValueError("Targets must be an object.")
    return validate_workspace({"version": 2, "courses": courses,
        "targets": {name: targets.get(name, 70.0) for name in courses},
        "thresholds": DEFAULT_THRESHOLDS if thresholds is None else thresholds})


MAX_WORKSPACE_BYTES = 1_000_000


def decode_workspace_bytes(content):
    """Decode an untrusted JSON upload without persisting or echoing its contents."""
    import json

    if not isinstance(content, bytes) or not content or len(content) > MAX_WORKSPACE_BYTES:
        raise ValueError("Choose a nonempty JSON workspace no larger than 1 MB.")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON fields are not allowed.")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("Workspace numbers must be finite.")

    try:
        payload = json.loads(content.decode("utf-8-sig"), object_pairs_hook=pairs,
                             parse_constant=constant)
        return validate_workspace(payload)
    except (UnicodeError, ValueError, TypeError, KeyError, RecursionError, OverflowError):
        raise ValueError("The file is not a valid supported workspace. Check its format, grades and weights; your current workspace was kept.") from None
