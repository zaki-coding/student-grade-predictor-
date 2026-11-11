"""Examples and edge cases for semester planning and grade arithmetic."""
from copy import deepcopy
from datetime import date
import json

import pytest

from app.persistence import decode_workspace_bytes, workspace_payload
from src.calculator import project_individual, required_assessment_score
from src.gpa import gpa_summary, points_for_grade, required_future_gpa
from src.planner import default_planning, semester_summary


def assessment(name, weight, mark=None, **details):
    return {"name": name, "weight": weight, "mark": mark, **details}


def test_exam_score_needed_for_target():
    records = [
        assessment("Midterm", 30, 75),
        assessment("Assignments", 20, 90),
        assessment("Final", 50),
    ]
    result = required_assessment_score(records, 2, target=80)
    assert result["fixed_contribution"] == pytest.approx(40.5)
    assert result["required_score"] == pytest.approx(79)
    assert result["target_possible"]
    assert not required_assessment_score(records, 2, target=91)["target_possible"]


def test_individual_scenarios_allow_zero_and_preserve_original_marks():
    records = [
        assessment("Midterm", 30, 75),
        assessment("Project", 20),
        assessment("Final", 30),
    ]
    before = deepcopy(records)
    low = project_individual(records, {1: 0, 2: 100}, 80, target=75)
    high = project_individual(records, {1: 90, 2: 100}, 80, target=75)
    assert low["final_grade"] == pytest.approx(68.5)
    assert not low["target_met"]
    assert high["final_grade"] == pytest.approx(86.5)
    assert high["target_met"]
    assert records == before


def test_required_exam_score_accounts_for_other_marks_and_unallocated_weight():
    records = [
        assessment("Midterm", 30, 75),
        assessment("Project", 20),
        assessment("Final", 30),
    ]
    result = required_assessment_score(records, 2, {1: 90}, 80, target=80)
    assert result["fixed_contribution"] == pytest.approx(56.5)
    assert result["required_score"] == pytest.approx(78.3333333333)


@pytest.mark.parametrize("scores", [{0: 90}, {-1: 10}, {2: 80}, {True: 80}, {1: 101}, {1: float("nan")}])
def test_scenario_rejects_invalid_assessment_overrides(scores):
    records = [assessment("Midterm", 30, 75), assessment("Final", 70)]
    with pytest.raises((ValueError, TypeError)):
        project_individual(records, scores, 50)


def test_zero_weight_assessment_cannot_change_target():
    records = [assessment("Midterm", 100, 70), assessment("Practice", 0)]
    assert required_assessment_score(records, 1, target=80)["required_score"] is None
    assert not required_assessment_score(records, 1, target=80)["target_possible"]
    assert required_assessment_score(records, 1, target=70)["target_possible"]


def test_gpa_uses_credit_weighting_and_custom_points():
    scale = {"maximum": 5.0, "points": {"High Pass": 4.5, "Pass": 3.0, "Fail": 0.0}}
    assert points_for_grade("High Pass", scale) == 4.5
    entries = [
        {"credits": 2, "gpa": points_for_grade("High Pass", scale)},
        {"credits": 4, "gpa": points_for_grade("Pass", scale)},
    ]
    semester = gpa_summary(entries, maximum=5)
    assert semester == {"credits": 6, "quality_points": 21, "gpa": 3.5}
    cumulative = gpa_summary([semester, {"credits": 12, "gpa": 3.8}], maximum=5)
    assert cumulative["gpa"] == pytest.approx(3.7)
    assert gpa_summary([])["gpa"] is None


def test_future_gpa_shows_achievable_and_impossible_targets():
    completed = [{"credits": 30, "gpa": 3.0}]
    result = required_future_gpa(completed, 15, 3.2)
    assert result["required_gpa"] == pytest.approx(3.6)
    assert result["target_possible"]
    assert required_future_gpa(completed, 15, 3.8)["required_gpa"] == pytest.approx(5.4)
    assert not required_future_gpa(completed, 15, 3.8)["target_possible"]


@pytest.mark.parametrize("entry", [
    {"credits": 0, "gpa": 3},
    {"credits": True, "gpa": 3},
    {"credits": 3, "gpa": 4.1},
    {"credits": 3, "gpa": float("inf")},
])
def test_invalid_gpa_entries_are_rejected(entry):
    with pytest.raises((ValueError, TypeError)):
        gpa_summary([entry])


def test_semester_progress_and_deadlines_include_only_unfinished_assessments():
    today = date(2026, 11, 9)
    courses = {
        "Statistics": [
            assessment("Returned quiz", 20, 0, due="2026-11-01", kind="Quiz"),
            assessment("Final", 70, due="2026-11-15", kind="Exam"),
        ],
        "Programming": [
            assessment("Project", 40, due="2026-11-09", kind="Project"),
            assessment("Assignment", 40, due="2026-11-08", kind="Assignment"),
            assessment("Quiz", 20),
        ],
    }
    summary = semester_summary(courses, {"Statistics": 75, "Programming": 80}, today)
    assert summary["progress"] == pytest.approx(20)
    assert summary["courses"]["Statistics"]["completed_count"] == 1
    assert summary["courses"]["Statistics"]["required_average"] == pytest.approx(93.75)
    assert [(item["course"], item["name"]) for item in summary["upcoming"]] == [
        ("Programming", "Project"), ("Statistics", "Final"),
    ]
    assert [item["name"] for item in summary["overdue"]] == ["Assignment"]


def test_v3_workspace_roundtrip_preserves_planning_and_old_exports_still_load():
    courses = {"Statistics": [assessment("Exam", 60, due="2026-12-15", kind="Exam")]}
    planning = default_planning(courses)
    planning["credits"]["Statistics"] = 4
    planning["gpa_history"] = [{"name": "Spring", "credits": 12, "gpa": 3.5}]
    saved = workspace_payload(courses, {"Statistics": 85}, planning=planning)
    restored = decode_workspace_bytes(json.dumps(saved, allow_nan=False).encode())
    assert restored["version"] == 3
    assert restored == saved
    assert restored["courses"] == courses
    assert restored["planning"] == planning

    old_courses = {"Statistics": [assessment("Exam", 60)]}
    old = workspace_payload(old_courses)
    assert old["version"] == 2
    assert decode_workspace_bytes(json.dumps(old).encode()) == old


@pytest.mark.parametrize("change", ["invalid_date", "unknown_course", "invalid_history"])
def test_bad_v3_payload_cannot_enter_session(change):
    courses = {"Statistics": [assessment("Exam", 60, due="2026-12-15", kind="Exam")]}
    saved = workspace_payload(courses, planning=default_planning(courses))
    if change == "invalid_date":
        saved["courses"]["Statistics"][0]["due"] = "2026-02-30"
    elif change == "unknown_course":
        saved["planning"]["credits"]["Unknown"] = 3
    else:
        saved["planning"]["gpa_history"] = [{"name": "Spring", "credits": 12, "gpa": 5}]
    with pytest.raises(ValueError):
        decode_workspace_bytes(json.dumps(saved).encode())

def test_required_score_handles_exact_maximum_and_already_reached_targets():
    records = [assessment("Midterm", 80, 75), assessment("Final", 20)]
    exact = required_assessment_score(records, 1, target=80)
    assert exact["required_score"] == pytest.approx(100)
    assert exact["target_possible"]
    reached = required_assessment_score(records, 1, target=50)
    assert reached["required_score"] == 0
    assert reached["target_possible"]


def test_gpa_scale_rejects_invalid_points_and_unknown_grades():
    with pytest.raises(ValueError):
        points_for_grade("A", {"maximum": 4, "points": {"A": 4.5}})
    with pytest.raises(ValueError):
        points_for_grade("B", {"maximum": 4, "points": {"A": 4}})


def test_no_assessments_means_no_completion_rate():
    summary = semester_summary({"Statistics": []}, {"Statistics": 75}, date(2026, 11, 9))
    assert summary["progress"] is None
    assert summary["assessment_count"] == 0
    assert summary["courses"]["Statistics"]["completed_average"] is None
