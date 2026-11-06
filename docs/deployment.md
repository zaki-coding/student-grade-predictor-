# Deployment and first public-release checklist

This is release preparation for a research/portfolio demonstration. **No hosted deployment or repository visibility change has been performed.** Source visibility and hosted availability require separate owner approval.

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

## Community Cloud settings (after approval)

1. Review and merge the release pull request only after its CI matrix succeeds. Confirm the repository is still private until visibility is explicitly approved.
2. In Streamlit Community Cloud select the existing repository, approved branch/commit, and entrypoint **`app/Home.py`**. Do not use the local-only launcher as a hosted entrypoint.
3. Select **Python 3.13** in Advanced settings, matching the recommended tested environment. The application also has a Python 3.11 CI job. Review the provider's supported versions at deployment time.
4. Keep the root `requirements.txt` and `pyproject.toml` in the checkout. No system packages, credentials, model downloads, PowerShell session or local artifact mount is needed.
5. Leave XSRF/CORS protections enabled. The app turns off Streamlit usage statistics, hides raw client exception details and limits workspace uploads to 1 MB; it adds no analytics service.
6. Cold-start the approved build and confirm the calculator loads, both prediction stages initialize, the demo button works, and checksum/version failures produce a safe message rather than a traceback. Use synthetic data only.
7. Check target planning, What-If Lab, JSON restore/export, CSV summaries and Markdown prediction reports. Inspect desktop/mobile layouts, privacy notices and the unchanged model limitations.
8. Review provider privacy/retention settings and operator access. Do not present this anonymous demonstration as a confidential student-record service.
9. **Obtain explicit owner approval before the final public deployment or repository visibility change.** Then add the real approved hosted URL to the README; until then it remains explicitly unavailable.

Community Cloud's dependency file conventions, Python selection and repository/entrypoint setup are documented in [official dependency guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) and [deployment guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

## Validation status

The approved base commit `73083aa86a51c10c1e97eb4f77d635a6ac561b0f` passed all four [Windows/Ubuntu and Python 3.11/3.13 jobs](https://github.com/zaki-coding/student-grade-predictor-/actions/runs/42248590363). Release-branch local clean-install, cold-start, automated and browser results are recorded in [release validation](release-validation.md). A local cold-start simulation is not evidence that Streamlit Community Cloud itself has deployed successfully.

## Recommendation

A public source portfolio release is reasonable after review of this pull request, its passing CI and the privacy/claim wording. A hosted release should be labeled **educational research demonstration** and recommend the synthetic workspace. Scientific gaps remain unchanged: reused audit data, retrospective predictor timing, weak early precision, small-group coverage failures, unverified external validity and no completed fairness/user study. Do not advertise personalized reliability.

Renaming the repository to `student-success-ai` would align it with the product name and improve presentation. It is optional; no automatic rename has been performed. If approved later, update README, Actions and hosted-app links after GitHub redirects are verified.
