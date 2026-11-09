"""Validate user-controlled workspace files before applying them to a session."""

import json

from src.calculator import validate_number, calculate, classify
from src.gpa import positive_credits, validate_scale
from src.planner import ASSESSMENT_KINDS, assessment_date, default_planning


DEFAULT_THRESHOLDS = {"A": 90, "B": 80, "C": 70, "D": 60, "F": 0}


def validate_courses(payload):
    """Read an original version 1 course export."""
    if (not isinstance(payload, dict) or set(payload) != {"version", "courses"}
            or type(payload.get("version")) is not int or payload["version"] != 1):
        raise ValueError("Expected a version 1 course export.")
    return _courses(payload["courses"])


def _courses(courses, include_planning=False):
    if not isinstance(courses, dict) or not 1 <= len(courses) <= 50:
        raise ValueError("An export must contain between 1 and 50 courses.")
    required = {"name", "weight", "mark"}
    allowed = required | {"kind", "due"} if include_planning else required
    clean = {}
    for name, records in courses.items():
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ValueError("Each course needs a name of 1–100 characters.")
        if not isinstance(records, list) or len(records) > 100:
            raise ValueError("Each course must contain a list of at most 100 assessments.")
        for record in records:
            if not isinstance(record, dict) or not required <= set(record) <= allowed:
                raise ValueError("Each assessment needs a name, weight and mark field.")
            if not isinstance(record["name"], str) or len(record["name"]) > 200:
                raise ValueError("Assessment names must contain at most 200 characters.")
            if record.get("kind", "Other") not in ASSESSMENT_KINDS:
                raise ValueError("Use Quiz, Assignment, Exam, Project or Other for assessment types.")
            assessment_date(record.get("due"))
        calculate(records)
        clean[name] = [dict(record) for record in records]
    return clean


def _thresholds(value):
    if not isinstance(value, dict) or not 1 <= len(value) <= 20:
        raise ValueError("Supply between 1 and 20 grading thresholds.")
    if any(not isinstance(k, str) or not k.strip() or len(k) > 100 for k in value):
        raise ValueError("Threshold labels must contain 1–100 characters.")
    classify(0, value)
    return dict(value)


def _planning(value, courses):
    if not isinstance(value, dict) or set(value) != {"credits", "gpa_scale", "gpa_history"}:
        raise ValueError("Planning data needs course credits, a GPA scale and semester GPA history.")
    credits = value["credits"]
    if not isinstance(credits, dict) or set(credits) != set(courses):
        raise ValueError("Enter credit hours for every course.")
    scale = validate_scale(value["gpa_scale"])
    history = value["gpa_history"]
    if not isinstance(history, list) or len(history) > 100:
        raise ValueError("Keep at most 100 semesters in GPA history.")
    semesters = []
    names = set()
    for entry in history:
        if not isinstance(entry, dict) or set(entry) != {"name", "credits", "gpa"}:
            raise ValueError("Each prior semester needs a name, credits and GPA.")
        name = entry["name"]
        if not isinstance(name, str) or not name.strip() or len(name) > 100 or name in names:
            raise ValueError("Each prior semester needs a unique name of 1–100 characters.")
        names.add(name)
        semesters.append({
            "name": name,
            "credits": positive_credits(entry["credits"]),
            "gpa": validate_number(entry["gpa"], "GPA", high=scale["maximum"]),
        })
    return {
        "credits": {name: positive_credits(credits[name]) for name in courses},
        "gpa_scale": scale,
        "gpa_history": semesters,
    }


def validate_workspace(payload):
    """Read older exports and validate all version 3 planning fields."""
    if not isinstance(payload, dict) or type(payload.get("version")) is not int:
        raise ValueError("Expected a versioned course workspace.")
    version = payload["version"]
    if version == 1:
        courses = validate_courses(payload)
        return {"version": 2, "courses": courses,
                "targets": {name: 70.0 for name in courses},
                "thresholds": dict(DEFAULT_THRESHOLDS)}
    fields = {"version", "courses", "targets", "thresholds"}
    if version == 3:
        fields.add("planning")
    if version not in (2, 3) or set(payload) != fields:
        raise ValueError("Expected a version 2 or 3 workspace with courses, targets and thresholds.")
    courses = _courses(payload["courses"], include_planning=version == 3)
    targets = payload["targets"]
    if not isinstance(targets, dict) or set(targets) != set(courses):
        raise ValueError("Every course must have exactly one target grade.")
    normalized_targets = {}
    for name, records in courses.items():
        calculate(records, targets[name])
        normalized_targets[name] = float(targets[name])
    clean = {"version": version, "courses": courses, "targets": normalized_targets,
             "thresholds": _thresholds(payload["thresholds"])}
    if version == 3:
        clean["planning"] = _planning(payload["planning"], courses)
    return clean


def workspace_payload(courses, targets=None, thresholds=None, planning=None):
    """Build a validated save from session state."""
    if not isinstance(courses, dict):
        raise ValueError("Courses must be an object.")
    if targets is None:
        targets = {}
    if not isinstance(targets, dict):
        raise ValueError("Targets must be an object.")
    payload = {
        "version": 2,
        "courses": courses,
        "targets": {name: targets.get(name, 70.0) for name in courses},
        "thresholds": DEFAULT_THRESHOLDS if thresholds is None else thresholds,
    }
    has_assessment_details = any(
        isinstance(record, dict) and ("kind" in record or "due" in record)
        for records in courses.values() if isinstance(records, list)
        for record in records
    )
    if planning is not None or has_assessment_details:
        payload["version"] = 3
        payload["planning"] = default_planning(courses) if planning is None else planning
    return validate_workspace(payload)


MAX_WORKSPACE_BYTES = 1_000_000


def _serialize_workspace(workspace):
    try:
        return json.dumps(workspace, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("Workspace text must be valid UTF-8.") from None


def encode_workspace_bytes(workspace):
    """Keep generated JSON within the same size limit as uploads."""
    raw = _serialize_workspace(workspace)
    if len(raw) > MAX_WORKSPACE_BYTES:
        raise ValueError("The workspace would exceed 1 MB. Split the records into smaller workspaces.")
    return raw


def decode_workspace_bytes(content):
    """Decode an untrusted JSON upload without persisting or echoing its contents."""

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
        clean = validate_workspace(payload)
        _serialize_workspace(clean)
        return clean
    except (UnicodeError, ValueError, TypeError, KeyError, RecursionError, OverflowError):
        raise ValueError("The file is not a valid supported workspace. Check its format, grades and weights; your current workspace was kept.") from None
