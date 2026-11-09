"""Semester overview built from the student's saved records."""

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.academic_ui import deadline_table
from app.components import PALETTE, chart
from src.exports import course_summary_csv, semester_summary_csv
from src.gpa import course_gpa_rows, gpa_summary
from src.planner import semester_summary


def _percent(value):
    return None if value is None else round(value, 2)


def _course_progress(summary, targets, credits):
    st.subheader("Course progress")
    courses = summary["courses"]
    rows = []
    for name, row in courses.items():
        status = "Met" if row["target_reached"] else "Within reach" if row["target_possible"] else "Out of reach"
        rows.append({
            "Course": name, "Credits": credits[name], "Current average (%)": _percent(row["completed_average"]),
            "Target (%)": targets[name], "Earned contribution": _percent(row["contribution"]),
            "Completed weight (%)": _percent(row["completed_weight"]),
            "Required remaining average (%)": _percent(row["required_average"]), "Target status": status,
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("The current average uses completed work. Earned contribution is the number of points banked toward the full course.")
    if not any(row["completed_weight"] > 0 for row in courses.values()):
        st.info("Record an assessment mark in the planner to see your current grade.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Bar(y=list(courses), x=[row["completed_average"] for row in courses.values()],
                             orientation="h", name="Current average", marker_color=PALETTE[0]))
        fig.add_trace(go.Scatter(y=list(courses), x=[targets[name] for name in courses], mode="markers",
                                 name="Target", marker=dict(symbol="diamond", size=11, color=PALETTE[3])))
        fig.update_layout(title="Current averages and targets", xaxis=dict(title="Grade (%)", range=[0, 100]),
                          height=min(700, max(280, 50 * len(courses))))
        chart(fig)
    if summary["completed_count"] and summary["completed_count"] < summary["assessment_count"]:
        counts = pd.DataFrame([
            {"Course": name, "Completed": row["completed_count"],
             "Remaining": row["assessment_count"] - row["completed_count"]}
            for name, row in courses.items()
        ])
        chart(px.bar(counts, y="Course", x=["Completed", "Remaining"], orientation="h",
                     labels={"value": "Assessments"}, title="Completed and remaining assessments",
                     height=min(700, max(280, 45 * len(courses)))))


def _priorities(summary, targets, today):
    st.subheader("What needs attention")
    courses = summary["courses"]
    unreachable = sorted(
        ((name, targets[name] - row["maximum_final"]) for name, row in courses.items() if not row["target_possible"]),
        key=lambda item: -item[1],
    )
    demands = sorted(
        ((name, row["required_average"]) for name, row in courses.items()
         if row["target_possible"] and row["required_average"] and row["completed_count"]),
        key=lambda item: -item[1],
    )
    if unreachable:
        st.warning(f"{len(unreachable)} course target(s) are out of reach with the remaining weight.")
        st.dataframe(pd.DataFrame(unreachable, columns=["Course", "Points short even with full marks"]),
                     hide_index=True, width="stretch")
    if demands:
        st.caption("Highest averages needed on remaining work")
        st.dataframe(pd.DataFrame([(name, round(value, 2)) for name, value in demands[:3]],
                                  columns=["Course", "Required average (%)"]), hide_index=True, width="stretch")
    due_soon = [item for item in summary["upcoming"] if item["due"] <= (today + timedelta(days=7)).isoformat()]
    if due_soon:
        highest_weight = max(due_soon, key=lambda item: item["weight"])
        st.caption("Highest-weight assessment due within seven days")
        deadline_table([highest_weight], "dashboard_heavy")
    if not (unreachable or demands or due_soon):
        st.caption("Add marks or due dates to see course priorities.")


def _deadlines(summary):
    st.subheader("Assessment deadlines")
    if summary["overdue"]:
        st.warning(f"{len(summary['overdue'])} unfinished assessment(s) are overdue.")
        deadline_table(summary["overdue"], "dashboard_overdue")
    if summary["upcoming"]:
        deadline_table(summary["upcoming"], "dashboard_upcoming")
    else:
        st.info("No upcoming assessments have a due date.")
    dated = len(summary["upcoming"]) + len(summary["overdue"])
    undated = summary["assessment_count"] - summary["completed_count"] - dated
    if undated:
        st.caption(f"{undated} unfinished assessment(s) still need a date.")


def _gpa_metrics(grade_rows, planning):
    history = planning["gpa_history"]
    actual = [row for row in grade_rows if row["gpa"] is not None]
    maximum = planning["gpa_scale"]["maximum"]
    current = gpa_summary(actual, maximum)
    cumulative = gpa_summary(history + actual, maximum)
    a, b = st.columns(2)
    for column, label, result in [(a, "Semester GPA", current), (b, "Cumulative GPA", cumulative)]:
        value = result["gpa"]
        column.metric(label, "—" if value is None else f"{value:.2f} / {maximum:g}")
        column.caption(f"{result['credits']:g} credit hours included")
    if any(row["gpa"] is None for row in grade_rows):
        st.caption("Current GPA includes courses with a final mark and a grade label on your GPA scale.")
    return current


def _gpa_history(history, current, maximum):
    st.subheader("GPA by semester")
    terms = list(history)
    if current["gpa"] is not None:
        terms.append({"name": "Current semester", "gpa": current["gpa"], "credits": current["credits"]})
    if not terms:
        st.caption("Add prior semesters in the GPA calculator to see GPA history.")
        return
    positions = list(range(len(terms)))
    names = [row["name"] for row in terms]
    fig = go.Figure(go.Bar(
        x=positions, y=[row["gpa"] for row in terms],
        customdata=[[row["name"], row["credits"]] for row in terms],
        hovertemplate="%{customdata[0]}<br>GPA %{y:.2f}<br>%{customdata[1]} credits<extra></extra>",
    ))
    fig.update_layout(xaxis=dict(tickmode="array", tickvals=positions, ticktext=names),
                      yaxis=dict(range=[0, maximum], title=f"GPA / {maximum:g}"), height=300)
    chart(fig)


def dashboard(courses, targets, thresholds, planning):
    today = date.today()
    summary = semester_summary(courses, targets, today)
    credits = planning["credits"]
    grade_rows = course_gpa_rows(courses, credits, thresholds, planning["gpa_scale"])
    a, b, c = st.columns(3)
    a.metric("Courses", len(courses))
    b.metric("Credit hours", f"{sum(credits.values()):g}")
    c.metric("Courses with recorded marks", sum(row["completed_count"] > 0 for row in summary["courses"].values()))
    if summary["assessment_count"]:
        st.progress(summary["progress"] / 100,
                    text=f"{summary['completed_count']} of {summary['assessment_count']} assessments completed")
    current_gpa = _gpa_metrics(grade_rows, planning)
    _deadlines(summary)
    _course_progress(summary, targets, credits)
    _priorities(summary, targets, today)
    _gpa_history(planning["gpa_history"], current_gpa, planning["gpa_scale"]["maximum"])
    a, b = st.columns(2)
    a.download_button("Download semester summary (CSV)", semester_summary_csv(courses, targets, credits, today),
                      file_name="student-success-semester-summary.csv", mime="text/csv")
    b.download_button("Download grade summary (CSV)", course_summary_csv(courses, targets, planning),
                      file_name="student-success-grade-summary.csv", mime="text/csv", key="dashboard_csv")

