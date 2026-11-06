"""Portable reports with explicit arithmetic/ML boundaries; no server file writes."""
import csv
import io
import math
from numbers import Real

from src.calculator import calculate


def _spreadsheet_text(value):
    """Prevent user labels being interpreted as spreadsheet formulas."""
    value = str(value)
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def course_summary_csv(courses, targets=None):
    from app.persistence import workspace_payload
    workspace = workspace_payload(courses, targets)
    output = io.StringIO(newline="")
    fields = ["Course", "Target (%)", "Earned contribution (points / 100)",
              "Completed weight (%)", "Completed average (%)", "Remaining weight (%)",
              "Required remaining average (%)", "Maximum final (%)", "Target possible",
              "Unallocated weight (%)", "Calculation basis"]
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(fields)
    for name, records in workspace["courses"].items():
        target = workspace["targets"][name]
        result = calculate(records, target)
        def number(value):
            return "" if value is None else round(value, 6)
        writer.writerow([_spreadsheet_text(name), target, number(result["contribution"]),
            number(result["completed_weight"]), number(result["completed_average"]),
            number(result["remaining_weight"]), number(result["required_average"]),
            number(result["maximum_final"]), result["target_possible"],
            number(result["unallocated_weight"]),
            "Exact arithmetic; remaining average includes unfinished and unallocated weight; no ML prediction"])
    return output.getvalue()


def _md(value):
    text = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for character in ("\\", "`", "*", "_", "[", "]", "|", "#"):
        text = text.replace(character, "\\" + character)
    return text.replace("\r", " ").replace("\n", " ")


def _finite(value, name, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f"{name} is outside the valid range.")
    return float(value)


def prediction_report(values, result):
    """Export the submitted prediction and its embedded evaluation, never live reports.

    Report accuracy belongs to the exact fitted artifact that generated the result.
    Missing or old evaluation metadata is disclosed rather than invented.
    """
    from src.schema import SPECS, validate_inputs
    if not isinstance(result, dict):
        raise ValueError("Supply a prediction result.")
    stage = result.get("stage")
    frame = validate_inputs(values, stage)
    point = _finite(result.get("prediction"), "Prediction", 0, 20)
    lower = _finite(result.get("lower"), "Interval lower bound", 0, 20)
    upper = _finite(result.get("upper"), "Interval upper bound", 0, 20)
    if not lower <= point <= upper:
        raise ValueError("Prediction must lie within its interval.")
    nominal = result.get("nominal_coverage")
    interval_title = "Prediction interval" if nominal is None else f"{_finite(nominal, 'Nominal coverage', 0, 1):.0%} nominal prediction interval"
    lines = ["# Student Success AI — Prediction report", "",
        "**Statistical estimate — not an exact course-grade calculation.**", "",
        f"- Prediction stage: **{stage.title()}**",
        f"- Estimated final grade: **{point:.2f} / 20**",
        f"- {interval_title}: **{lower:.2f}–{upper:.2f} / 20**",
        f"- Fitted model: {_md(result.get('model_name', 'Unavailable'))}",
        "- Dataset scale: original Portuguese-course grade **0–20**, not a percentage.", "",
        "## Evaluation attached to this model", "",
        _md(result.get("evaluation_context", "Historical evaluation metadata unavailable; retrain the local model.")), ""]
    evaluation = result.get("evaluation") or {}
    test = evaluation.get("test") or {}
    if all(key in test for key in ("mae", "rmse", "r2")):
        lines += [f"- Audit MAE: {test['mae']:.3f} grade points",
                  f"- Audit RMSE: {test['rmse']:.3f} grade points",
                  f"- Audit R²: {test['r2']:.3f}"]
    if "coverage" in test:
        lines.append(f"- Observed audit interval coverage: {test['coverage']:.1%}")
    if "mean_interval_width" in test:
        lines.append(f"- Mean audit interval width: {test['mean_interval_width']:.3f} grade points")
    overall = (evaluation.get("interval_diagnostics") or {}).get("overall", {})
    bounds = overall.get("coverage_95ci")
    if bounds is not None:
        lines.append(f"- 95% Wilson confidence interval for measured coverage: {bounds[0]:.1%}–{bounds[1]:.1%}")
    if "n" in overall and "covered" in overall:
        lines.append(f"- Audit outcomes covered by the interval: {overall['covered']} / {overall['n']}")
    if not test:
        lines.append("Measured evaluation is unavailable in this result; no accuracy claim is made.")
    baselines = evaluation.get("baselines") or {}
    if baselines:
        lines += ["", "Stage-appropriate comparison baselines:", ""]
        for name, metrics in baselines.items():
            lines.append(f"- {_md(name)}: MAE {metrics['mae']:.3f}, RMSE {metrics['rmse']:.3f}, R² {metrics['r2']:.3f}")
    active = result.get("active_features", list(frame.columns))
    if result.get("model_name") == "G2Persistence":
        lines += ["", "The selected baseline uses G2 unchanged as its point estimate. It does not fit a complex model to predict improvement; the interval is calibrated from historical final-grade residuals."]
    lines += ["", "## Input profile", "", "Only active inputs affect the selected point estimate. Other fields are retained for schema compatibility and may be defaults.", "",
              "| Input | Dataset value/code | Role |", "| --- | --- | --- |"]
    for field in frame.columns:
        value = "Missing — training-fitted imputation" if values[field] is None else values[field]
        role = "Active model input" if field in active else "Unused compatibility field"
        lines.append(f"| {_md(SPECS[field]['label'])} | {_md(value)} | {role} |")
    lines += ["", "## Reliability notices", ""]
    warnings = result.get("warnings") or []
    for warning in warnings:
        lines.append(f"- {_md(warning)}")
    if not warnings:
        lines.append("No heuristic input warning was triggered. This does not establish that the profile is in-distribution or that the estimate is accurate.")
    lines += ["", "## Limitations", "",
        "- Historical observational data from two Portuguese secondary schools; not validated for your institution or future cohort.",
        "- Split conformal intervals target marginal coverage under exchangeability, not a personal or subgroup guarantee. Distribution shift can invalidate coverage.",
        "- The benchmark test has already been inspected in development. Reused audit results are not fresh independent evidence of improvement.",
        "- Early questionnaire timing is retrospective; early prediction is a proxy, not a prospectively validated warning system. The updated stage supports prior grades; only the active inputs listed above affect this selected model.",
        "- Input-support checks are heuristics; plausible ranges do not guarantee realistic combinations. Accuracy and coverage under missing inputs have not been validated.",
        "- Inputs and global importance describe association, not causal effects. Scenario changes cannot promise grade improvements.",
        "- This report must not be used for admissions, disciplinary action, grading or other high-stakes decisions.",
        "- This download includes the submitted profile. Store it privately.", ""]
    return "\n".join(lines)
