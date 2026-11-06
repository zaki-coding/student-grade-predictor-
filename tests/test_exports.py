"""Downloads must disclose uncertainty and must not turn course names into formulas."""
import csv
import io

import pytest


def test_grade_summary_contains_exact_target_calculations():
    from src.exports import course_summary_csv
    courses = {"Statistics": [{"name": "Quiz", "weight": 20, "mark": 80},
                              {"name": "Exam", "weight": 80, "mark": None}]}
    rows = list(csv.DictReader(io.StringIO(course_summary_csv(courses, {"Statistics": 76}))))
    assert len(rows) == 1
    flattened = " ".join(rows[0].values())
    assert "Statistics" in flattened
    # Course contributed 16 points; a 76 target needs 75 across its remaining 80%.
    numbers = []
    for value in rows[0].values():
        try:
            numbers.append(float(value))
        except ValueError:
            pass
    for expected in [16, 76, 75, 80]:
        assert expected in numbers


@pytest.mark.parametrize("name", ["=SUM(1,2)", "+cmd", "-1+2", "@formula", "\t=1+1", "\r=1+1", "\n=1+1"])
def test_course_name_formula_injection_is_escaped(name):
    from src.exports import course_summary_csv
    text = course_summary_csv({name: []}, {name: 70})
    row = next(csv.DictReader(io.StringIO(text)))
    name_value = next(value for value in row.values() if name.strip() in value)
    assert name_value.startswith("'"), "Spreadsheet-active names must be prefixed with an apostrophe"


def profile():
    from src.schema import FEATURES, SPECS
    return {field: SPECS[field]["default"] for field in FEATURES["updated"]}


def result():
    return {
        "prediction": 12.5, "lower": 10.1, "upper": 14.9, "stage": "updated",
        "model_name": "ExampleRegression", "nominal_coverage": .9,
        "warnings": ["Unusual input profile; uncertainty is not validated for this profile."],
        "reliability": {"status": "caution"},
        "evaluation_context": "Reused historical audit set, not fresh external validation.",
        "evaluation": {"test": {"mae": .8, "rmse": 1.2, "r2": .7, "coverage": .88,
                                  "mean_interval_width": 4.8},
                       "baseline_test": {"mae": 2.4, "rmse": 3.2, "r2": -.04},
                       "baselines": {"G2Persistence": {"mae": .9, "rmse": 1.3, "r2": .6}}},
    }


def test_prediction_report_retains_inputs_stage_and_validated_uncertainty():
    from src.exports import prediction_report
    report = prediction_report({**profile(), "G1": 11, "G2": 12, "studytime": 3}, result())
    lowered = report.lower()
    for expected in ["Updated", "ExampleRegression", "12.5", "10.1", "14.9", "First-period", "Second-period", "Weekly study"]:
        assert expected in report
    assert "90" in report and "88" in report
    assert "0" in report and "20" in report and "scale" in lowered
    assert "mae" in lowered and "rmse" in lowered
    assert "reused historical audit" in lowered
    assert "unusual input" in lowered
    assert "guarantee" in lowered and "caus" in lowered


def test_prediction_report_uses_embedded_evaluation_not_current_files(monkeypatch):
    from pathlib import Path
    from src.exports import prediction_report

    def forbidden(*args, **kwargs):
        raise AssertionError("Report export must use the result-bound evaluation snapshot")

    monkeypatch.setattr(Path, "read_text", forbidden)
    report = prediction_report(profile(), result())
    assert "12.5" in report


def test_latest_grade_report_distinguishes_active_input_from_compatibility_fields_and_coverage_count():
    from src.exports import prediction_report
    report_result = result()
    report_result["model_name"] = "G2Persistence"
    report_result["active_features"] = ["G2"]
    report_result["evaluation"]["interval_diagnostics"] = {
        "overall": {"n": 130, "covered": 128, "coverage_95ci": [.9456415, .9957708]}}
    report = prediction_report(profile(), report_result)
    assert "G2 unchanged" in report
    assert "95% Wilson" in report
    assert "94.6%" in report and "99.6%" in report
    assert "128 / 130" in report
    active_rows = [line for line in report.splitlines() if "| Active model input |" in line]
    assert len(active_rows) == 1 and "Second-period" in active_rows[0]
    unused_rows = [line for line in report.splitlines() if "| Unused compatibility field |" in line]
    assert len(unused_rows) == len(profile()) - 1
    assert any("Weekly study" in line for line in unused_rows)
