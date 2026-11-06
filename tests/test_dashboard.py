"""Dashboard progress and future-mark scenarios remain deterministic."""
import hashlib
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_empty_state_and_saved_course_summary():
    app = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=30).run()
    assert not app.exception
    assert any("record an assessment mark" in message.value.lower() for message in app.info)
    app.session_state["courses"] = {"Statistics": [{"name": "Exam", "weight": 50, "mark": 80}]}
    app.session_state["targets"] = {"Statistics": 75}
    app.run()
    assert not app.exception
    assert any(item.label == "Courses with recorded marks" and item.value == "1" for item in app.metric)
    frame = next(item.value for item in app.dataframe if "Course" in item.value.columns)
    assert frame.loc[0, "Earned contribution"] == 40
    assert frame.loc[0, "Required remaining average (%)"] == 70
    assert frame.loc[0, "Target (%)"] == 75


def test_target_and_threshold_settings_survive_navigation_and_change_exact_projection():
    app = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=30).run()
    app.radio(key="page").set_value("Grade Calculator").run()
    digest = hashlib.sha256(b"My first course").hexdigest()[:12]
    app.slider(key=f"target_{digest}").set_value(85).run()
    app.slider(key=f"scenario_{digest}").set_value(90).run()
    assert not app.exception
    assert app.session_state["targets"]["My first course"] == 85
    assert next(item for item in app.metric if item.label == "Scenario final grade (exact arithmetic)").value == "90.0%"
    app.text_area(key="threshold_editor").set_value('{"Pass": 50, "Fail": 0}').run()
    app.radio(key="page").set_value("Overview").run()
    app.radio(key="page").set_value("Grade Calculator").run()
    assert not app.exception
    assert app.slider(key=f"target_{digest}").value == 85
    assert app.session_state["thresholds"] == {"Pass": 50, "Fail": 0}


@pytest.mark.integration
def test_prediction_result_discloses_stage_scale_and_model_bound_metrics():
    if not (ROOT / "models" / "updated.joblib").exists():
        pytest.skip("Train artifacts first")
    app = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=30).run()
    app.radio(key="page").set_value("AI Predictor").run()
    app.radio(key="prediction_stage").set_value("updated").run()
    next(item for item in app.button if item.label == "Estimate final grade").click().run()
    assert not app.exception
    assert any(item.value == "Updated prediction result" for item in app.subheader)
    assert any(item.label == "MAE (grade points)" for item in app.metric)
    assert any("observed interval coverage" in item.value.lower() for item in app.caption)
    assert any("0–20" in item.value for item in app.caption)
    assert any(item.label == "Download prediction report (Markdown)" for item in app.get("download_button"))
