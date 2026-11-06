"""Local record imports are validated atomically before session replacement."""
import copy

import pytest

from app.persistence import validate_courses


def export():
    return {"version": 1, "courses": {"Statistics": [
        {"name": "Exam", "weight": 60, "mark": 80},
        {"name": "Project", "weight": 40, "mark": None},
    ]}}


def test_export_roundtrip_preserves_unfinished_marks_without_aliasing():
    payload = export()
    result = validate_courses(payload)
    assert result == payload["courses"]
    assert result["Statistics"][1]["mark"] is None
    result["Statistics"][0]["mark"] = 0
    assert payload["courses"]["Statistics"][0]["mark"] == 80


@pytest.mark.parametrize("payload", [
    None, [], {}, {"version": True, "courses": {}},
    {"version": 2, "courses": {}}, {"version": 1, "courses": {}},
    {"version": 1, "courses": {"": []}},
    {"version": 1, "courses": {"A": []}, "unexpected": 1},
    {"version": 1, "courses": {"A": [{"name": "Exam", "weight": 100}]}},
    {"version": 1, "courses": {"A": [{"name": "Exam", "weight": 101, "mark": None}]}},
])
def test_invalid_imports_rejected(payload):
    with pytest.raises((ValueError, TypeError)):
        validate_courses(payload)


def test_second_invalid_course_does_not_mutate_first_or_input():
    payload = export()
    payload["courses"]["Invalid"] = [{"name": "Exam", "weight": 100, "mark": float("nan")}]
    before = copy.deepcopy(payload["courses"]["Statistics"])
    with pytest.raises(ValueError):
        validate_courses(payload)
    assert payload["courses"]["Statistics"] == before


def test_course_limit():
    with pytest.raises(ValueError):
        validate_courses({"version": 1, "courses": {str(i): [] for i in range(51)}})
