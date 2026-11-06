"""Student Success AI: Streamlit entry point. Run from any working directory."""

from __future__ import annotations

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
from app.persistence import workspace_payload, decode_workspace_bytes
from src.exports import course_summary_csv, prediction_report
from app.components import PALETTE, apply_style, chart, header, prediction_result, reliability_messages

st.set_page_config(page_title="Student Success AI", page_icon="🎓", layout="wide")

PAGES = ["Overview", "Grade Calculator", "AI Predictor", "What-If Lab", "Model Insights"]
apply_style()


def ensure_workspace():
    st.session_state.setdefault("courses", {"My first course": [
        {"name": "Coursework", "weight": 30.0, "mark": None},
        {"name": "Final assessment", "weight": 70.0, "mark": None}]})
    st.session_state.setdefault("targets", {})
    st.session_state.setdefault("thresholds", {"A":90,"B":80,"C":70,"D":60,"F":0})
    for name in st.session_state["courses"]:
        st.session_state["targets"].setdefault(name, 70.0)


def navigate(page):
    st.session_state["page"] = page


def replace_session_workspace(clean):
    """Apply an already validated workspace only to the current visitor session."""
    st.session_state["courses"] = clean["courses"]
    st.session_state["targets"] = clean["targets"]
    st.session_state["thresholds"] = clean["thresholds"]
    for key in list(st.session_state):
        if key in {"threshold_editor", "last_prediction"} or key.startswith(("target_", "scenario_", "assessments_", "assessment_form_")):
            st.session_state.pop(key, None)
    st.session_state["course_select"] = next(iter(clean["courses"]))
    st.session_state["editor_revision"] = st.session_state.get("editor_revision", 0) + 1


def load_demo_workspace():
    try:
        payload = (ROOT / "docs" / "example-workspace.json").read_bytes()
        clean = decode_workspace_bytes(payload)
    except (OSError, ValueError):
        st.session_state["workspace_notice"] = "The demo workspace could not be loaded. Your current workspace was kept."
        return
    replace_session_workspace(clean)
    st.session_state["workspace_notice"] = "Loaded the synthetic demo workspace for this session. These are demonstration marks, not real student records."


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
        clean=workspace_payload(st.session_state["courses"],st.session_state["targets"],values)
        st.session_state["thresholds"]=clean["thresholds"]
    except (ValueError,TypeError,AttributeError):
        pass  # Retain last valid thresholds; show the error beside the editor.


def delete_course(course):
    courses = st.session_state["courses"]
    if len(courses) > 1:
        del courses[course]
        st.session_state["targets"].pop(course, None)
        digest=hashlib.sha256(course.encode()).hexdigest()[:12]
        st.session_state.pop(f"target_{digest}",None)
        st.session_state.pop(f"scenario_{digest}",None)
        st.session_state["course_select"] = next(iter(courses))


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


def dashboard():
    courses, targets = st.session_state["courses"], st.session_state["targets"]
    summaries = [(name, calculate(records, targets[name])) for name,records in courses.items()]
    completed = sum(item[1]["completed_weight"] > 0 for item in summaries)
    a,b,c = st.columns(3)
    a.metric("Courses in your workspace", str(len(courses)))
    b.metric("Courses with recorded marks", str(completed))
    c.metric("Targets within mathematical reach", f"{sum(r['target_possible'] for _,r in summaries)} / {len(courses)}")
    st.subheader("Your course dashboard")
    st.caption("EXACT ARITHMETIC • Percentages based on saved assessments. No machine learning is used here.")
    if not completed:
        st.info("Your workspace is ready. Open the Grade Calculator, record an assessment mark, then save to see your progress here. "
                "Blank marks mean unfinished work; they are never treated as achieved zeroes.")
    else:
        rows=[]
        for name,r in summaries:
            rows.append({"Course":name,"Target (%)":targets[name],"Earned contribution":round(r["contribution"],2),
                         "Completed weight (%)":r["completed_weight"],"Required remaining average (%)":
                         None if r["required_average"] is None else round(r["required_average"],2),
                         "Target feasible":r["target_possible"]})
        st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch")
        fig=go.Figure()
        fig.add_trace(go.Bar(y=[n for n,_ in summaries],x=[r["contribution"] for _,r in summaries],
                            orientation="h",name="Earned contribution",marker_color=PALETTE[0]))
        fig.add_trace(go.Scatter(y=[n for n,_ in summaries],x=[targets[n] for n,_ in summaries],mode="markers",
                                marker=dict(symbol="diamond",size=12,color=PALETTE[3]),name="Target"))
        fig.update_layout(title="Earned grade points and course targets", xaxis=dict(title="Course percentage points",range=[0,100]),
                          height=max(280,70*len(summaries)))
        chart(fig)
    st.download_button("Download grade summary (CSV)",course_summary_csv(courses,targets),
                       file_name="student-success-grade-summary.csv",mime="text/csv",key="dashboard_csv")
    st.caption("Save your workspace from the Grade Calculator to retain courses, targets and grading thresholds between sessions.")


def overview():
    header("YOUR ACADEMIC ANALYTICS WORKSPACE", "Make every assessment count.",
           "A clearer view of where you stand, what comes next, and what the data can tell you.")
    st.button("Load Demo Workspace", key="load_demo", type="primary", on_click=load_demo_workspace)
    st.caption("One click loads synthetic demonstration courses. This replaces this session's courses, targets and grading thresholds; export your current workspace first.")
    if st.session_state.get("workspace_notice"):
        st.info(st.session_state.pop("workspace_notice"))
    dashboard()
    st.markdown('''<div class="hero"><div class="eyebrow">STUDENT SUCCESS AI</div>
    <h2>Know your grades.<br>Explore your possibilities.</h2>
    <p>Plan with precise grade calculations, explore statistical estimates, and inspect the evidence
    behind every model. Three distinct tools, one transparent workspace.</p></div>''', unsafe_allow_html=True)
    cols = st.columns(3)
    cards = [
        ("01 / EXACT CALCULATION", "Grade Calculator", "Organize courses, track assessment contributions, and work out the average mark needed for your target."),
        ("02 / STATISTICAL ESTIMATE", "AI Predictor", "Estimate final Portuguese-course grades with a reproducible model and a calibrated prediction interval."),
        ("03 / HYPOTHETICAL COMPARISON", "What-If Lab", "Adjust supported inputs to see how model outputs differ. Explore scenarios without assuming cause and effect."),
    ]
    for col, (tag, title, body) in zip(cols, cards):
        with col:
            st.markdown(f'<div class="card"><span class="tag">{tag}</span><h3>{title}</h3><p>{body}</p></div>', unsafe_allow_html=True)
            st.button(f"Open {title}", key=f"open_{title}", width="stretch",
                      on_click=navigate, args=(title,))
    st.divider()
    left, right = st.columns([1.3, 1])
    with left:
        st.subheader("Evidence you can inspect")
        st.write("The Model Insights page exposes the dataset, validation approach, measured errors, "
                 "and global feature importance. Predictions retain the dataset’s original 0–20 scale.")
        st.caption("Research demonstration • Historical data from two Portuguese secondary schools • Not validated for your university")
    with right:
        st.subheader("Understand where inputs go")
        st.write("Course records, targets and grading thresholds live in temporary server memory for your current app session. Export a versioned workspace JSON file to save them "
                 "on your device, then import it when you return. On a hosted instance, inputs are sent to the app server and hosting provider; use synthetic data for public demonstrations.")


def calculator_page():
    header("EXACT CALCULATION", "Your grades, clearly calculated.",
           "Track assessment weights and find the average mark needed across your remaining work.")
    st.caption("Local runs process entries on your machine. Hosted instances send them to the app server and hosting provider; use synthetic grades when trying a public demonstration.")
    courses = st.session_state["courses"]
    with st.expander("Manage courses & local files"):
        a, b = st.columns(2)
        with a:
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
                        st.session_state["course_select"] = name
                        st.rerun()
        with b:
            st.download_button("Export all courses (JSON)",
                               json.dumps(workspace_payload(courses,st.session_state["targets"],st.session_state["thresholds"]), indent=2, allow_nan=False),
                               file_name="student-success-courses.json", mime="application/json")
            st.caption("Uploads are processed in server session memory. On hosted instances, the file is transmitted to the host. Use synthetic data for public demos. Maximum workspace size: 1 MB.")
            uploaded = st.file_uploader("Import a course export", type="json")
            if st.button("Import and replace current courses", disabled=uploaded is None):
                try:
                    clean = decode_workspace_bytes(uploaded.getvalue())
                    replace_session_workspace(clean)
                    st.rerun()
                except (ValueError, TypeError, KeyError, UnicodeError):
                    st.error("Import rejected: use a supported JSON workspace no larger than 1 MB with valid grades and weights. Your current workspace was kept.")
        st.caption("Export before closing the app. Version 2 saves courses, targets and grading thresholds. Older course exports can be restored too. Import replaces the current workspace after validation.")
    course = st.selectbox("Course", list(courses), key="course_select")
    top_a, top_b = st.columns([4, 1])
    with top_a:
        st.caption("Add a row with the + control. Select a row to delete it. Leave a mark blank for unfinished work.")
    with top_b:
        st.button("Delete course", disabled=len(courses) == 1,
                  on_click=delete_course, args=(course,))
    frame = pd.DataFrame(courses[course], columns=["name", "weight", "mark"])
    # Explicit numeric dtype keeps an all-empty marks column editable as numbers.
    for field in ["weight", "mark"]:
        frame[field] = pd.to_numeric(frame[field], errors="coerce").astype(float)
    revision = st.session_state.get("editor_revision", 0)
    course_key = hashlib.sha256(course.encode()).hexdigest()[:12]
    with st.form(f"assessment_form_{course_key}_{revision}"):
        edited = st.data_editor(frame, num_rows="dynamic", hide_index=True, width="stretch",
            key=f"assessments_{course_key}_{revision}", column_config={
                "name": st.column_config.TextColumn("Assessment", required=True),
                "weight": st.column_config.NumberColumn("Weight (%)", min_value=0, max_value=100, step=1, required=True),
                "mark": st.column_config.NumberColumn("Achieved mark (%)", min_value=0, max_value=100, step=1),
            })
        save_assessments = st.form_submit_button("Save assessments", type="primary")
    records = []
    for row in edited.to_dict("records"):
        records.append({"name": row["name"], "weight": row["weight"],
                        "mark": None if pd.isna(row["mark"]) else row["mark"]})
    if save_assessments:
        try:
            candidate_courses = {**courses, course: records}
            clean = workspace_payload(candidate_courses, st.session_state["targets"], st.session_state["thresholds"])
            courses[course] = clean["courses"][course]
            st.session_state["editor_revision"] = revision + 1
            st.rerun()
        except (ValueError, TypeError) as exc:
            st.error(f"Assessments were not saved: {exc}")
    st.caption("Save your assessment edits to update calculations and include them in your export.")
    records = courses[course]
    target = st.slider("Target final grade (%)", 0.0, 100.0, float(st.session_state["targets"].get(course,70)), step=0.5, key=f"target_{course_key}", on_change=update_target, args=(course,f"target_{course_key}"))
    st.session_state["targets"][course] = float(target)
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
    st.caption("The required average applies to the combined weight of every unfinished assessment, including "
               "any weight you have not allocated yet. It does not require the same mark on every assessment.")
    if result["unallocated_weight"] > 0:
        st.warning(f"{result['unallocated_weight']:.1f}% of the course is not assigned to assessments yet. "
                   "It is included in the remaining weight above.")
    st.subheader("Plan your remaining assessments")
    if result["remaining_weight"] > 0:
        assumed = st.slider("Assumed average on remaining work (%)",0,100,70,key=f"scenario_{course_key}")
        scenario = project(records,assumed)
        st.metric("Scenario final grade (exact arithmetic)",f"{scenario['final_grade']:.1f}%",
                  delta=f"{scenario['final_grade']-target:+.1f} points vs target",delta_color="normal")
        st.caption("This calculation applies the assumed weighted average to every unfinished assessment and any unallocated weight. "
                   "It is a planning scenario, not a statistical forecast or a guarantee of future marks.")
        plan = pd.DataFrame({"Remaining average (%)":[40,50,60,70,80,90,100],
                             "Final course grade (%)":[project(records,x)["final_grade"] for x in [40,50,60,70,80,90,100]]})
        fig=px.line(plan,x="Remaining average (%)",y="Final course grade (%)",markers=True,title="Target scenarios for outstanding work")
        fig.add_hline(y=target,line_dash="dash",line_color=PALETTE[3],annotation_text=f"Target {target}%")
        fig.update_yaxes(range=[0,100]); chart(fig)
    else:
        st.info("This course is complete. Its final grade is the earned contribution shown above; no outstanding marks remain to plan.")
    st.download_button("Download grade summary (CSV)",course_summary_csv(courses,st.session_state["targets"]),
                       file_name="student-success-grade-summary.csv",mime="text/csv",key="calculator_csv")
    if records:
        contributions = pd.DataFrame(records)
        contributions["Earned contribution"] = contributions["weight"] * contributions["mark"].fillna(0) / 100
        chart(px.bar(contributions, x="name", y="Earned contribution", labels={"name": "Assessment"},
                     title="Completed contributions to your final grade"))
    with st.expander("Configure grading thresholds"):
        st.caption("Calculator percentages are independent of the ML dataset’s 0–20 scale. Set your own institution’s boundaries.")
        text = st.text_area("Grade boundaries (JSON: label → minimum percentage)",
                            json.dumps(st.session_state["thresholds"],indent=2), key="threshold_editor", on_change=update_thresholds)
        try:
            boundaries = json.loads(text)
            clean=workspace_payload(courses,st.session_state["targets"],boundaries)
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


def prediction_context(stage):
    st.caption("Source population: Portuguese-language students in two Portuguese secondary schools. "
               "All predictions use the original 0–20 grade scale, not percentages.")
    if stage == "early":
        st.info("Early stage excludes G1 and G2. These retrospective questionnaire variables are proxies for "
                "early information; their collection timing is not established for a prospective deployment.")
    else:
        st.info("Updated stage uses earlier assessment information after period two. Use it only after G2 is available; the controls below show the inputs actually used by the selected model.")


def prediction_page():
    header("STATISTICAL ESTIMATE", "A prediction with perspective.",
           "Enter supported inputs to estimate a final Portuguese-course grade. This is a research demonstration.")
    api = get_model_api()
    if not api:
        return
    features, specs, predict, _, load_bundle = api
    stage = st.radio("Prediction stage", ["early", "updated"], horizontal=True, format_func=str.title, key="prediction_stage")
    prediction_context(stage)
    try:
        current_bundle=prepared_bundle(load_bundle, stage)
    except (FileNotFoundError, ValueError, OSError, KeyError) as exc:
        model_help()
        return
    active=current_bundle.get("active_features",features[stage])
    if set(active)!=set(features[stage]):
        st.info("This selected model uses only " + ", ".join(specs[k]["label"] for k in active) + ". Other schema fields use compatibility defaults and do not affect this selected model.")
    if current_bundle.get("model_name")=="G2Persistence":
        st.info("The selected model is the latest-grade baseline: its point estimate equals G2. The calibrated range describes uncertainty in the final grade; the final result is not known exactly.")
    st.caption("On a hosted instance, submitted inputs are processed on the app server. Prefer synthetic inputs for public demonstrations.")
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
            st.caption("Only fields marked Used by selected model are predictors; compatibility values are not used. Model predictors are not proven causes. Reported study and travel values are category codes, not exact hours or minutes.")
        st.download_button("Download prediction report (Markdown)",prediction_report(saved["values"],result),
                           file_name=f"student-success-{stage}-prediction.md",mime="text/markdown")
    else:
        st.info("Complete the supported inputs and choose Estimate final grade. Your result will show its stage, scale, historical error and uncertainty together.")
    st.warning("Historical associations may not generalize to your school, course, or grading system. "
               "Do not use this estimate for admissions, grading, or high-stakes decisions.")


def scenario_page():
    header("HYPOTHETICAL COMPARISON", "Explore the what-ifs.",
           "Compare two valid input profiles using the same fitted model.")
    st.caption("On a hosted instance, scenario inputs are processed on the app server. Use synthetic profiles for public demonstrations.")
    api = get_model_api()
    if not api:
        return
    features, specs, _, compare_scenario, load_bundle = api
    stage = st.radio("Prediction stage", ["early", "updated"], horizontal=True, format_func=str.title, key="scenario_stage")
    prediction_context(stage)
    try:
        current_bundle=prepared_bundle(load_bundle, stage)
    except (FileNotFoundError, ValueError, OSError, KeyError) as exc:
        model_help()
        return
    active=current_bundle.get("active_features",features[stage])
    if set(active)!=set(features[stage]):
        st.info("The selected model uses only " + ", ".join(specs[k]["label"] for k in active) + ". Only these inputs are adjustable. Other schema fields use compatibility defaults and do not affect this model. Changing G2 is an alternative history, not an actionable study intervention.")
    st.warning("A changed prediction is a hypothetical model response. It does not establish that changing "
               "study habits, family background, or earlier grades will cause an improvement. "
               "Treat previous-grade changes as alternative histories, not actionable interventions.")
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
    header("TRANSPARENT BY DESIGN", "Behind the prediction.",
           "Inspect the data, measured errors, and methodological choices behind Student Success AI.")
    try:
        from src.provisioning import read_release_resources
        _, release_frame, metrics, release_predictions = read_release_resources()
    except (ImportError, ValueError, OSError):
        st.info("The approved release data could not pass its integrity checks. Model Insights is temporarily unavailable; the grade calculator remains ready to use.")
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
        st.subheader("Early versus updated: historical audit results")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("MAE and RMSE are grade-point errors (lower is better). R² compares squared error against "
                   "a constant test-set mean (higher is better; negative values are possible). "
                   "The mean baseline is supplemented below by stage-appropriate alternatives.")
        st.warning("This historical test set was already inspected in Phase 1. It is reused for auditing, not fresh evidence of prospective improvement. Model selection uses training-only validation.")
        stage = st.selectbox("Inspect a prediction stage", ["early", "updated"], format_func=str.title)
        m = metrics[stage]
        st.subheader("Meaningful baselines for this stage")
        if m.get("baselines"):
            baseline_rows=[{"Baseline":name,**values} for name,values in m["baselines"].items()]
            st.dataframe(pd.DataFrame(baseline_rows),hide_index=True,width="stretch")
        st.caption("Early baselines use training-only constant summaries. Updated baselines include persistence of G2 and a prior-grades-only linear estimate; they use information actually available at that stage.")
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
                st.caption("Group checks are descriptive and often small. They do not guarantee conditional or subgroup coverage.")
        if not release_predictions.empty:
            predictions = release_predictions
            predictions = predictions[predictions["stage"] == stage]
            left, right = st.columns(2)
            with left:
                fig = px.scatter(predictions, x="actual", y="predicted", opacity=.6,
                    labels={"actual": "Actual final grade", "predicted": "Predicted final grade"}, title="Actual versus predicted")
                fig.add_shape(type="line", x0=0, x1=20, y0=0, y1=20, line=dict(color="#9CA3AF", dash="dash"))
                fig.update_xaxes(range=[0, 20]); fig.update_yaxes(range=[0, 20])
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
        st.subheader("How the experiment is kept honest")
        st.write("One Portuguese-language dataset avoids overlapping student records across subjects. A fixed seed "
                 "creates the same training, calibration and held-out test partitions for both prediction stages. "
                 "Training-only cross-validation compares candidates with a predeclared preference for simpler models when differences are small. "
                 "Preprocessing is fitted inside each pipeline and validation fold.")
        st.write("Candidates include constant and stage-specific baselines, linear models with modest regularization, Random Forest and Gradient Boosting. "
                 "The selected pipeline is fitted on training data. Separate calibration residuals set "
                 "the 90% split conformal interval. The historical test audits the final choice and baselines; "
                 "it is not used to choose this iteration’s model, but its prior exposure limits claims of fresh evidence.")
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
    st.markdown("### 🎓 Student Success AI")
    st.caption("ACADEMIC PERFORMANCE & ANALYSIS")
    st.divider()
    page = st.radio("Workspace", PAGES, key="page", label_visibility="collapsed")
    st.divider()
    st.markdown("**Clarity before certainty.**")
    st.caption("Exact calculations · statistical estimates · hypothetical scenarios")
    st.caption("Workspace data is session-only. Export JSON to keep courses, targets and thresholds.")
    privacy_notice()

{
    "Overview": overview,
    "Grade Calculator": calculator_page,
    "AI Predictor": prediction_page,
    "What-If Lab": scenario_page,
    "Model Insights": insights_page,
}[page]()
