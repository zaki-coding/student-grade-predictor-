"""Render each product section through Streamlit's actual test runtime."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("page", ["Overview", "Grade Calculator", "AI Predictor", "What-If Lab", "Model Insights"])
def test_sections_render_without_exceptions(page):
    app = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=30).run()
    assert not app.exception
    app.radio(key="page").set_value(page).run()
    assert not app.exception
    assert app.title or app.markdown


def test_calculator_creates_then_deletes_course():
    app = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=30).run()
    app.radio(key="page").set_value("Grade Calculator").run()
    next(widget for widget in app.text_input if widget.label == "New course name").set_value("Statistics")
    next(widget for widget in app.button if widget.label == "Add course").click().run()
    assert not app.exception
    assert "Statistics" in app.session_state["courses"]
    assert app.selectbox(key="course_select").value == "Statistics"
    next(widget for widget in app.button if widget.label == "Delete course").click().run()
    assert not app.exception
    assert "Statistics" not in app.session_state["courses"]
    assert app.selectbox(key="course_select").value == "My first course"


def test_overview_navigation_button_opens_calculator():
    app = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=30).run()
    app.button(key="open_Grade Calculator").click().run()
    assert not app.exception
    assert app.radio(key="page").value == "Grade Calculator"


def test_calculator_stays_available_when_models_unavailable(monkeypatch):
    import src.predict as inference

    def unavailable(*args, **kwargs):
        raise FileNotFoundError("Model unavailable. Run python -m src.train")

    monkeypatch.setattr(inference, "load_bundle", unavailable)
    app = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=30).run()
    app.radio(key="page").set_value("AI Predictor").run()
    assert not app.exception
    assert any("unavailable" in info.value.lower() for info in app.info)
    app.radio(key="page").set_value("Grade Calculator").run()
    assert not app.exception
    assert len(app.metric) >= 3


def test_assessment_edits_save_repeatedly_and_update_exact_contribution():
    import hashlib

    app = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=30).run()
    app.radio(key="page").set_value("Grade Calculator").run()
    digest = hashlib.sha256(b"My first course").hexdigest()[:12]
    for revision, mark, contribution in [(0, 80.0, "24.0 / 100"), (1, 90.0, "27.0 / 100")]:
        app.session_state[f"assessments_{digest}_{revision}"] = {
            "edited_rows": {0: {"mark": mark}}, "added_rows": [], "deleted_rows": []}
        next(widget for widget in app.button if widget.label == "Save assessments").click().run()
        assert not app.exception
        assert app.session_state["courses"]["My first course"][0]["mark"] == mark
        assert next(widget for widget in app.metric if widget.label == "Earned contribution").value == contribution


@pytest.mark.integration
def test_prediction_submit_and_scenario_match_saved_inputs():
    if not (ROOT / "models" / "updated.joblib").exists():
        pytest.skip("Train artifacts first: python -m src.train")
    app = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=30).run()
    app.radio(key="page").set_value("AI Predictor").run()
    app.radio(key="prediction_stage").set_value("updated").run()
    app.number_input(key="predict_updated_G2").set_value(16)
    next(widget for widget in app.button if widget.label == "Estimate final grade").click().run()
    assert not app.exception
    saved = app.session_state["last_prediction"]
    assert saved["values"]["G2"] == 16
    assert 0 <= saved["result"]["prediction"] <= 20
    assert any(widget.label == "Estimated final grade" for widget in app.metric)
    app.radio(key="page").set_value("What-If Lab").run()
    app.radio(key="scenario_stage").set_value("updated").run()
    assert not app.exception
    assert app.number_input(key="original_updated_G2").value == 16
    assert next(widget for widget in app.metric if widget.label == "Model difference").value == "+0.00 points"
    app.number_input(key="adjusted_updated_G2").set_value(18).run()
    assert not app.exception
    assert app.dataframe
