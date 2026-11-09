# Version 3 development evaluation

The prediction demo still uses the approved early linear model and the updated G2 persistence baseline. This experiment compared two alternatives on the original 389 training rows from the UCI Portuguese course data. The 130 calibration rows and 130 historical audit rows were excluded from every fit and score.

## How the comparison worked

- Early, before G1 or G2 is available, compares linear regression and Huber regression against a constant median. Huber reduces the influence of large residuals during fitting.
- Updated, after G2 is available, compares G2 persistence, ordinary regression on G1 and G2, and median regression on G1 and G2 with fixed L1 regularization at 0.01. Median regression directly targets absolute error. The constant median provides a baseline with no prior-grade information.
- Each method uses the same five shuffled folds with seed 42. Imputation, encoding, and scaling are fitted inside each fold. Each row is scored using a model fitted on the other four folds. Predictions are clipped to 0–20 before scoring.
- G3 is the target. G3, full-year absences, and school are excluded as predictors. The early questionnaire inputs still have uncertain collection timing, so this is a retrospective comparison.

Run `python -m src.development_evaluation` from the repository root. It checks the bundled dataset's hash and prints the results without writing files. The run below used Python 3.13.3, scikit-learn 1.8.0, NumPy 2.5.4, and pandas 3.1.1.

## Results on development rows

| Stage | Method | MAE | RMSE | R² |
| --- | --- | ---: | ---: | ---: |
| Early | Constant median | 2.491 | 3.371 | −0.007 |
| Early | Linear regression (in app) | 2.084 | 2.934 | 0.237 |
| Early | Huber | 2.057 | 2.918 | 0.245 |
| Updated | Constant median | 2.491 | 3.371 | −0.007 |
| Updated | G2 persistence (in app) | 0.797 | 1.394 | 0.828 |
| Updated | G1/G2 linear regression | 0.826 | 1.344 | 0.840 |
| Updated | G1/G2 median regression | 0.797 | 1.394 | 0.828 |

Huber lowered pooled early MAE by 0.027 points. Updated median regression tied G2 persistence. The updated linear fit lowered RMSE but raised MAE, the comparison's primary metric. These are internal comparisons on development data used before. The small Huber difference needs confirmation in a separate cohort before a release change.

### School transfer within the dataset

Each row below was scored by a model trained on the other school's development rows. This checks how sensitive results are to leaving one school out of training. Both schools are from the same source and there are only two, so this is limited evidence about transfer to new institutions.

| Held-out school | Rows | Early linear MAE | Huber MAE | G2 persistence MAE | G1/G2 median MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| GP | 250 | 2.357 | 2.186 | 0.712 | 0.712 |
| MS | 139 | 2.808 | 2.763 | 0.950 | 0.950 |

### Where the current methods miss

These bands use the observed final grade after prediction. Negative mean residuals indicate overestimation.

| Actual G3 | Rows | Early MAE | Early mean residual | Updated MAE | Updated mean residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 12 | 10.063 | −10.063 | 3.333 | −3.333 |
| 1–9 | 57 | 2.457 | −1.821 | 0.947 | −0.105 |
| 10–20 | 320 | 1.718 | 0.710 | 0.675 | 0.525 |

In these folds the early model overestimated lower grades on average, especially zeros. The 12 zero grades are too few for a stable group estimate. These errors limit the use of the early model for detecting students likely to receive low grades.

## Historical audit and intervals

The archived audit measured MAE of 2.135 for early linear regression and 0.677 for G2 persistence. The 90% nominal intervals covered 116 of 130 early outcomes and 128 of 130 updated outcomes in that audit. Their mean widths were about 9.0 and 4.0 grade points, respectively. The early range is wide and coverage was lower in some subgroups. The intervals assume future records resemble the calibration sample. Coverage for a particular student, a university cohort, or missing inputs has not been established. Training-support checks only flag unusual inputs.

The version 3 comparison did not fit or recalibrate intervals, and it leaves the release recipes and historical reports intact. See the [historical ML audit](ml_audit.md) and [methodology](methodology.md).

## What a university dataset would need

The two reviewed UCI higher-education datasets use different outcomes: [letter-grade categories](https://archive.ics.uci.edu/dataset/856/higher+education+students+performance+evaluation) and [dropout, enrolled, or graduate status](https://archive.ics.uci.edu/dataset/697/predict+students+dropout+and+academic+success). The [Open University dataset](https://pmc.ncbi.nlm.nih.gov/articles/PMC5704676/) includes assessment scores and dates, but its documentation says final exam scores are usually missing. It is a candidate for studying timed assessment data with a separately defined target. None of these sources was used to validate the current course-grade predictor.

A future numeric course-grade study needs a licensed target with a clear grading scale, a prediction cutoff for every feature, and stable group or cohort identifiers to split by student, course, institution or term as appropriate. `compare_candidates` in `src/development_evaluation.py` already accepts a separate predictor table, a target, pipelines, a fold splitter, and grade bounds. Keep dataset parsing, feature availability, and any new calibration protocol outside the released UCI model recipes. Reserve a fresh cohort for evaluation before choosing models, then check error, interval coverage, and missingness on that cohort.
