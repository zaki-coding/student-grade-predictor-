# Release readiness

**Public demo:** [student-success-ai-zaki.streamlit.app](https://student-success-ai-zaki.streamlit.app/) is deployed from `main` → `app/Home.py` on Python 3.13.18, with **public and searchable** access. A signed-out browser session loaded the dashboard, two synthetic demo courses, the Early prediction (12.7/20) and the Updated prediction (15.0/20 with synthetic G2 = 15).

**Public source:** [zaki-coding/student-grade-predictor-](https://github.com/zaki-coding/student-grade-predictor-) has been verified **public**. [PR #1](https://github.com/zaki-coding/student-grade-predictor-/pull/1) was squash-merged as [`e4578a6`](https://github.com/zaki-coding/student-grade-predictor-/commit/e4578a6fdc51463e1d5ff73bb5d50a5bf24333b9). All four [release CI jobs passed](https://github.com/zaki-coding/student-grade-predictor-/actions/runs/42296289289). Subsequent [documentation CI passed](https://github.com/zaki-coding/student-grade-predictor-/actions/runs/42304164557). Release preparation reported **163 passing tests** in working and clean-install environments.

**Hosted checks:** Earlier authenticated testing passed the dashboard, calculator, both prediction stages, What-If comparison and JSON/CSV/Markdown downloads using synthetic data. Public signed-out testing confirmed the dashboard and both predictions. The optional built-in Plotly PNG chart download remained **unverified** in browser automation; no specific defect is established.

**Maintenance:** Keep the [deployment checklist](deployment.md), [privacy explanation](privacy.md) and [release validation](release-validation.md) current. Use synthetic demonstration data by default. Verify public accessibility and core prediction behavior after meaningful app changes.

**Scientific limits remain:** reused historical audit data, retrospective early inputs, limited early accuracy, broad intervals, subgroup coverage concerns and no prospective/external or completed fairness validation. Public hosting does not establish personalized forecasting reliability.
