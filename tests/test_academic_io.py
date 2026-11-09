"""Check atomic CSV imports and exported academic summaries."""

import csv
from datetime import date
from io import StringIO
import json

import pytest

from app.persistence import MAX_WORKSPACE_BYTES, decode_workspace_bytes, encode_workspace_bytes, workspace_payload
from src.academic_io import import_assessments, import_courses
from src.exports import gpa_report_csv, semester_summary_csv
from src.gpa import course_gpa_rows
from src.planner import default_planning


def workspace():
    courses = {"Statistics": [{"name": "Quiz", "weight": 20, "mark": 80}]}
    return workspace_payload(courses, planning=default_planning(courses))


def test_courses_csv_adds_courses_and_assessments_csv_replaces_only_listed_courses():
    original = workspace()
    added = import_courses(b"\xef\xbb\xbfcourse,credits,target\r\nProgramming,4,82.5\r\nWriting,,\r\n", original)
    updated = import_assessments(
        b"course,name,kind,due,weight,mark\nProgramming,Final project,Project,2090-02-04,65,\n"
        b"Programming,Midterm,Exam,,35,80\n",
        added,
    )
    assert updated["planning"]["credits"] == {"Statistics": 3, "Programming": 4, "Writing": 3}
    assert updated["targets"]["Programming"] == 82.5
    assert updated["targets"]["Writing"] == 70
    assert updated["courses"]["Programming"][0] == {
        "name": "Final project", "kind": "Project", "due": "2090-02-04", "weight": 65, "mark": None,
    }
    assert updated["courses"]["Statistics"] == original["courses"]["Statistics"]
    assert added["courses"]["Programming"] == []
    assert list(original["courses"]) == ["Statistics"]
    assert decode_workspace_bytes(encode_workspace_bytes(updated)) == updated


def test_assessments_prefer_exact_legacy_course_names_before_trimming():
    courses = {"Statistics": [], " Statistics ": []}
    original = workspace_payload(courses, planning=default_planning(courses))
    updated = import_assessments(
        b"course,name,kind,due,weight,mark\n"
        b" Statistics ,Legacy exam,Exam,,100,80\n"
        b"  Statistics,Current exam,Exam,,100,90\n",
        original,
    )
    assert updated["courses"][" Statistics "][0]["name"] == "Legacy exam"
    assert updated["courses"]["Statistics"][0]["name"] == "Current exam"


@pytest.mark.parametrize(("data", "message"), [
    (b"course,credits,target\nNew course,3,70\nStatistics,4,75\n", "line 3"),
    (b"course,credits,credits\nTest,4,75\n", "headers"),
    (b"course,credits,target\nTest,3,70,unexpected\n", "wrong number"),
    (b'course,credits,target\n"Unclosed,3,75\n', "invalid quoting"),
    (b"course,credits,target\nTest,inf,70\n", "finite"),
    (b" " * (MAX_WORKSPACE_BYTES + 1), "no larger"),
])
def test_invalid_courses_leave_workspace_untouched(data, message):
    original = workspace()
    saved = encode_workspace_bytes(original)
    with pytest.raises(ValueError, match=message):
        import_courses(data, original)
    assert encode_workspace_bytes(original) == saved


@pytest.mark.parametrize(("last_row", "message"), [
    (b"Missing course,Final,Exam,,10,\n", "add this course"),
    (b"Statistics,Final,Exam,2090-02-30,10,\n", "YYYY-MM-DD"),
    (b"Statistics,Final,Exam,,80,\n", "cannot exceed"),
])
def test_invalid_assessments_do_not_replace_any_rows(last_row, message):
    original = workspace()
    csv_bytes = b"course,name,kind,due,weight,mark\nStatistics,Midterm,Exam,,35,80\n" + last_row
    with pytest.raises(ValueError, match=message):
        import_assessments(csv_bytes, original)
    assert original["courses"]["Statistics"] == [{"name": "Quiz", "weight": 20, "mark": 80}]


def test_near_limit_v1_can_open_even_when_its_migrated_export_exceeds_limit():
    courses = {
        str(i): [{"name": "x" * 164, "weight": 0, "mark": None} for _ in range(100)]
        for i in range(50)
    }
    raw = {"version": 1, "courses": courses}
    data = json.dumps(raw, separators=(",", ":")).encode("utf-8")
    excess_slots = iter(record for records in courses.values() for record in records)
    for _ in range(MAX_WORKSPACE_BYTES - len(data)):
        next(excess_slots)["name"] += "x"
    data = json.dumps(raw, separators=(",", ":")).encode("utf-8")
    assert len(data) == MAX_WORKSPACE_BYTES
    clean = decode_workspace_bytes(data)
    assert clean["version"] == 2 and len(clean["courses"]) == 50
    with pytest.raises(ValueError, match="exceed 1 MB"):
        encode_workspace_bytes(clean)


def test_semester_and_gpa_exports_include_context_and_escape_labels():
    course = "=HYPERLINK(1)"
    prior = "+Other term"
    courses = {course: [{"name": "Exam", "weight": 100, "mark": 91}]}
    credits = {course: 4}
    semester = list(csv.DictReader(StringIO(semester_summary_csv(courses, {course: 92}, credits, date(2026, 11, 9)))))
    assert semester[0]["Course"] == "'" + course
    assert semester[0]["Completed assessments"] == "1"
    assert semester[0]["As of"] == "2026-11-09"
    rows = course_gpa_rows(courses, credits, {"@A": 90}, {"maximum": 4, "points": {"@A": 4}})
    report = list(csv.DictReader(StringIO(gpa_report_csv(rows, [{"name": prior, "credits": 2, "gpa": 3}], 4))))
    assert report[0]["Name"] == "'" + course
    assert report[0]["Grade label"] == "'@A"
    assert report[1]["Name"] == "'" + prior
    assert report[-1]["GPA"] == "3.666667"

