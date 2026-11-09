"""Summarize the same courses and assessments used by the calculator."""

from datetime import date

from src.calculator import calculate

ASSESSMENT_KINDS = ("Quiz", "Assignment", "Exam", "Project", "Other")


def default_planning(courses: dict) -> dict:
    return {
        "credits": {course: 3.0 for course in courses},
        "gpa_scale": {"maximum": 4.0, "points": {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}},
        "gpa_history": [],
    }


def assessment_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        due = date.fromisoformat(value)
        if due.isoformat() == value:
            return due
    except (TypeError, ValueError):
        pass
    raise ValueError("Assessment dates must use YYYY-MM-DD")


def semester_summary(courses: dict, targets: dict, today: date) -> dict:
    """Summarize completion and sort incomplete assessments by due date."""
    summaries = {}
    upcoming = []
    overdue = []
    completed_count = assessment_count = 0
    for course, records in courses.items():
        grade = calculate(records, targets[course])
        completed = sum(record.get("mark") is not None for record in records)
        summaries[course] = {**grade, "completed_count": completed, "assessment_count": len(records)}
        completed_count += completed
        assessment_count += len(records)
        for index, record in enumerate(records):
            due = assessment_date(record.get("due"))
            if due is None or record.get("mark") is not None:
                continue
            deadlines = overdue if due < today else upcoming
            deadlines.append({
                "course": course, "index": index, "name": record["name"],
                "weight": record["weight"], "due": due.isoformat(), "kind": record.get("kind", "Other"),
            })
    for deadlines in (upcoming, overdue):
        deadlines.sort(key=lambda item: (item["due"], item["course"].casefold(), item["index"]))
    return {
        "courses": summaries,
        "completed_count": completed_count,
        "assessment_count": assessment_count,
        "progress": 100 * completed_count / assessment_count if assessment_count else None,
        "upcoming": upcoming,
        "overdue": overdue,
    }
