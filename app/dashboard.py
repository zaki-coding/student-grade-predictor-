"""Semester overview built from the student's saved records."""

from datetime import date, timedelta

import pandas as pd
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
            "Course": name, "Current average (%)": _percent(row["completed_average"]),
            "Target status": status,
            "Target (%)": targets[name], "Earned contribution": _percent(row["contribution"]),
            "Completed weight (%)": _percent(row["completed_weight"]),
            "Required remaining average (%)": _percent(row["required_average"]),
            "Highest possible (%)": _percent(row["maximum_final"]),
            "Credits": credits[name],
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
        "Completed weight (%)": st.column_config.ProgressColumn(
            "Graded weight", min_value=0, max_value=100, format="%.1f%%"),
    })
    st.caption("The current average uses completed work. Earned points are already banked. "
               "The highest possible grade assumes full marks on all remaining weight, including unallocated weight.")
    if not any(row["completed_weight"] > 0 for row in courses.values()):
        st.info("Record an assessment mark in the planner to see your current grade.")
    else:
        fig = go.Figure()
        for label, field, color in [
            ("Earned", "contribution", PALETTE[0]),
            ("Still available", "remaining_weight", "#475569"),
        ]:
            fig.add_bar(y=list(courses), x=[row[field] for row in courses.values()],
                        orientation="h", name=label, marker_color=color,
                        hovertemplate="%{y}<br>%{x:.2f} course points<extra>%{fullData.name}</extra>")
        fig.add_scatter(y=list(courses), x=[targets[name] for name in courses], mode="markers",
                        name="Target", marker=dict(symbol="diamond", size=10, color=PALETTE[3]))
        fig.update_layout(title="Reachable final grades", barmode="stack",
                          xaxis=dict(title="Course points out of 100", range=[-1, 101]),
                          height=min(850, max(310, 46 * len(courses))))
        chart(fig)


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
        count = len(unreachable)
        if count == 1:
            st.warning("One course target is out of reach with the remaining weight.")
        else:
            st.warning(f"{count} course targets are out of reach with the remaining weight.")
        st.dataframe(pd.DataFrame(unreachable, columns=["Course", "Points short even with full marks"]),
                     hide_index=True, width="stretch")
    if demands:
        st.caption("Highest averages needed on remaining work")
        st.dataframe(pd.DataFrame([(name, round(value, 2)) for name, value in demands[:3]],
                                  columns=["Course", "Required average (%)"]), hide_index=True, width="stretch")
    week_end = (today + timedelta(days=6)).isoformat()
    due_soon = [item for item in summary["upcoming"] if item["due"] <= week_end]
    if due_soon:
        highest_weight = max(due_soon, key=lambda item: item["weight"])
        st.caption("Highest-weight assessment due within seven days")
        deadline_table([highest_weight], "dashboard_heavy")
    if not (unreachable or demands or due_soon or summary["overdue"]):
        if summary["undated"]:
            st.caption("Add due dates to unfinished work in the planner to see weekly priorities.")
        else:
            st.caption("No outstanding target or dated assessment needs attention here.")


def _deadlines(summary, open_course):
    st.subheader("Assessment deadlines")
    overdue = len(summary["overdue"])
    if overdue:
        message = "One assessment is overdue." if overdue == 1 else f"{overdue} assessments are overdue."
        st.warning(message)
        deadline_table(summary["overdue"], "dashboard_overdue")
    if summary["upcoming"]:
        next_due = summary["upcoming"][0]
        st.caption(f"Next due · {next_due['due']}")
        deadline_table(summary["upcoming"][:3], "dashboard_upcoming")
        if len(summary["upcoming"]) > 3:
            st.caption("The semester planner lists the rest of your dated assessments.")
    else:
        st.info("No upcoming assessments have a due date.")
    queue = summary["overdue"] or summary["upcoming"] or summary["undated"]
    if queue:
        course = queue[0]["course"]
        st.button(f"Open {course} in the planner", on_click=open_course, args=(course, "Semester Planner"))
    undated = len(summary["undated"])
    if undated == 1:
        st.caption("One unfinished assessment still needs a date.")
    elif undated:
        st.caption(f"{undated} unfinished assessments still need dates.")


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


def dashboard(courses, targets, thresholds, planning, open_course):
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
    _deadlines(summary, open_course)
    _course_progress(summary, targets, credits)
    _priorities(summary, targets, today)
    _gpa_history(planning["gpa_history"], current_gpa, planning["gpa_scale"]["maximum"])
    a, b = st.columns(2)
    a.download_button("Download semester summary (CSV)", semester_summary_csv(courses, targets, credits, today),
                      file_name="student-success-semester-summary.csv", mime="text/csv")
    b.download_button("Download grade summary (CSV)", course_summary_csv(courses, targets, planning),
                      file_name="student-success-grade-summary.csv", mime="text/csv", key="dashboard_csv")
