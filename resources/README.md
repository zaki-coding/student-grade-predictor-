# Trusted public release resources

`student-por.csv` is the unmodified Portuguese-language course file from the UCI Student Performance dataset (649 rows). It is public research data, not visitor records.

- Citation: Cortez, P. (2008). *Student Performance* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5TG7T
- Source archive: https://archive.ics.uci.edu/static/public/320/student+performance.zip
- License: **CC BY 4.0**, https://creativecommons.org/licenses/by/4.0/ (credit must accompany redistribution).
- Raw CSV SHA-256: `a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f`.
- Changes: none to source CSV. `release-metrics.json` and `release-predictions.csv` are exact canonical-LF snapshots of the already-approved iteration2 reports from commit `73083aa`. Their measurements and methods are unchanged.

`model-release.json` binds the approved source data, evaluation snapshots, canonical-LF recipe source hashes, model names, seed, schema/artifact version and scikit-learn version. Its reviewed SHA-256 is pinned in `src/provisioning.py`. Updating it is a deliberate maintainer code-review action, never an automatic response to checksum failure. These checks detect resource or version drift within a trusted reviewed checkout; they do not replace signed distribution or protect against an attacker who can replace the whole application.

Run `python -m src.provisioning` from the repository root to verify the release and initialize both stages without any model file or network access. It fits only the existing selected recipes on the original 389 training rows, reconstructs calibration and checks parity against approved outcomes with absolute tolerance 1e-9. Audit checks are release parity assertions, not model tuning. No cross-validation/model search runs during initialization. Both bundles are cached once per process and callers receive isolated copies; visitor data is never cached. No serialized model is read. Optional `.joblib` research exports from `python -m src.train` are never loaded by the application.

The immutable snapshots keep inference independent of numerical report regeneration during research training. The full experiment remains `python -m src.train`; changes to modeling choices require a new reviewed release registry and evidence, not a silent runtime refresh.
