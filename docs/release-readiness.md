# Release readiness

**Hosted app:** [student-success-ai-zaki.streamlit.app](https://student-success-ai-zaki.streamlit.app/) is deployed from `main` → `app/Home.py` on Python 3.13.18. At last confirmation, app access was **limited to specific people** and the [GitHub repository](https://github.com/zaki-coding/student-grade-predictor-) was **private**. Public access has not been verified.

**Release status:** [PR #1](https://github.com/zaki-coding/student-grade-predictor-/pull/1) was squash-merged as [`e4578a6`](https://github.com/zaki-coding/student-grade-predictor-/commit/e4578a6fdc51463e1d5ff73bb5d50a5bf24333b9). All four [merged-commit CI jobs passed](https://github.com/zaki-coding/student-grade-predictor-/actions/runs/42296289289). Release validation reported **163 passing tests** in both working and clean-install environments, plus reproduced research reports.

**Hosted checks:** The demo dashboard, calculator, both prediction stages, What-If comparison and JSON/CSV/Markdown downloads were verified using synthetic data. The optional Plotly PNG chart download remained **unverified** in browser automation; there is no confirmed app defect from that result.

**Before public release:** The owner can separately approve (1) Streamlit app public sharing and signed-out verification, and (2) making the source repository public. Keep privacy warnings visible and recommend synthetic demo data. See the [deployment checklist](deployment.md), [privacy explanation](privacy.md) and [release validation](release-validation.md).

**Scientific limits remain:** reused historical audit data, retrospective early inputs, limited early accuracy, broad intervals, subgroup coverage concerns and no prospective/external or completed fairness validation. Public hosting does not establish personalized forecasting reliability.
