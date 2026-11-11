# How the app fits together

## Academic tools

`app/Home.py` starts Streamlit and owns navigation and session state. `app/dashboard.py` reads the current workspace and shows deadlines, course progress, and GPA. `app/academic_ui.py` handles planner, GPA, and individual grade scenario controls.

A workspace stores courses, their assessments, grading thresholds, and planning settings. The dashboard, planner, and grade calculator all read the same records. Each assessment has a name, weight, and optional mark, type, and due date. The GPA page also uses credit hours, grade points, and prior semesters. See the [grade and GPA formulas](academic-planning.md).

`src/calculator.py`, `src/gpa.py`, and `src/planner.py` handle the arithmetic and summaries without Streamlit. `app/persistence.py` validates version 1, 2, and 3 JSON. `src/academic_io.py` parses CSV and validates the proposed workspace before the app applies it. `src/exports.py` creates reports in memory. See the [workspace file guide](workspace-files.md).

## Prediction demo

`src/schema.py` defines the inputs. `src/provisioning.py` verifies the bundled data and approved model recipes, then prepares them in memory. `src/predict.py` validates submitted inputs and returns a point estimate, an interval, and any input warnings. `src/reliability.py` calculates those warnings and describes interval coverage.

The original `src/train.py` experiment and its historical audit are separate from model initialization. `src/development_evaluation.py` runs the version 3 development comparison and leaves the release snapshots alone. See [deployment](deployment.md) and [model evaluation](../reports/development-evaluation-v3.md).

## Tests

Run `python -m pytest`. Calculation tests use small examples, workspace tests exercise both valid and malformed files, and Streamlit AppTest covers navigation and several user flows. Model tests verify input validation, split separation, and parity with the approved historical predictions.
