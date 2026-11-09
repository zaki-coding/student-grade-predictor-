# Running and deploying the app

## Local and hosted entry points

Run `python -m src.local` after installing dependencies. The launcher binds to `127.0.0.1:8501` by default. Set a different local port with `--port 8502`.

Streamlit Community Cloud uses `app/Home.py` as the entry point. The [public app](https://student-success-ai-zaki.streamlit.app/) was set up from `main` on Python 3.13.18. Dependencies are declared in `pyproject.toml` and installed through the root `requirements.txt`. The hosted platform manages the listener.

## Prediction setup

At first use, the app verifies the bundled dataset, approved metrics and predictions, recipe checksums, and the pinned scikit-learn version. It then fits the approved early linear regression and G2 persistence recipes on the original training rows and calibrates the intervals on the original calibration rows. The historical audit predictions are checked for parity after fitting.

The process cache holds public model resources. The app does not load pickle or joblib files, download models, or require a local research dataset. If model setup fails, the academic tools remain available. Check the bundled resources and dependency versions before retrying. Checksums detect inconsistent files inside the reviewed source checkout. They cannot protect a deployment whose source and expected hashes can both be changed by an attacker.

The historical training command, `python -m src.train`, regenerates the older research reports and writes ignored joblib files. Use a separate checkout when reproducing the historical run so the tracked reports in your working copy stay intact. The version 3 development command, `python -m src.development_evaluation`, reads bundled data and prints its results without writing files.

## After a deployment change

1. Open the app while signed out. Load the synthetic workspace and check the dashboard, planner, grade scenarios, and GPA.
2. Try the CSV imports, JSON restore, and report downloads. Repeat the main workflows at a narrow width.
3. Run both prediction stages and check the historical metrics and warnings. Test the What-If Lab with synthetic profiles.
4. Check the [privacy notice](privacy.md). Keep Streamlit's normal XSRF and CORS protections enabled.

The previous release's hosted and CI checks are recorded in [release validation](release-validation.md). For Community Cloud setup, see Streamlit's [deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [dependency guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).
