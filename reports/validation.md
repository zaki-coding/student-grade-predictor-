# Local validation record

Executed on **6 November 2026**, Windows 11 build 26300, Python **3.13.3**, in the project virtual environment.

- `python -m pytest -q`: **74 passed in 8.08 seconds**, no skips or failures.
- `python -m compileall -q src app`: completed successfully.
- `python -m pip check`: **No broken requirements found**.

The test suite covers exact grade arithmetic, incomplete and invalid weights, impossible targets, configurable thresholds, strict prediction schemas, explicit missing-value inference, trusted artifact loading and compatibility rejection, scenario deltas, source checksums, disjoint reproducible splits, training-only preprocessing, conformal order statistics, local JSON import validation, all five Streamlit sections, course creation/deletion, repeated assessment saves, prediction submission, scenario controls and calculator availability when models are missing.

The full Streamlit suite required execution outside the restricted sandbox because its asyncio runtime creates local socket pairs. Initial sandbox runs were interrupted while blocked on socket accept; this was an environment restriction. The first complete elevated run found a real Model Insights pandas API bug (`Series.reset_index(names=...)`), which was fixed to use `rename_axis(...).reset_index()`. The final complete run above passed after that fix.

Resolved validation packages: Streamlit **1.67.0**, Plotly **6.9.0**, pandas **3.1.1**, NumPy **2.5.4**, scikit-learn **1.8.0**, joblib **1.6.0**, pytest **9.2.0**. The experiment manifest records training versions and exact split indices. The lead separately repeated training in this virtual environment and observed identical selected models and reported metrics.

GitHub Actions is configured for Windows/Ubuntu and Python 3.11/3.13, but **remote CI has not run** because no changes have been pushed. This local Windows run does not claim that all CI platforms have already passed. No public deployment was performed.

## Lead integration review

- Re-ran `python -m src.train` inside the isolated virtual environment; early and updated metrics matched the initial training run exactly (all reported floating-point values).
- Re-ran `python -m compileall -q src app`, `python -m pip check`, and `git diff --check`: successful.
- Started the actual server on loopback `127.0.0.1:8501` and reviewed it in a browser.
- Visually checked overview, calculator, submitted early prediction, changed study-time scenario, model tables, diagnostics, distributions, missing counts and correlations.
- Reviewed overview at 390x844 and default desktop viewport. Corrected fixed card height causing desktop text spill, then visually verified text fits. This final change affects CSS only.
- Saved actual browser captures to `docs/screenshots/`. No model results were fabricated.
- The user approved keeping this writable clone as the working location. The original OneDrive folder remains unchanged.
- Repository remains on local `codex/student-success-ai` with original history preserved. No commits, pushes, repository visibility changes or public deployment were performed.
