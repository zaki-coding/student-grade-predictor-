# Modeling methodology and model card — iteration 2

## Scope, data and timing

The UCI Student Performance data (Cortez, 2008; [DOI 10.24432/C5TG7T](https://doi.org/10.24432/C5TG7T)) describes two Portuguese secondary schools. Only 649 Portuguese-language course records are used, avoiding the known cross-subject student overlap that pooling mathematics and Portuguese can create. The pinned source CSV has 33 columns, zero missing cells and zero identical full rows. Reliable student IDs are unavailable: distinct full rows do not prove student independence. The original data retain CC BY 4.0; download attribution and SHA256 provenance are preserved. Personal calculator records never enter training.

G3, the final-period grade, is a bounded 0–20 regression target. Early inputs are age, parental education, travel-time category, study-time category, past-failure code, internet access and higher-education aspiration. Updated schema also accepts G1/G2. G3 is never a predictor, and ambiguously timed full-year absences are excluded. These restricted predictors differ from the published benchmark. Survey collection timing does not establish a prospective early prediction date; study time and intentions can evolve. Early is a retrospective proxy, not a validated early-warning deployment. Age and parental education can encode disadvantage; no fairness certification is claimed.

## What the audit found

The original preprocessing separation was sound, but the updated task lacked meaningful prior-grade baselines. Comparing only against a constant mean overstated the apparent value of learning a model once G2 is known. Iteration 2 adds median, G2 persistence and G1/G2-only linear comparisons. It also repairs model/report provenance: inference now returns the evaluation embedded in its own artifact instead of assuming separately loaded reports describe that model.

The Phase 1 test results were already inspected. This iteration preserves the original 130-row test partition for historical audit and honestly labels reuse. It is **not** a pristine holdout, and its results cannot establish a newly discovered improvement. All candidate choices and selection rules below were fixed before this iteration's test evaluation. No model selection uses calibration or test outcomes. New external or prospective data are required before release claims.

## Splits and leakage safeguards

Seed 42 creates 389 training, 130 calibration and 130 test rows, with exact indices in `split_manifest.json`. Training-only shuffled five-fold CV supplies validation. Every candidate wraps preprocessing in a scikit-learn Pipeline: numeric median imputation and scaling, categorical most-frequent imputation and one-hot encoding. Each CV clone fits its own preprocessing only on its fold's training rows. The final pipeline fits 389 rows; calibration rows remain outside fitting. All CV, calibration, test and inference points are clipped to [0,20], so the evaluated prediction procedure matches the application. G2 persistence omits scaling to preserve its original grade value. See [scikit-learn's leakage guidance](https://scikit-learn.org/1.8/common_pitfalls.html).

The model schema is validated before inference. Target, extra fields, missing keys, nonfinite numbers, fractional ordinal codes and invalid categories/ranges are rejected. Explicit None values request training-fitted imputation. Such API support does not validate predictive accuracy under missingness; imputed active inputs produce warnings. Browser controls require complete values. Artifact loading checks schema version, feature order, actual selected preprocessing columns, active-feature metadata, nominal interval/radius consistency, reference dimensions and exact scikit-learn version. These checks detect accidental incompatibility; joblib files remain trusted executable serialization, never a security boundary.

## Candidate experiment and selection

The declared candidates, in simplicity preference order, are:

1. Mean DummyRegressor and median DummyRegressor.
2. Updated only: G2Persistence (return G2 directly), then PriorGradesLinear (G1/G2-only linear regression).
3. Full-feature LinearRegression, then Ridge with fixed alpha 1, 10, 100.
4. Original GradientBoostingRegressor (100 estimators, learning rate 0.05, depth 2, minimum leaf 5) and RandomForestRegressor (250 trees, minimum leaf 3, max_features 0.8), both seed 42.

Choose the first candidate in this order whose mean CV MAE is within one standard error of the minimum CV MAE. The best candidate's fold sample standard deviation divided by sqrt(5) defines that tolerance. This is a practical simplicity heuristic, **not** a significance test: CV folds overlap in their training records. The rule follows the principle illustrated in [scikit-learn's simplicity-aware refit example](https://scikit-learn.org/stable/auto_examples/model_selection/plot_grid_search_refit_callable.html). No broad search or increased nonlinear complexity was added.

Early selects full-feature LinearRegression: CV MAE 2.083384 versus boosting 2.069948, a negligible difference compared with fold variation. Ridge(alpha=10) gives 2.077144 and does not justify a more elaborate model. Updated selects G2Persistence, which also has the lowest CV MAE 0.797003, versus 0.826353 for prior-grades linear and 0.839550 for full-feature linear. Updated accepts the backward-compatible full schema, but **only G2 affects its point estimate**. The app and reports disclose active inputs. Changes to inactive fields cannot be advertised as improvements.

## Actual historical audit results

| Stage / baseline | MAE | RMSE | R² |
|---|---:|---:|---:|
| Early selected linear |2.135139|2.805599|0.192821|
| Early mean |2.403718|3.186493|−0.041226|
| Early median |2.369231|3.142757|−0.012839|
| Updated selected G2 persistence |0.676923|1.170141|0.859591|
| Updated prior-grades-only linear |0.735755|1.161104|0.861751|

The mean and median baselines have the same test results for both tasks because their training targets are identical. Updated G2 persistence is a separate, stronger task-appropriate comparator. It improves MAE on this reused audit sample relative to Phase 1's full linear model 0.733928, but has slightly higher RMSE 1.170141 versus 1.159314. This is not proof of new generalization accuracy or added ML value.

Early linear MAE is effectively unchanged from Phase 1 boosting 2.134514. R² moves from 0.161535 to 0.192821 while uncertainty stays broad. Coarse questionnaire/background variables contain much less direct information than prior grades; early CV R² is also low. Small sample size, retrospective measurement, unobserved academic factors and rare low/zero outcomes limit the forecast. `ml_audit.json` gives descriptive error by observed target band, which was not used for tuning and is not available at inference. Honest simplification and defensible evaluation are the improvement, not an accuracy breakthrough.

## Uncertainty and its validation

Absolute residuals from 130 calibration rows set a 90% split-conformal radius using rank ceil((n+1)*0.90), without quantile interpolation. Intersect point±radius with [0,20]. This is a prediction interval for an outcome, not a confidence interval for an expected grade. Under exchangeability, conformal coverage is marginal; it is not a personal, subgroup or external-population guarantee. [Angelopoulos and Bates](https://arxiv.org/abs/2107.07511) explain the method and assumptions.

Early radius 4.493936 gives 89.23% coverage (116/130), 95% Wilson interval 82.73%–93.48%, mean width 8.983321. Updated radius 2 gives 98.46% coverage (128/130), 95% Wilson interval 94.56%–99.58%, mean width 3.984615. Discrete grades/residuals make the updated interval conservative on this audit sample. The empirical coverage uncertainty is substantial, and test reuse further limits independent interpretation.

Predeclared descriptive diagnostics split age 15–17 vs 18–22, studytime 1–2 vs 3–4, and interval midpoint below 10 vs at least 10. Wilson intervals are per-group binomial approximations, not simultaneous bounds. The early age 18–22 group has **75% coverage (21/28)**, showing that overall coverage does not assure conditional coverage. Small groups are noisy; this is a diagnostic, not a completed fairness audit. No diagnostic is used to retune interval radii. Distribution shift and unknown dependence can break the nominal assumptions.

## Input support and hypothetical scenarios

Hard schema validation handles invalid inputs. For otherwise valid inputs, a separate training-only reference reports active-feature support ranges and counts; codes seen fewer than five times are flagged. A standardized/one-hot nearest-neighbor distance compares the joint profile with training rows. Its warning threshold is the 95th percentile of training leave-one-out nearest distances. It uses no G3, calibration rows or test rows. The heuristic geometry is not a calibrated probability or a certification of in-distribution status. An unflagged input can still be unrealistic or externally inapplicable; an unusual but legitimate student may be flagged. See [scikit-learn's novelty-detection cautions](https://scikit-learn.org/stable/modules/outlier_detection.html).

Novelty checks use only the selected model's active inputs. This avoids suggesting that inactive profile fields affect G2 persistence. Warning cases keep their statistical interval but explicitly disclose that coverage is unvalidated for unusual profiles; the interval is not silently widened or treated as a guarantee.

Scenarios run one fixed pipeline twice. A changed output is a hypothetical model response, never evidence of a causal intervention. Earlier grades are historical observations; changing G2 describes an alternative history. The updated baseline returns no difference when only an inactive field changes.

## Interpretation, reproducibility and release limits

Calibration-set permutation importance (20 repeats, seed 42) measures global reliance through increased MAE after shuffling original columns. It is descriptive, not local explanation, causal influence or a significance test. Unused updated features have zero importance. Correlated inputs can share importance. Calibration explanations never select models or intervals.

Run `python -m src.train` to regenerate models, metrics, diagnostics, split manifest and audit reports. Downloaded and cached data must match the pinned SHA256. `reports/phase1/` preserves original results. Candidate CV folds, parameters and selection order are deterministic; dependency versions are recorded. Small cross-platform numerical differences remain possible. Models are not evidence for other countries, schools, university grading systems or future cohorts. Before public release, obtain a new cohort and verify prospective timing, subgroup errors, interval calibration and educational utility. Preserve a fresh locked evaluation set for that work.
