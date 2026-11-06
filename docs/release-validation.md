# Release-preparation verification

The approved base commit `73083aa86a51c10c1e97eb4f77d635a6ac561b0f` passed four [Windows/Ubuntu and Python 3.11/3.13 CI jobs](https://github.com/zaki-coding/student-grade-predictor-/actions/runs/42248590363). The following results describe this release branch, not an actual Streamlit Community Cloud deployment.

## Automated and reproducibility results

- Final working-copy release suite: **163 passed in 48.94 seconds**, no skips.
- Full research training reproduced all **seven approved numerical/audit reports byte-for-byte**, with their recorded SHA256 values unchanged. Selected methods, split indices, calibration and measured results were preserved.
- Both release models remained usable after research training regenerated its separate ignored exports.
- Byte compilation passed; `pip check` reported no broken requirements.
- Tests cover release checksums/versions, offline preparation, all 260 approved audit points/intervals, no pickle/joblib loading, arbitrary artifact rejection, concurrent exactly-once initialization, retry after failure, cache-copy and visitor-session isolation, one-click demo reset, bounded atomic JSON restore, safe errors, downloads and all existing grade calculations.

## Fresh install and cold start

A separate source snapshot was created from intended repository files with **no `models/` directory, no `data/student-por.csv`, and no existing virtual environment**. A new Python 3.13.3 environment was installed from `requirements.txt`, without system site-packages. Imported application modules were checked to resolve to the isolated checkout.

The first deeply nested environment hit a Windows package-path length limit while unpacking a bundled Streamlit template. Installation succeeded at a shorter isolated environment path. This was an installation-path issue, not a model initialization failure; the README includes the short-path guidance.

With model deserialization and network requests patched to fail, first-use initialization prepared both selected models from verified public resources. Measured initialization after Python imports took **0.370 seconds**; a warm cache-copy call took **0.005 seconds** in this one local run. These are not complete browser startup times or hosted performance guarantees.

- Early default: **12.7100401854 / 20**, interval **8.2161044679–17.2039759029**.
- Updated default: **12 / 20**, interval **10–14**.
- Fresh-environment complete suite: **163 passed in 49.23 seconds**, no skips.
- Fresh dependency and compilation checks passed.
- After the suite, no generated model directory or research-data cache had appeared. The application did not need the full research experiment or an external model download.

## Real browser verification

Launched the isolated checkout through `python -m src.local --port 8502`, bound only to loopback. Browser checks used synthetic data only:

- First landing page and one-click Load Demo Workspace populated both courses and preserved targets 76 / 82.5 and custom thresholds.
- Calculator showed Statistics contribution 38.5 and required remaining average 75%; its planning scenario displayed 73.5% at an assumed remaining average of 70%.
- Downloaded CSV values matched those exact calculations. Exported JSON retained version 2, courses, targets and thresholds; uploading and restoring it preserved the workspace.
- Both prediction stages submitted successfully, with the point estimates, intervals and model-bound historical error/coverage shown above.
- The downloaded updated prediction report included its 10–14 range, 128/130 coverage count, G2-baseline explanation and statistical limitations.
- Updated What-If comparison changed G2 from 12 to 13 and returned exactly +1.00 point.
- Model Insights loaded dataset distributions, zero-missing audit and correlations from verified bundled data without a research-data cache.
- Hosted/local privacy notice correctly disclosed server/provider transmission, transient buffers and limits to confidentiality/erasure promises.
- Desktop (1280px) and narrow (390px) layouts were visually inspected. Captures: [demo](screenshots/release/demo.jpg), [mobile](screenshots/release/mobile.jpg). This is not a formal accessibility/user study.

## Release boundary

No visibility change, repository rename, merge or public deployment was performed during these checks. PR CI is recorded by the workflow for the release branch. This local simulation cannot prove a hosted provider deployment has succeeded; the owner-approved Community Cloud cold-start smoke test remains on [the deployment checklist](deployment.md).

Scientific limitations are unchanged: reused historical audit data, retrospective input timing, broad early uncertainty, small-subgroup coverage failures and no validated external/fairness/causal claims. A public source portfolio release is reasonable after review and passing PR CI; a hosted instance should remain clearly labeled an educational demonstration and recommend synthetic data.
