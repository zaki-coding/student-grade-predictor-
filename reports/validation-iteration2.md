# Iteration 2 local validation record

Executed on **6 November 2026**, Windows, Python **3.13.3**, using the existing project virtual environment.

## Executed checks

- Final complete run after all additions: `python -m pytest -q` completed with **129 passed in 38.44 seconds**, no skips or failures.
- Initial complete iteration 2 run: `python -m pytest -q` completed with **124 passed in 26.70 seconds**, no skips or failures.
- Lead repeated complete suite: **124 passed in 35.13 seconds**, no skips or failures.
- After strengthening artifact metadata validation and report disclosure, targeted `python -m pytest tests/test_exports.py tests/test_reliability.py -q --basetemp=.pytest_qa_iteration2` completed with **24 passed in 5.14 seconds**. This includes five newly added regression cases.
- `python -m compileall -q src app` completed successfully.
- `python -m pip check` reported **No broken requirements found**.
- `git diff --check` completed without whitespace errors.

The final 129-test run includes all earlier regression tests and the five final report/artifact cases. The counts above describe executed commands, not assumed totals.

## Coverage of the suite

Existing exact-calculator, schema, missingness, artifact, dataset, split, preprocessing and Streamlit tests were retained. New checks cover:

- Version 1 course-export migration to version 2 workspace saves.
- Round-trip preservation and isolation of marks, per-course targets and grading thresholds.
- Invalid target/threshold rejection and atomic import validation.
- Exact remaining-work projections, including unallocated weight and completed courses.
- Stage-appropriate G2 persistence semantics, fold-fitted missing-G2 median, and independence from unused profile fields.
- Conservative one-standard-error selection for near ties.
- Independent interval coverage counting and known Wilson confidence bounds.
- Train-only input-support bounds, unusual joint-profile warnings, and no refitting at inference.
- Model-bound evaluation, missingness warnings, and rejection of inconsistent/outdated artifacts.
- CSV calculation correctness and spreadsheet-formula escaping for user labels.
- Prediction report disclosures: original scale, stage, fitted method, point/range, historical evaluation, limitations, active versus compatibility inputs, and observed coverage counts/confidence bounds.
- Real Streamlit runtime navigation, course creation/deletion, repeated mark saves, dashboard empty/saved states, target/threshold navigation persistence, prediction submission and what-if controls.

The complete Streamlit suite requires local socket pairs. It was run outside the restricted execution sandbox because the sandbox blocks that runtime initialization. This environment requirement is not a claim that the app needs elevated privileges on an ordinary Windows installation.

## Training reproducibility

The lead reran the complete training command and persisted [the reproducibility comparison](reproducibility-iteration2.json). All seven generated reports matched byte-for-byte: `metrics.json`, `predictions.csv`, `importance.csv`, `data_summary.json`, `split_manifest.json`, `ml_audit.json`, and `ml_audit.md`.

The experiment retains the fixed Phase 1 row splits and dataset checksum. Test results are explicitly a **reused historical audit**, not a pristine holdout or external-validation result. See [the generated ML audit](ml_audit.md) and [the model card](methodology.md) for scientific interpretation.

## Browser and download validation

The lead reviewed the running app in a real browser. Importing `docs/example-workspace.json` restored synthetic courses, targets **76 / 82.5**, and custom thresholds. The exported workspace JSON and downloaded grade-summary CSV were inspected: Statistics contributed **38.5** points and required **75%** across remaining work; Programming contributed **34** points and required **80.8333%**. These are exact calculator results, not model predictions. Actual captures are stored under `docs/screenshots/iteration2/`.

The app defaults to loopback binding (`127.0.0.1`) for local use. Browser checks are distinct from the automated test result and do not replace a formal accessibility/user study.

## Scope of claims

The configured GitHub Actions matrix targets Windows/Ubuntu and Python 3.11/3.13. Remote CI has **not** run because no changes have been pushed. This local Windows result does not establish that every CI environment passes. Browser review and screenshots are recorded by the lead; they are distinct from these automated test results. No accounts, cloud database, public deployment, repository visibility change or GitHub push was performed.

## Final lead integration review

After the interrupted tasks resumed, all completed contributions were preserved. The final complete suite passed **129 tests in 38.44 seconds**, with no skips. Compilation, dependency checks and whitespace checks passed. A final retraining after the audit-prose corrections again reproduced all seven report files byte-for-byte; all saved SHA256 values were checked against the current files.

Browser verification additionally covered the submitted updated G2 estimate (12.0/20; interval10.0–14.0), matching embedded audit error/coverage, and a G2 scenario12→13 producing exactly+1.00 point. Desktop and390px mobile layouts were inspected. Refreshed captures are in `docs/screenshots/iteration2/` (dashboard, calculator, predictor, insights, what-if and mobile).

The final server was restarted after source edits so imported Python modules matched the tested source. A newly downloaded prediction report was inspected: the point/range,128/130 coverage count, active/compatibility roles, G2-baseline explanation and corrected limitations were present. The earlier cached sentence implying that this selected G2-only model used G1 was absent. This was a stale running-process issue, not a model-selection change.

The final application is running locally on `http://127.0.0.1:8501/`, bound to loopback. The review browser was left on the updated prediction result. The synthetic example workspace is available for import; no personal records were used in these checks. No commits, pushes or public deployment were performed.
