"""Exercise the academic pages through Streamlit's test runner."""

import hashlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
COURSE_KEY = hashlib.sha256(b"My first course").hexdigest()[:12]


def app():
    return AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=30).run()


def test_planner_saves_deadline_and_shares_marks_with_calculator():
    visitor = app()
    visitor.radio(key="page").set_value("Semester Planner").run()
    assert not visitor.exception
    visitor.session_state[f"assessments_{COURSE_KEY}_0"] = {
        "edited_rows": {0: {"mark": 80, "kind": "Project"}, 1: {"kind": "Exam", "due": "2090-12-10"}},
        "added_rows": [], "deleted_rows": [],
    }
    next(widget for widget in visitor.number_input if widget.label == "Credit hours").set_value(4.0)
    next(widget for widget in visitor.button if widget.label == "Save assessments").click().run()
    assert not visitor.exception
    assert visitor.session_state["planning"]["credits"]["My first course"] == 4
    assert visitor.session_state["courses"]["My first course"][1]["due"] == "2090-12-10"
    assert any("2090-12-10" in frame.value.get("Due", []).tolist()
               for frame in visitor.dataframe if "Due" in frame.value)
    next(widget for widget in visitor.button if widget.label == "Open this course in the grade calculator").click().run()
    assert not visitor.exception
    assert visitor.radio(key="page").value == "Grade Calculator"
    assert next(widget for widget in visitor.metric if widget.label == "Earned contribution").value == "24.0 / 100"
    assert any("65.72%" in message.value for message in visitor.success)


def test_gpa_includes_completed_and_prior_credits_without_hypothetical_marks():
    visitor = app()
    visitor.session_state["courses"] = {"Statistics": [{"name": "Exam", "weight": 100, "mark": 90}]}
    visitor.session_state["planning"] = {
        "credits": {"Statistics": 3},
        "gpa_scale": {"maximum": 4, "points": {"A": 4}},
        "gpa_history": [{"name": "Last semester", "credits": 9, "gpa": 3}],
    }
    visitor.radio(key="page").set_value("GPA Calculator").run()
    assert not visitor.exception
    metrics = {widget.label: widget.value for widget in visitor.metric}
    assert metrics["Semester GPA"] == "4.00 / 4"
    assert metrics["Cumulative GPA"] == "3.25 / 4"
    visitor.number_input(key="academic_gpa_target").set_value(4.0).run()
    assert any("would require 7.00" in message.value for message in visitor.warning)

