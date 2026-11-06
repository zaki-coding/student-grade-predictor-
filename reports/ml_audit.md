# Iteration 2 machine-learning audit

This report is generated from the measured run. The 130-row historical test was already inspected in Phase 1; it is an audit set, not pristine evidence of improvement.

## Results

| Stage | Selected | MAE | RMSE | R² | Coverage | 95% Wilson interval |
|---|---|---:|---:|---:|---:|---|
| early | LinearRegression | 2.135139 | 2.805599 | 0.192821 | 89.23% | 82.73%–93.48% |
| updated | G2Persistence | 0.676923 | 1.170141 | 0.859591 | 98.46% | 94.56%–99.58% |

## Audit findings

- **target_leakage:** G3 excluded from all features and support heuristics; earlier grades only updated.
- **preprocessing:** All imputers/encoders/scalers fit inside each training CV fold; final fit 389 training rows.
- **separation:** 389 train, 130 calibration, 130 test, no shared row indices. Same fixed splits as Phase 1.
- **test_reuse:** Historical test already examined in Phase 1. No selection on this test, but not a fresh independent confirmation.
- **validation:** Five-fold training CV for all candidates, one-standard-error simplicity heuristic; folds correlated so SE is not a formal significance test.
- **baseline_gap_fixed:** Early mean/median; updated G2 persistence and G1/G2-only linear added beside mean/median.
- **timing:** Questionnaire timing cannot prove prospective early availability. Full-year absences excluded.
- **input_support:** Strict domain/schema rejection plus training-only active-feature support and nearest-neighbor warning heuristic.
- **unresolved:** No student IDs or temporal/external cohort. Random row split cannot establish independence, transportability or fairness.

## Early-model investigation

Early coarse background predictors contain limited information without prior grades. Ridge does not materially improve CV error; complexity is not justified. Target-band residuals are descriptive and were not used for tuning.

| Observed target band | Test count | MAE | Mean actual−predicted residual |
|---|---:|---:|---:|
| G3=0 | 2 | 9.599853011251081 | -9.599853011251081 |
| G3=1..9 | 13 | 2.6540340464085617 | -1.6164627368426143 |
| G3=10..20 | 115 | 1.9466606628430647 | 0.7698367526303829 |

The target-band breakdown uses observed outcomes solely to describe error after evaluation. It is not available at inference and does not define model inputs.

Updated G2Persistence is intentionally a transparent baseline: the point equals G2. Other accepted profile fields do not affect its estimate. The calibration residual radius is 2 grade points; discrete grades make the nominal 90% interval conservative on this audit sample. A learned model should not be advertised as adding value over this baseline.

Early linear MAE is virtually unchanged from Phase 1 boosting (2.135139 vs 2.134514), while R² is 0.192821 vs 0.161535. These small, reused-sample differences do not establish improved generalization. The benefit is simpler modeling and more honest comparison.

## Before release

Obtain a truly new prospective/external cohort; assess input timing, subgroup errors and interval coverage; preserve a fresh locked evaluation set. Novelty warnings cannot replace those checks.
