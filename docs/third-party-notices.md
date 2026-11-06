# Third-party notices

Original project code is MIT licensed (see `LICENSE`). No third-party images, icons, fonts, or stock assets are bundled. Interface icons use Unicode text.

The UCI Student Performance dataset and its derived data summaries require CC BY 4.0 attribution; see [data-card.md](data-card.md). The reviewed source CSV and frozen derived evaluation/prediction snapshots bundled in `resources/` retain that attribution; runtime verifies their checksums. Full research training can generate ignored local model artifacts, but the application never loads them.

Dependencies are installed separately and keep their upstream licenses: NumPy, pandas and scikit-learn (BSD family); joblib (BSD 3-Clause); Streamlit (Apache 2.0); Plotly.py (MIT); pytest (MIT). Dependencies can carry additional vendored notices; retain those when redistributing installed environments. This project does not relicense dependency code or the UCI dataset under MIT.
