# Deployment and public-release checklist

**Hosted URL:** [student-success-ai-zaki.streamlit.app](https://student-success-ai-zaki.streamlit.app/). The application is **public and searchable**, deployed from `main` → `app/Home.py` using Python 3.13.18. Signed-out access, the synthetic demo workspace and both prediction stages were verified. The [GitHub repository](https://github.com/zaki-coding/student-grade-predictor-) is also **public**. Streamlit app sharing and repository visibility remain separate settings.

## How a cold process prepares predictions

The app uses the reviewed resources in `resources/`: the original small UCI Portuguese-course CSV, frozen approved evaluation/prediction snapshots, and a release manifest. Provisioning verifies pinned data/resource checksums, canonical-LF recipe hashes, schema/artifact/release versions, and the exact scikit-learn version before building anything. It constructs only the approved early Linear Regression and updated G2 persistence recipes with the existing fixed train/calibration split. Approved predictions and intervals are checked within the documented numerical tolerance; the audit outcomes are not used to fit, tune or select the model.

Initialization does not read a developer's `data/` cache or ignored `models/*.joblib` files, does not download a model, and does not deserialize pickle/joblib. It does not execute full cross-validation. Both models are cached once per server process behind a lock; failure leaves the calculator usable and can be retried after the underlying resource/configuration issue is corrected. Process restarts prepare the public resources again. Only public model resources are shared, never user workspaces or inputs.

The reviewed source repository is the trust boundary. These checks detect corruption and mismatched releases, not a malicious actor who controls the entire application and can replace its code and checksum manifest. Do not accept external model uploads or refresh manifest hashes blindly after a mismatch. Research `python -m src.train` output remains separate from the frozen release snapshots.

## Local use

Use the documented environment installation, then:

```text
python -m src.local
```

This portable launcher adds a loopback-only address and serves the app at `http://127.0.0.1:8501/`. Optional `--port 8502` selects a different local port. Shared `.streamlit/config.toml` deliberately has no fixed server address because Community Cloud manages its own listener.

## Current Community Cloud settings and public maintenance checklist

The existing deployment uses `main`, `app/Home.py` and Python **3.13.18**. Do not use the local-only launcher as the hosted entrypoint. Required dependency files are in the repository root. The app does not need credentials, model downloads or developer-local artifacts.

1. **Public access verified:** Streamlit is set to public and searchable, and a signed-out session loaded the dashboard, two synthetic demo courses and both AI prediction stages. Recheck signed-out access after material deployment changes.
2. Test the site while signed out, using **synthetic demo data**. Verify the Overview demo, calculator and targets, both prediction stages, What-If Lab, JSON workspace restore/export, CSV summaries, Markdown prediction reports, and narrow-screen layout.
3. Charts rendered interactively during hosted testing. The optional built-in Plotly **PNG chart download is unverified** after browser-automation attempts. Test it manually in a normal browser if it matters; do not label it broken without reproducing a failure.
4. Confirm the app's privacy notices clearly disclose that hosted grade inputs are processed on the app server. Recommend the synthetic demo rather than uploading private educational records.
5. **Public source verified:** The GitHub repository is public. Consider adding the hosted URL to the repository About section and pinning it on the GitHub profile. Keep model limitations and privacy notices prominent.

Leave XSRF/CORS protections enabled. The app disables Streamlit usage statistics, hides raw client exception details and limits workspace JSON uploads to 1 MB. It adds no accounts, analytics service, or persistent grade database.

Community Cloud's dependency file conventions, Python selection and repository/entrypoint setup are documented in [official dependency guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) and [deployment guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

## Validation status

The release merge commit [`e4578a6`](https://github.com/zaki-coding/student-grade-predictor-/commit/e4578a6fdc51463e1d5ff73bb5d50a5bf24333b9) passed [all four CI jobs](https://github.com/zaki-coding/student-grade-predictor-/actions/runs/42296289289); the subsequent documentation commit [also passed CI](https://github.com/zaki-coding/student-grade-predictor-/actions/runs/42304164557). Clean-install and cold-start evidence is recorded in [release validation](release-validation.md). Separately, real hosted and signed-out checks passed using synthetic data.

## Recommendation

The hosted application and source are **public** as a clearly labeled **educational research demonstration**. Recommend the synthetic workspace. Scientific gaps remain unchanged: reused audit data, retrospective predictor timing, weak early precision, small-group coverage failures, unverified external validity and no completed fairness/user study. Do not advertise personalized reliability.

Renaming the repository to `student-success-ai` would align it with the product name and improve presentation. It is optional; no automatic rename has been performed. If approved later, update README, Actions and hosted-app links after GitHub redirects are verified.
