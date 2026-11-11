"""Read course and assessment CSV files into a validated workspace."""

import csv
from io import StringIO
from math import isfinite

from app.persistence import MAX_WORKSPACE_BYTES, encode_workspace_bytes, workspace_payload
from src.calculator import validate_number
from src.gpa import positive_credits
from src.planner import DEFAULT_CREDITS

COURSE_FIELDS = ("course", "credits", "target")
ASSESSMENT_FIELDS = ("course", "name", "kind", "due", "weight", "mark")


def _rows(content, fields):
    if not isinstance(content, bytes) or not content or len(content) > MAX_WORKSPACE_BYTES:
        raise ValueError("Choose a nonempty CSV no larger than 1 MB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Save the file as UTF-8 CSV and try again.") from None
    reader = csv.DictReader(StringIO(text, newline=""), strict=True)
    try:
        headers = reader.fieldnames
        if headers is None or len(headers) != len(fields) or set(headers) != set(fields):
            raise ValueError("Use these CSV headers: " + ", ".join(fields) + ".")
        found = False
        for row in reader:
            if set(row) != set(fields) or any(value is None for value in row.values()):
                raise ValueError(f"CSV line {reader.line_num} has the wrong number of columns.")
            if any("\x00" in value for value in row.values()):
                raise ValueError(f"CSV line {reader.line_num} contains an invalid character.")
            found = True
            yield reader.line_num, {
                field: row[field] if field == "course" else row[field].strip() for field in fields
            }
        if not found:
            raise ValueError("Add at least one row below the CSV header.")
    except csv.Error:
        raise ValueError(f"CSV line {max(1, reader.line_num)} has invalid quoting or a field is too long.") from None


def _number(value, label, line, validator=validate_number):
    try:
        number = float(value)
    except ValueError:
        raise ValueError(f"CSV line {line}: enter a numeric {label}.") from None
    if not isfinite(number):
        raise ValueError(f"CSV line {line}: {label} must be finite.")
    try:
        return validator(number, label)
    except ValueError as exc:
        raise ValueError(f"CSV line {line}: {exc}.") from None


def _validated(workspace, courses, targets, credits):
    planning = {**workspace["planning"], "credits": credits}
    clean = workspace_payload(courses, targets, workspace["thresholds"], planning)
    encode_workspace_bytes(clean)
    return clean


def import_courses(content, workspace):
    """Add new courses. Existing courses and the input workspace are kept intact."""
    courses = dict(workspace["courses"])
    targets = dict(workspace["targets"])
    credits = dict(workspace["planning"]["credits"])
    for line, row in _rows(content, COURSE_FIELDS):
        name = row["course"].strip()
        if not 1 <= len(name) <= 100:
            raise ValueError(f"CSV line {line}: enter a course name of 1 to 100 characters.")
        if name in courses:
            raise ValueError(f"CSV line {line}: a course with this name already exists.")
        if len(courses) >= 50:
            raise ValueError("A workspace supports up to 50 courses.")
        courses[name] = []
        targets[name] = _number(row["target"], "target grade", line) if row["target"] else 70.0
        credits[name] = _number(row["credits"], "credit hours", line, positive_credits) if row["credits"] else DEFAULT_CREDITS
    return _validated(workspace, courses, targets, credits)


def import_assessments(content, workspace):
    """Replace assessments for listed courses after validating the entire import."""
    replacements = {}
    for line, row in _rows(content, ASSESSMENT_FIELDS):
        course = row["course"]
        if course not in workspace["courses"]:
            course = course.strip()
        if course not in workspace["courses"]:
            raise ValueError(f"CSV line {line}: add this course before importing its assessments.")
        records = replacements.setdefault(course, [])
        if len(records) >= 100:
            raise ValueError(f"CSV line {line}: a course supports up to 100 assessments.")
        record = {
            "name": row["name"], "weight": _number(row["weight"], "weight", line),
            "mark": _number(row["mark"], "mark", line) if row["mark"] else None,
        }
        if row["kind"]:
            record["kind"] = row["kind"]
        if row["due"]:
            record["due"] = row["due"]
        records.append(record)
    return _validated(workspace, {**workspace["courses"], **replacements},
                      workspace["targets"], workspace["planning"]["credits"])
