"""Streamlit views for course scenarios, deadlines, and GPA."""

from datetime import date
import json
import math

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components import chart
from app.persistence import workspace_payload
from src.calculator import calculate, classify, project_individual, required_assessment_score
from src.gpa import MAX_CREDITS, gpa_summary, points_for_grade, required_future_gpa
from src.planner import semester_summary


def individual_scenarios(records, target, course_key):
    """Compare individually assigned marks without changing saved assessments."""
    unfinished = {i: record for i, record in enumerate(records) if record["mark"] is None}
    if not unfinished:
        return
    with st.expander("Compare individual assessment scenarios"):
        st.caption("Enter hypothetical marks for any unfinished assessment. Blank cells and any unallocated weight use the fallback average.")
        fallback = st.number_input("Fallback average (%)", 0.0, 100.0, 70.0, step=1.0,
                                   key=f"academic_fallback_{course_key}")
        labels = ["Scenario A", "Scenario B", "Scenario C"]
        rows = [
            {"Assessment": record["name"], "Weight (%)": record["weight"],
             **dict.fromkeys(labels, float("nan"))}
            for record in unfinished.values()
        ]
        overrides = st.data_editor(
            pd.DataFrame(rows, index=list(unfinished)),
            key=f"academic_scenarios_{course_key}",
            hide_index=True, width="stretch", disabled=["Assessment", "Weight (%)"],
            column_config={
                label: st.column_config.NumberColumn(label, min_value=0, max_value=100, step=0.1)
                for label in labels
            },
        )
        scores = {label: overrides[label].dropna().to_dict() for label in labels}
        results = [project_individual(records, scores[label], fallback, target) for label in labels]
        st.dataframe(pd.DataFrame([
            {"Scenario": label, "Final grade (%)": round(result["final_grade"], 2),
             "Meets target": "Yes" if result["target_met"] else "No"}
            for label, result in zip(labels, results)
        ]), hide_index=True, width="stretch")

        st.subheader("Minimum score on one assessment")
        index = st.selectbox(
            "Assessment to solve for", list(unfinished),
            format_func=lambda i: f"{i + 1}. {unfinished[i]['name']} ({unfinished[i]['weight']:g}%)",
            key=f"academic_solve_{course_key}",
        )
        basis = st.selectbox("Use other marks from", labels, key=f"academic_basis_{course_key}")
        other_scores = {i: score for i, score in scores[basis].items() if i != index}
        requirement = required_assessment_score(records, index, other_scores, fallback, target)
        required = requirement["required_score"]
        if required is None:
            message = "This assessment has zero weight. "
            message += "The other work meets your target." if requirement["target_possible"] else "The other work falls short of your target."
            st.info(message)
        elif requirement["target_possible"]:
            # Round up to a hundredth so the displayed minimum still meets the target.
            score = min(100, math.ceil(round(required * 100, 9)) / 100)
            st.success(f"Score at least {score:.2f}% on this assessment to reach {target:g}%.")
        else:
            st.warning(f"This target is out of reach in {basis}. The assessment would need {required:.2f}%.")
        st.caption("The calculator subtracts points from recorded work and your other hypothetical marks, then divides the gap by this assessment’s weight.")


def deadline_table(records, key=None):
    if records:
        st.dataframe(pd.DataFrame([
            {"Due": item["due"], "Course": item["course"], "Assessment": item["name"],
             "Type": item.get("kind") or "Other", "Weight (%)": item["weight"]}
            for item in records
        ]), hide_index=True, width="stretch", key=key)


def planner_page(course_editor, open_calculator):
    st.title("Semester planner")
    st.caption("Manage courses, weights, due dates and marks. The grade calculator uses these same assessments.")
    courses, targets = st.session_state["courses"], st.session_state["targets"]
    credits = st.session_state["planning"]["credits"]
    summary = semester_summary(courses, targets, date.today())
    a, b, c = st.columns(3)
    a.metric("Courses", len(courses))
    b.metric("Credit hours", f"{sum(credits.values()):g}")
    c.metric("Assessments completed", f"{summary['completed_count']} / {summary['assessment_count']}")
    if summary["assessment_count"]:
        st.progress(summary["completed_count"] / summary["assessment_count"], text="Semester progress by assessment count")
    st.subheader("Deadlines")
    if summary["overdue"]:
        st.warning("Overdue and unfinished")
        deadline_table(summary["overdue"], "planner_overdue")
    if summary["upcoming"]:
        deadline_table(summary["upcoming"], "planner_upcoming")
    else:
        st.info("No upcoming deadlines. Add a due date to an unfinished assessment below.")
    st.subheader("Course progress")
    st.dataframe(pd.DataFrame([
        {"Course": name, "Credits": credits[name],
         "Assessments done": f"{result['completed_count']} / {result['assessment_count']}",
         "Completed weight (%)": round(result["completed_weight"], 1),
         "Earned points": round(result["contribution"], 1), "Target (%)": targets[name]}
        for name, result in summary["courses"].items()
    ]), hide_index=True, width="stretch")
    st.subheader("Edit courses and assessments")
    course = course_editor()
    if course is not None:
        st.button("Open this course in the grade calculator", on_click=open_calculator, args=(course,))


def _workspace_with_planning(planning):
    return workspace_payload(st.session_state["courses"], st.session_state["targets"],
                             st.session_state["thresholds"], planning)


def _edit_gpa_settings(planning):
    with st.expander("Grading scale and previous semesters"):
        st.caption("Use your university’s scale. Grade labels here match the percentage thresholds in the Grade Calculator.")
        frame = pd.DataFrame(planning["gpa_history"], columns=["name", "credits", "gpa"])
        for field in ("credits", "gpa"):
            frame[field] = pd.to_numeric(frame[field]).astype(float)
        revision = st.session_state.get("academic_gpa_revision", 0)
        with st.form(f"academic_gpa_settings_{revision}"):
            saved_maximum = float(planning["gpa_scale"]["maximum"])
            maximum = st.number_input("Maximum GPA", min_value=min(0.01, saved_maximum),
                                      max_value=100.0, value=saved_maximum, step=0.1)
            mapping = st.text_area("Grade points (JSON)", json.dumps(planning["gpa_scale"]["points"], indent=2))
            st.caption("Add one row for each previous semester. Enter credit hours and its GPA on the scale above.")
            history = st.data_editor(frame, num_rows="dynamic", hide_index=True, width="stretch",
                column_config={
                    "name": st.column_config.TextColumn("Semester", required=True),
                    "credits": st.column_config.NumberColumn("Credit hours", min_value=0, max_value=MAX_CREDITS, required=True),
                    "gpa": st.column_config.NumberColumn("Semester GPA", min_value=0, max_value=100, required=True),
                })
            save = st.form_submit_button("Save GPA settings", type="primary")
        if save:
            try:
                candidate = {**planning, "gpa_scale": {"maximum": maximum, "points": json.loads(mapping)},
                             "gpa_history": history.to_dict("records")}
                clean = _workspace_with_planning(candidate)
            except (ValueError, TypeError) as exc:
                st.error(f"GPA settings were not saved. {exc}")
            else:
                st.session_state["planning"] = clean["planning"]
                st.session_state["academic_gpa_revision"] = revision + 1
                st.rerun()


def _gpa_metric(label, summary, maximum):
    value = summary["gpa"]
    st.metric(label, "—" if value is None else f"{value:.2f} / {maximum:g}")
    st.caption(f"{summary['credits']:g} credit hours included")


def gpa_page():
    st.title("GPA calculator")
    st.caption("Grade points are weighted by credit hours. The app calculates GPA from your scale and saved or hypothetical marks.")
    planning = st.session_state["planning"]
    courses, thresholds = st.session_state["courses"], st.session_state["thresholds"]
    scale, history = planning["gpa_scale"], planning["gpa_history"]
    maximum = scale["maximum"]
    _edit_gpa_settings(planning)
    actual, projected, unfinished_credits = [], [], 0.0
    st.subheader("Current semester")
    records = []
    for course, assessments in courses.items():
        result = calculate(assessments)
        grade = min(100.0, result["contribution"]) if result["remaining_weight"] <= 1e-9 else None
        records.append({"Course": course, "Credit hours": planning["credits"][course],
                        "Final grade (%)": grade, "Hypothetical final (%)": float("nan")})
    if records:
        frame = pd.DataFrame(records)
        frame["Final grade (%)"] = frame["Final grade (%)"].astype(float)
        revision = st.session_state.get("editor_revision", 0)
        estimates = st.data_editor(
            frame, key=f"academic_gpa_estimates_{revision}", hide_index=True, width="stretch",
            disabled=["Course", "Credit hours", "Final grade (%)"],
            column_config={"Hypothetical final (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=0.1)},
        ).to_dict("records")
        st.caption("A final grade appears when all 100% of the course weight has a mark. Enter hypothetical percentages for courses still in progress.")
    else:
        st.info("Add courses in the semester planner to calculate a semester GPA.")
        estimates = []
    missing = set()
    unmapped_completed = False
    for row in estimates:
        credits, grade = row["Credit hours"], row["Final grade (%)"]
        hypothetical = pd.isna(grade)
        if hypothetical:
            unfinished_credits += credits
            grade = row["Hypothetical final (%)"]
        if pd.isna(grade):
            continue
        label = classify(grade, thresholds)
        try:
            points = points_for_grade(label, scale)
        except ValueError:
            missing.add(label)
            unmapped_completed |= not hypothetical
            continue
        entry = {"credits": credits, "gpa": points}
        if not hypothetical:
            actual.append(entry)
        projected.append(entry)
    if missing:
        st.warning("Add grade points for these labels to include the affected courses: " + ", ".join(sorted(missing)))
    semester = gpa_summary(actual, maximum)
    cumulative = gpa_summary(history + actual, maximum)
    a, b = st.columns(2)
    with a:
        _gpa_metric("Semester GPA", semester, maximum)
    with b:
        _gpa_metric("Cumulative GPA", cumulative, maximum)
    if len(projected) > len(actual):
        a, b = st.columns(2)
        with a:
            _gpa_metric("Hypothetical semester GPA", gpa_summary(projected, maximum), maximum)
        with b:
            _gpa_metric("Hypothetical cumulative GPA", gpa_summary(history + projected, maximum), maximum)
        st.caption("The hypothetical results include recorded grades and estimates entered above. Courses without either are excluded.")
    st.subheader("Plan a cumulative GPA target")
    a, b = st.columns(2)
    target = a.number_input("Target cumulative GPA", 0.0, float(maximum), min(3.0, float(maximum)),
                            step=0.01, key="academic_gpa_target")
    future_default = min(float(MAX_CREDITS), max(unfinished_credits, 0.01)) if unfinished_credits else 3.0
    future = b.number_input("Future credit hours", min_value=0.01, max_value=float(MAX_CREDITS),
                            value=future_default, step=1.0, key="academic_future_credits")
    if unmapped_completed:
        st.info("Map the completed course grades to grade points before calculating a cumulative target.")
        return
    required = required_future_gpa(history + actual, future, target, maximum)
    value = required["required_gpa"]
    if required["target_possible"]:
        displayed = min(maximum, math.ceil(round(value * 100, 9)) / 100)
        st.info(f"Average at least {displayed:.2f} / {maximum:g} over {future:g} future credit hours.")
    else:
        st.warning(f"This target would require {value:.2f} / {maximum:g} over {future:g} future credit hours.")
    st.caption("This target uses recorded GPA and credit hours. Hypothetical results are shown separately.")

