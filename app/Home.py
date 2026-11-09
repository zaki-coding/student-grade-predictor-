"""Student Success AI: Streamlit entry point. Run from any working directory."""

from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.calculator import calculate, classify, project
from src.gpa import MAX_CREDITS
from src.planner import ASSESSMENT_KINDS, DEFAULT_CREDITS, default_planning
from app.academic_ui import gpa_page, individual_scenarios, planner_page
from app.dashboard import dashboard
from app.persistence import decode_workspace_bytes, encode_workspace_bytes, workspace_payload
from src.academic_io import import_assessments, import_courses
from src.exports import course_summary_csv, prediction_report
from app.components import PALETTE, apply_style, chart, prediction_result, reliability_messages

st.set_page_config(page_title="Student Success AI", page_icon="🎓", layout="wide")

PAGES = ["Overview", "Semester Planner", "Grade Calculator", "GPA Calculator",
         "AI Predictor", "What-If Lab", "Model Insights"]
apply_style()


def ensure_workspace():
    st.session_state.setdefault("courses", {"My first course": [
        {"name": "Coursework", "weight": 30.0, "mark": None},
        {"name": "Final assessment", "weight": 70.0, "mark": None}]})
    st.session_state.setdefault("targets", {})
    st.session_state.setdefault("thresholds", {"A":90,"B":80,"C":70,"D":60,"F":0})
    courses = st.session_state["courses"]
    defaults = default_planning(courses)
    planning = st.session_state.setdefault("planning", defaults)
    planning["credits"] = {
        name: planning["credits"].get(name, defaults["credits"][name]) for name in courses
    }
    for name in courses:
        st.session_state["targets"].setdefault(name, 70.0)


def navigate(page):
    st.session_state["page"] = page


def open_calculator(course):
    st.session_state["course_select"] = course
    navigate("Grade Calculator")


def current_workspace(courses=None, thresholds=None, planning=None):
    return workspace_payload(
        st.session_state["courses"] if courses is None else courses,
        st.session_state["targets"],
        st.session_state["thresholds"] if thresholds is None else thresholds,
        st.session_state["planning"] if planning is None else planning,
    )


def replace_session_workspace(clean, *, reset_prediction=True):
    """Apply an already validated workspace only to the current visitor session."""
    st.session_state["courses"] = clean["courses"]
    st.session_state["targets"] = clean["targets"]
    st.session_state["thresholds"] = clean["thresholds"]
    st.session_state["planning"] = clean.get("planning", default_planning(clean["courses"]))
    for key in list(st.session_state):
        if key == "threshold_editor" or key.startswith(("target_", "scenario_", "assessments_", "assessment_form_", "academic_")):
            st.session_state.pop(key, None)
    if reset_prediction:
        st.session_state.pop("last_prediction", None)
    selected = st.session_state.get("course_select") if not reset_prediction else None
    st.session_state["course_select"] = selected if selected in clean["courses"] else next(iter(clean["courses"]))
    st.session_state["editor_revision"] = st.session_state.get("editor_revision", 0) + 1


def load_demo_workspace():
    try:
        payload = (ROOT / "docs" / "example-semester.json").read_bytes()
        clean = decode_workspace_bytes(payload)
        shift = date.today() - date(2026, 11, 9)
        for assessments in clean["courses"].values():
            for assessment in assessments:
                if assessment.get("due"):
                    assessment["due"] = (date.fromisoformat(assessment["due"]) + shift).isoformat()
    except (OSError, ValueError):
        st.session_state["workspace_notice"] = "The demo workspace could not be loaded. Your current workspace was kept."
        return
    replace_session_workspace(clean)
    st.session_state["workspace_notice"] = "Loaded the sample semester with synthetic courses and marks."


def privacy_notice():
    with st.expander("Privacy: local and hosted use"):
        st.write("When you run this app locally, inputs are processed on your machine. On a hosted app, course records, uploads and prediction inputs are sent to the app server and processed by its hosting provider. Use synthetic demonstration data when exploring a public instance.")
        st.write("The app keeps workspace records, uploaded JSON and generated downloads in transient session memory. It does not intentionally write personal grades to server disk, log their contents, or put them in the shared model cache. Export your workspace before closing; a refresh or disconnected session may lose it.")
        st.write("There are no accounts, analytics trackers or third-party data collection added by this app. Hosting operators and providers may retain operational logs and transient buffers under their own policies; closing a browser is not a promise of immediate deletion. A hosted session and its download links are not a confidential grade vault. Avoid names, IDs or sensitive educational records. Downloaded files are saved to your device and should be kept private.")


def update_target(course, key):
    st.session_state["targets"][course] = float(st.session_state[key])


def update_thresholds():
    try:
        values=json.loads(st.session_state["threshold_editor"])
        clean = current_workspace(thresholds=values)
        st.session_state["thresholds"]=clean["thresholds"]
    except (ValueError,TypeError,AttributeError):
        pass  # Retain last valid thresholds; show the error beside the editor.


def delete_course(course):
    courses = st.session_state["courses"]
    if len(courses) > 1:
        del courses[course]
        st.session_state["targets"].pop(course, None)
        st.session_state["planning"]["credits"].pop(course, None)
        digest=hashlib.sha256(course.encode()).hexdigest()[:12]
        st.session_state.pop(f"target_{digest}",None)
        st.session_state.pop(f"scenario_{digest}",None)
        st.session_state["course_select"] = next(iter(courses))
        st.session_state["editor_revision"] = st.session_state.get("editor_revision", 0) + 1


def model_help():
    st.info("Predictions are temporarily unavailable because model preparation could not finish. The grade calculator is ready to use. No personal grades are used for model preparation.")
    st.caption("Retry initialization below. If the problem continues, the operator should verify the bundled release resources and supported dependency versions.")
    st.button("Retry model initialization", on_click=lambda: None, key="retry_initialization")


def prepared_bundle(load_bundle, stage):
    with st.spinner("Preparing verified prediction models (first use only)…"):
        return load_bundle(stage, ROOT / "models")


def get_model_api():
    try:
        from src.schema import FEATURES, SPECS
        from src.predict import predict, compare_scenario, load_bundle
        return FEATURES, SPECS, predict, compare_scenario, load_bundle
    except ImportError:
        model_help()
        return None


def overview():
    st.title("Semester overview")
    st.caption("Track marks, deadlines and GPA from the courses in this session.")
    actions = st.columns(3)
    for column, page in zip(actions, ("Semester Planner", "Grade Calculator", "GPA Calculator")):
        column.button(f"Open {page}", key=f"open_{page}", width="stretch",
                      on_click=navigate, args=(page,))
    with st.expander("Try a sample semester"):
        st.caption("The demo uses synthetic grades. It replaces your workspace for this session.")
        st.button("Load Demo Workspace", key="load_demo", on_click=load_demo_workspace)
    if st.session_state.get("workspace_notice"):
        st.info(st.session_state.pop("workspace_notice"))
    dashboard(st.session_state["courses"], st.session_state["targets"],
              st.session_state["thresholds"], st.session_state["planning"])


def _workspace_files():
    st.caption("Files are processed in session memory. A hosted app sends uploads to the hosting provider. Use synthetic records on public demos. File size limit: 1 MB.")
    workspace, courses, assessments = st.tabs(["Workspace JSON", "Courses CSV", "Assessments CSV"])
    with workspace:
        st.caption("Save courses, due dates and GPA settings in one file. Versions 1, 2 and 3 can be restored.")
        try:
            exported = encode_workspace_bytes(current_workspace())
        except ValueError as exc:
            st.warning(str(exc))
        else:
            st.download_button("Export all courses (JSON)", exported,
                               file_name="student-success-courses.json", mime="application/json")
        uploaded = st.file_uploader("Import a course export", type="json")
        if st.button("Import and replace current courses", disabled=uploaded is None):
            try:
                clean = decode_workspace_bytes(uploaded.getvalue())
            except ValueError as exc:
                st.error(str(exc))
            else:
                replace_session_workspace(clean)
                st.session_state["workspace_notice"] = "Workspace restored."
                st.rerun()
    with courses:
        st.caption("Add new courses. Leave credits or target blank to use 3 credit hours or a 70% target.")
        st.download_button("Download course CSV template", "course,credits,target\nStatistics,3,75\n",
                           file_name="course-template.csv", mime="text/csv")
        uploaded = st.file_uploader("Import courses (CSV)", type="csv")
        if st.button("Add courses from CSV", disabled=uploaded is None):
            _apply_csv(uploaded, import_courses, "Courses added.")
    with assessments:
        st.caption("Replace the assessments for each course listed in the file. Other courses keep their assessments. Use YYYY-MM-DD for dates and leave marks blank for unfinished work.")
        st.download_button("Download assessment CSV template",
                           "course,name,kind,due,weight,mark\nStatistics,Midterm,Exam,,40,80\nStatistics,Final exam,Exam,,60,\n",
                           file_name="assessment-template.csv", mime="text/csv")
        uploaded = st.file_uploader("Import assessments (CSV)", type="csv")
        if st.button("Replace assessments in listed courses", disabled=uploaded is None):
            _apply_csv(uploaded, import_assessments, "Assessments replaced for the listed courses.")


def _apply_csv(uploaded, importer, success_message):
    try:
        clean = importer(uploaded.getvalue(), current_workspace())
    except ValueError as exc:
        st.error(f"{exc} Your workspace was kept.")
    else:
        replace_session_workspace(clean, reset_prediction=False)
        st.session_state["workspace_notice"] = success_message
        st.rerun()


def course_editor():
    """Edit the same course records from the planner and grade calculator."""
    courses = st.session_state["courses"]
    planning = st.session_state["planning"]
    # Keep the file controls at the same position after the notice clears.
    notice = st.empty()
    if message := st.session_state.pop("workspace_notice", None):
        notice.success(message)
    with st.expander("Manage courses & local files"):
        with st.form("new_course", clear_on_submit=True):
            name = st.text_input("New course name", max_chars=100)
            if st.form_submit_button("Add course"):
                name = name.strip()
                if not name:
                    st.error("Enter a course name.")
                elif name in courses:
                    st.error("That course already exists.")
                elif len(courses) >= 50:
                    st.error("A workspace supports up to 50 courses.")
                else:
                    courses[name] = []
                    st.session_state["targets"][name] = 70.0
                    planning["credits"][name] = DEFAULT_CREDITS
                    st.session_state["course_select"] = name
                    st.session_state["editor_revision"] = st.session_state.get("editor_revision", 0) + 1
                    st.rerun()
        _workspace_files()
    course = st.selectbox("Course", list(courses), key="course_select")
    top_a, top_b = st.columns([2, 1])
    with top_a:
        st.caption("Add a row with the + control. Select a row to delete it. Leave a mark blank for unfinished work.")
    with top_b:
        st.button("Delete course", disabled=len(courses) == 1,
                  on_click=delete_course, args=(course,))
    frame = pd.DataFrame(courses[course], columns=["name", "weight", "mark", "kind", "due"])
    frame["due"] = pd.Series([date.fromisoformat(value) if pd.notna(value) else None
                              for value in frame["due"]], dtype=object)
    # Explicit numeric dtype keeps an all-empty marks column editable as numbers.
    for field in ["weight", "mark"]:
        frame[field] = pd.to_numeric(frame[field], errors="coerce").astype(float)
    revision = st.session_state.get("editor_revision", 0)
    course_key = hashlib.sha256(course.encode()).hexdigest()[:12]
    with st.form(f"assessment_form_{course_key}_{revision}"):
        saved_credits = float(planning["credits"][course])
        credit_hours = st.number_input("Credit hours", min_value=min(0.01, saved_credits),
                                       max_value=float(MAX_CREDITS), value=saved_credits, step=0.5)
        edited = st.data_editor(frame, num_rows="dynamic", hide_index=True, width="stretch",
            key=f"assessments_{course_key}_{revision}", column_config={
                "name": st.column_config.TextColumn("Assessment", required=True),
                "weight": st.column_config.NumberColumn("Weight (%)", min_value=0, max_value=100, step=0.1, required=True),
                "mark": st.column_config.NumberColumn("Achieved mark (%)", min_value=0, max_value=100, step=0.1),
                "kind": st.column_config.SelectboxColumn("Type", options=list(ASSESSMENT_KINDS)),
                "due": st.column_config.DateColumn("Due date", format="YYYY-MM-DD"),
            })
        save_assessments = st.form_submit_button("Save assessments", type="primary")
    if save_assessments:
        try:
            records = []
            for row in edited.to_dict("records"):
                record = {"name": row["name"], "weight": row["weight"],
                          "mark": None if pd.isna(row["mark"]) else row["mark"]}
                if pd.notna(row["kind"]):
                    record["kind"] = row["kind"]
                due = row["due"]
                if pd.notna(due):
                    if isinstance(due, datetime):
                        due = due.date()
                    record["due"] = due.isoformat() if isinstance(due, date) else due
                records.append(record)
            candidate_courses = {**courses, course: records}
            candidate_planning = {**planning, "credits": {**planning["credits"], course: credit_hours}}
            clean = current_workspace(courses=candidate_courses, planning=candidate_planning)
            courses[course] = clean["courses"][course]
            st.session_state["planning"] = clean["planning"]
            st.session_state["editor_revision"] = revision + 1
            st.rerun()
        except (ValueError, TypeError) as exc:
            st.error(f"Assessments were not saved: {exc}")
    st.caption("Save assessments to update grades, dates and credit hours.")
    target_key = f"target_{course_key}"
    target = st.slider("Target final grade (%)", 0.0, 100.0, float(st.session_state["targets"][course]),
                       step=0.5, key=target_key, on_change=update_target, args=(course, target_key))
    st.session_state["targets"][course] = float(target)
    return course


def calculator_page():
    st.title("Grade calculator")
    st.caption("Use assessment weights and marks to calculate your grade and plan for your target.")
    course = course_editor()
    courses = st.session_state["courses"]
    records = courses[course]
    target = st.session_state["targets"][course]
    course_key = hashlib.sha256(course.encode()).hexdigest()[:12]
    try:
        result = calculate(records, target)
    except (ValueError, TypeError) as exc:
        st.error(f"Check your assessments: {exc}")
        return
    a, b, c = st.columns(3)
    a.metric("Earned contribution", f"{result['contribution']:.1f} / 100")
    b.metric("Completed weight", f"{result['completed_weight']:.1f}%")
    c.metric("Remaining weight", f"{result['remaining_weight']:.1f}%")
    st.progress(min(max(result["completed_weight"] / 100, 0), 1), text="Assessment weight completed")
    required = result["required_average"]
    if required is None:
        st.success("All assessment weight is complete.")
        if not result["target_possible"]:
            st.warning("The final grade is below your target; there is no remaining assessment weight.")
    elif not result["target_possible"]:
        st.warning(f"This target is mathematically out of reach: it requires {required:.1f}% across "
                   f"the remaining weight. The highest possible final grade is {result['maximum_final']:.1f}%.")
    elif result["target_reached"]:
        st.success("Your completed assessments already contribute enough to meet this target.")
    else:
        st.info(f"You need a weighted average of **{required:.1f}%** across all remaining assessment weight "
                f"to finish with **{target}%**.")
    st.caption("The required average includes unfinished assessments and unallocated course weight.")
    if result["unallocated_weight"] > 0:
        st.warning(f"{result['unallocated_weight']:.1f}% of the course is not assigned to assessments yet. "
                   "It is included in the remaining weight above.")
    st.subheader("Plan your remaining assessments")
    if result["remaining_weight"] > 0:
        assumed = st.slider("Assumed average on remaining work (%)",0,100,70,key=f"scenario_{course_key}")
        scenario = project(records,assumed)
        st.metric("Scenario final grade (exact arithmetic)",f"{scenario['final_grade']:.1f}%",
                  delta=f"{scenario['final_grade']-target:+.1f} points vs target",delta_color="normal")
        st.caption("This scenario uses one average across all remaining weight.")
        plan = pd.DataFrame({"Remaining average (%)":[40,50,60,70,80,90,100],
                             "Final course grade (%)":[project(records,x)["final_grade"] for x in [40,50,60,70,80,90,100]]})
        fig=px.line(plan,x="Remaining average (%)",y="Final course grade (%)",markers=True,title="Target scenarios for outstanding work")
        fig.add_hline(y=target,line_dash="dash",line_color=PALETTE[3],annotation_text=f"Target {target}%")
        fig.update_yaxes(range=[0,100]); chart(fig)
    else:
        st.info("This course is complete. Its final grade is the earned contribution shown above; no outstanding marks remain to plan.")
    revision = st.session_state.get("editor_revision", 0)
    individual_scenarios(records, target, f"{course_key}_{revision}")
    st.download_button("Download grade summary (CSV)", course_summary_csv(courses, st.session_state["targets"],
                       st.session_state["planning"]),
                       file_name="student-success-grade-summary.csv",mime="text/csv",key="calculator_csv")
    contributions = [
        {"Assessment": f"{i + 1}. {row['name']}", "Earned course points": row["weight"] * row["mark"] / 100}
        for i, row in enumerate(records) if row["mark"] is not None
    ]
    if contributions:
        chart(px.bar(contributions, x="Assessment", y="Earned course points",
                     title="Points earned by assessment"))
    with st.expander("Configure grading thresholds"):
        st.caption("Calculator percentages are independent of the ML dataset’s 0–20 scale. Set your own institution’s boundaries.")
        text = st.text_area("Grade boundaries (JSON: label → minimum percentage)",
                            json.dumps(st.session_state["thresholds"],indent=2), key="threshold_editor", on_change=update_thresholds)
        try:
            boundaries = json.loads(text)
            clean = current_workspace(thresholds=boundaries)
            boundaries=clean["thresholds"]
            st.session_state["thresholds"] = boundaries
            if result["completed_average"] is not None:
                label = classify(result["completed_average"], boundaries)
                st.write(f"Average on completed work: **{result['completed_average']:.1f}% ({label})**")
                st.caption("This is the average on completed assessment weight, not a forecast of your final result.")
            else:
                classify(0, boundaries)  # Validate even before a mark is entered.
                st.caption("Enter a completed mark to see a grade label.")
        except (ValueError, TypeError, AttributeError) as exc:
            st.error(f"Invalid thresholds: {exc}")


HELP = {
    "studytime": "Weekly study time: 1 = <2 hours; 2 = 2–5 hours; 3 = 5–10 hours; 4 = >10 hours.",
    "traveltime": "Travel to school: 1 = <15 min; 2 = 15–30 min; 3 = 30–60 min; 4 = >60 min.",
    "Medu": "0 = none; 1 = primary (4th grade); 2 = 5th–9th grade; 3 = secondary; 4 = higher education.",
    "Fedu": "0 = none; 1 = primary (4th grade); 2 = 5th–9th grade; 3 = secondary; 4 = higher education.",
    "failures": "Past class failures, encoded by the source dataset as 0–4; 4 is its capped/other category.",
    "G1": "First-period grade on the original 0–20 scale.",
    "G2": "Second-period grade on the original 0–20 scale.",
}


def controls(features, specs, stage, prefix, defaults=None, active_features=None):
    values = {field:(defaults or {}).get(field,specs[field]["default"]) for field in features[stage]}
    columns = st.columns(2)
    for index, field in enumerate(active_features if active_features is not None else features[stage]):
        spec = specs[field]
        default = (defaults or {}).get(field, spec["default"])
        with columns[index % 2]:
            if "options" in spec:
                options = list(spec["options"])
                values[field] = st.selectbox(spec["label"], options, index=options.index(default),
                    key=f"{prefix}_{stage}_{field}", help=HELP.get(field))
            else:
                values[field] = st.number_input(spec["label"], min_value=int(spec["min"]),
                    max_value=int(spec["max"]), value=int(default), step=1,
                    key=f"{prefix}_{stage}_{field}", help=HELP.get(field))
    return values


def prediction_context(stage, model_name):
    st.caption("This demo uses Portuguese-language course records from two secondary schools. Grades are on a 0–20 scale.")
    if stage == "early":
        st.info("The early model uses background and questionnaire answers. The study did not establish when all answers were collected.")
    elif model_name == "G2Persistence":
        st.info("The updated estimate equals the second-period grade (G2). The interval shows how much the final grade may vary.")
    else:
        st.info("Use the updated stage after the second-period grade is available.")


def prediction_page():
    st.title("AI predictor")
    st.caption("Estimate the final grade for a profile from the Portuguese secondary-school dataset.")
    api = get_model_api()
    if not api:
        return
    features, specs, predict, _, load_bundle = api
    stage = st.radio("Prediction stage", ["early", "updated"], horizontal=True, format_func=str.title, key="prediction_stage")
    try:
        current_bundle = prepared_bundle(load_bundle, stage)
    except (FileNotFoundError, ValueError, OSError, KeyError):
        model_help()
        return
    prediction_context(stage, current_bundle.get("model_name"))
    active = current_bundle.get("active_features", features[stage])
    st.caption("A hosted app sends these inputs to the server. Use synthetic profiles on the public demo.")
    with st.form(f"predict_{stage}"):
        values = controls(features, specs, stage, "predict", active_features=active)
        submitted = st.form_submit_button("Estimate final grade", type="primary", width="stretch")
    if submitted:
        try:
            result = predict(values, stage, ROOT / "models")
            st.session_state["last_prediction"] = {"values": values, "stage": stage, "result": result}
        except (ValueError, OSError, TypeError, KeyError) as exc:
            st.error("The estimate could not be prepared. Check the supported input values and retry; the grade calculator remains available.")
    saved = st.session_state.get("last_prediction")
    if saved and saved["stage"] == stage:
        result = saved["result"]
        prediction_result(result)
        st.caption("Result reflects the last submitted inputs. Submit again after editing the form.")
        with st.expander("Inputs used for this estimate", expanded=False):
            active=result.get("active_features",list(saved["values"]))
            st.dataframe(pd.DataFrame([{"Input":specs[k]["label"],"Value":str(v),"Role":"Used by selected model" if k in active else "Compatibility value; not used by selected model", "Meaning":HELP.get(k,"Dataset-supported category or value")}
                                      for k,v in saved["values"].items()]),hide_index=True,width="stretch")
            st.caption("The Role column shows which inputs affect the estimate. Study time and travel time are recorded as ranges.")
        st.download_button("Download prediction report (Markdown)",prediction_report(saved["values"],result),
                           file_name=f"student-success-{stage}-prediction.md",mime="text/markdown")
    else:
        st.info("Enter a profile and choose Estimate final grade to see the estimate and its range.")
    st.warning("The prediction demo has not been validated for university grades. "
               "Do not use this estimate for admissions, grading, or high-stakes decisions.")


def scenario_page():
    st.title("What-if lab")
    st.caption("Compare how two profiles change a model estimate.")
    st.caption("On a hosted instance, scenario inputs are processed on the app server. Use synthetic profiles for public demonstrations.")
    api = get_model_api()
    if not api:
        return
    features, specs, _, compare_scenario, load_bundle = api
    stage = st.radio("Prediction stage", ["early", "updated"], horizontal=True, format_func=str.title, key="scenario_stage")
    try:
        current_bundle = prepared_bundle(load_bundle, stage)
    except (FileNotFoundError, ValueError, OSError, KeyError):
        model_help()
        return
    prediction_context(stage, current_bundle.get("model_name"))
    active = current_bundle.get("active_features", features[stage])
    st.warning("Changing an input shows how the estimate responds. The comparison cannot tell you "
               "whether changing study habits or another input would improve your grade.")
    left, right = st.columns(2, gap="large")
    last = st.session_state.get("last_prediction", {})
    defaults = last.get("values") if last.get("stage") == stage else None
    with left:
        st.subheader("Original profile")
        original = controls(features, specs, stage, "original", defaults, active)
    with right:
        st.subheader("Adjusted scenario")
        adjusted = controls(features, specs, stage, "adjusted", defaults, active)
    try:
        result = compare_scenario(original, adjusted, stage, ROOT / "models")
    except (ValueError, TypeError, OSError, KeyError) as exc:
        st.error("The scenario could not be prepared. Check the supported values and retry; the grade calculator remains available.")
        return
    if result["original"].get("warnings") or result["adjusted"].get("warnings"):
        st.subheader("Input support cautions")
        st.caption("Original profile")
        reliability_messages(result["original"])
        st.caption("Adjusted scenario")
        reliability_messages(result["adjusted"])
    a, b, c = st.columns(3)
    a.metric("Original estimate", f"{result['original']['prediction']:.1f} / 20")
    b.metric("Scenario estimate", f"{result['adjusted']['prediction']:.1f} / 20")
    c.metric("Model difference", f"{result['delta']:+.2f} points")
    labels = ["Original", "Adjusted"]
    predictions = [result["original"]["prediction"], result["adjusted"]["prediction"]]
    fig = go.Figure(go.Bar(x=labels, y=predictions, marker_color=PALETTE[:2],
        error_y=dict(type="data", symmetric=False,
            array=[result[k]["upper"]-result[k]["prediction"] for k in ["original", "adjusted"]],
            arrayminus=[result[k]["prediction"]-result[k]["lower"] for k in ["original", "adjusted"]])))
    fig.update_layout(yaxis=dict(title="Final grade (0–20)", range=[0, 20]), title="Estimates with 90% prediction intervals")
    chart(fig)
    if result["changes"]:
        st.subheader("Changed inputs")
        st.dataframe(pd.DataFrame([{"Input": specs[k]["label"], "Original": str(v[0]), "Adjusted": str(v[1])}
                                  for k, v in result["changes"].items()]), hide_index=True, width="stretch")
    else:
        st.caption("Both profiles are identical. Adjust a supported input to compare model responses.")


def insights_page():
    st.title("Model insights")
    st.caption("Review the dataset, historical evaluation and prediction limits.")
    try:
        from src.provisioning import read_release_resources
        _, release_frame, metrics, release_predictions = read_release_resources()
    except (ImportError, ValueError, OSError):
        st.info("Model insights are unavailable because the bundled files could not be verified. You can still use the planner and calculators.")
        return
    summary = {"rows": len(release_frame)}
    a, b, c = st.columns(3)
    a.metric("Dataset records", str(summary.get("rows", "See dataset")))
    b.metric("Grade scale", "0–20")
    c.metric("Prediction stages", "2")
    st.markdown("[UCI Student Performance](https://archive.ics.uci.edu/dataset/320/student+performance) · "
                "Cortez (2008) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · "
                "Portuguese-language course only")
    evaluation, data_tab, explanation = st.tabs(["Model evaluation", "Explore the dataset", "Methodology & limitations"])
    with evaluation:
        rows = []
        for stage in ["early", "updated"]:
            if stage in metrics:
                m = metrics[stage]
                rows.append({"Stage": stage.title(), "Selected model": m["selected_model"],
                    "Audit MAE": m["test"]["mae"], "Baseline MAE": m["baseline_test"]["mae"],
                    "Audit RMSE": m["test"]["rmse"], "Audit R²": m["test"]["r2"],
                    "Interval coverage": m["test"]["coverage"]})
        st.subheader("Historical audit results")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("MAE and RMSE are grade-point errors (lower is better). R² compares squared error against "
                   "a constant test-set mean (higher is better; negative values are possible). "
                   "The mean baseline is supplemented below by stage-appropriate alternatives.")
        st.warning("The original project already inspected these 130 audit records. Model selection used separate training rows.")
        stage = st.selectbox("Inspect a prediction stage", ["early", "updated"], format_func=str.title)
        m = metrics[stage]
        st.subheader("Baseline comparisons")
        if m.get("baselines"):
            baseline_rows=[{"Baseline":name,**values} for name,values in m["baselines"].items()]
            st.dataframe(pd.DataFrame(baseline_rows),hide_index=True,width="stretch")
        st.caption("The constant baselines use the mean or median training grade. Updated baselines can also use G1 or G2.")
        st.caption(m.get("evaluation_context","Historical audit sample; external validation remains outstanding."))
        st.subheader("Training cross-validation comparison")
        cv = pd.DataFrame(m["cv_results"])
        st.dataframe(cv.drop(columns=["fold_mae"],errors="ignore"), hide_index=True, width="stretch",
                     column_config={name:st.column_config.NumberColumn(format="%.3f") for name in ["mae","rmse","r2","mae_std","mae_se"]})
        if "model" in cv and "mae" in cv:
            ordered=cv.sort_values("mae",ascending=False)
            fig=go.Figure(go.Bar(y=ordered["model"],x=ordered["mae"],orientation="h",
                                error_x=dict(type="data",array=ordered["mae_se"]) if "mae_se" in ordered else None,
                                marker_color=[PALETTE[0] if name==m["selected_model"] else PALETTE[1] for name in ordered["model"]]))
            fig.update_layout(title="Training-only validation error (mean ± one standard error)",
                              xaxis_title="MAE (grade points; lower is better)",height=max(350,40*len(ordered)))
            chart(fig)
            st.caption("Teal marks the selected candidate. Fold error bars summarize variation, not independent confidence intervals.")
        if m.get("selection_rule"):
            st.info(str(m["selection_rule"]))
        diagnostics=m.get("interval_diagnostics",{})
        if diagnostics:
            with st.expander("Interval coverage diagnostics"):
                overall=diagnostics.get("overall",{})
                if overall:
                    bounds=overall.get("coverage_95ci",[0,1])
                    st.write(f"**{overall['covered']} of {overall['n']}** audit outcomes lay inside their intervals "
                             f"(**{overall['coverage']:.1%}**). The 95% Wilson interval for observed coverage is "
                             f"**{bounds[0]:.1%}–{bounds[1]:.1%}**.")
                groups=diagnostics.get("groups",{})
                if groups:
                    rows=[{"Group":name.replace("_"," "),"Records":values["n"],"Coverage (%)":round(values["coverage"]*100,1),
                           "95% lower (%)":round(values["coverage_95ci"][0]*100,1),
                           "95% upper (%)":round(values["coverage_95ci"][1]*100,1),
                           "Mean interval width":round(values["mean_interval_width"],2)} for name,values in groups.items()]
                    st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch")
                st.caption("Some groups have few records, so their observed coverage can vary widely.")
        if not release_predictions.empty:
            predictions = release_predictions
            predictions = predictions[predictions["stage"] == stage]
            left, right = st.columns(2)
            with left:
                fig = px.scatter(predictions, x="actual", y="predicted", opacity=.6,
                    labels={"actual": "Actual final grade", "predicted": "Predicted final grade"}, title="Actual versus predicted")
                fig.add_shape(type="line", x0=0, x1=20, y0=0, y1=20, line=dict(color="#9CA3AF", dash="dash"))
                fig.update_xaxes(range=[0, 20])
                fig.update_yaxes(range=[0, 20])
                chart(fig)
            with right:
                fig = px.scatter(predictions, x="predicted", y="residual", opacity=.6,
                                 title="Residuals versus predictions")
                fig.add_hline(y=0, line_dash="dash", line_color="#9CA3AF")
                chart(fig)
            chart(px.histogram(predictions, x="residual", nbins=20, title="Held-out residual distribution"))
            st.caption("Residual = actual grade − predicted grade. Positive residuals indicate underestimation.")
        importance_path = ROOT / "reports" / "importance.csv"
        if importance_path.exists():
            importance = pd.read_csv(importance_path)
            importance = importance[importance["stage"] == stage].sort_values("importance")
            chart(px.bar(importance, y="feature", x="importance", error_x="std" if "std" in importance else None, orientation="h",
                         title="Global permutation importance", labels={"importance": "Increase in MAE after shuffling", "feature": "Input"}))
            st.caption("Global importance measures model reliance across calibration records. Correlated inputs can "
                       "share importance; negative values can occur through sampling noise. This is neither an "
                       "individual explanation nor evidence of a causal effect.")
    with data_tab:
        data = release_frame
        st.subheader("Feature distributions")
        feature = st.selectbox("Dataset variable", list(data.columns), index=list(data.columns).index("G3"))
        chart(px.histogram(data, x=feature, title=f"Distribution: {feature}"))
        st.caption("Exploratory charts include the full source dataset and do not drive model selection.")
        st.subheader("Missing-value audit")
        missing = data.isna().sum().rename("Missing values").rename_axis("Variable").reset_index()
        st.write(f"Observed missing cells: **{int(missing['Missing values'].sum())}**")
        with st.expander("Missing counts by variable"):
            st.dataframe(missing, hide_index=True, width="stretch")
        numeric = data.select_dtypes(include="number")
        st.subheader("Numeric correlations")
        chart(px.imshow(numeric.corr(), color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                        aspect="auto", title="Pearson correlation (observational)"))
        st.caption("Correlation summarizes association. It does not establish causation or justify using a feature at prediction time.")
    with explanation:
        st.subheader("How the models were tested")
        st.write("One Portuguese-language dataset avoids overlapping student records across subjects. A fixed seed "
                 "creates the same training, calibration and held-out test partitions for both prediction stages. "
                 "Training-only cross-validation compares candidates with a predeclared preference for simpler models when differences are small. "
                 "Preprocessing is fitted inside each pipeline and validation fold.")
        st.write("Candidates include constant and stage-specific baselines, linear models with modest regularization, Random Forest and Gradient Boosting. "
                 "The selected pipeline is fitted on training data. Separate calibration residuals set "
                 "the 90% split conformal interval. The historical audit measures errors for the selected methods and baselines. "
                 "The version 3 comparison reused the training rows and is documented separately.")
        if "split_sizes" in metrics["early"]:
            st.write("Partition sizes:", metrics["early"]["split_sizes"])
        st.subheader("What the model cannot tell you")
        st.markdown("""
- This small historical dataset covers two Portuguese secondary schools and one subject; generalization is unproven.
- Early-stage questionnaire timing is retrospective. It is a proxy for early information, not a prospectively validated early-warning system.
- Full-year absences are excluded because they may include information unavailable at the prediction date. G3 is never an input.
- Updated candidates can use prior grades; the selected G2 persistence baseline uses only G2, with statistical uncertainty about the final result.
- Parent education and access variables may encode social inequalities. No fairness or deployment validation has been established.
- Intervals target marginal historical coverage under exchangeability. Coverage may fail under new populations or changing assessment policies.
- Grade calculations are exact arithmetic; ML predictions are estimates; scenarios describe model responses rather than causal interventions.
""")


ensure_workspace()

with st.sidebar:
    st.markdown("### Student Success AI")
    page = st.radio("Workspace", PAGES, key="page")
    st.divider()
    st.caption("Export your workspace to save it between sessions.")
    privacy_notice()

{
    "Overview": overview,
    "Semester Planner": lambda: planner_page(course_editor, open_calculator),
    "Grade Calculator": calculator_page,
    "GPA Calculator": gpa_page,
    "AI Predictor": prediction_page,
    "What-If Lab": scenario_page,
    "Model Insights": insights_page,
}[page]()
