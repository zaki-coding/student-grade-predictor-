# Prediction dataset

The app uses the Portuguese-language file from UCI Student Performance. It contains 649 records from two Portuguese secondary schools. The target, G3, is the final grade on a 0–20 scale. We use one subject because the mathematics and Portuguese files can include the same students. See [Cortez (2008), Student Performance](https://doi.org/10.24432/C5TG7T) and the [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/).

| Stage | Inputs in the current method | Intended prediction time |
| --- | --- | --- |
| Early linear regression | Age, parent education, travel time, study time, past failures, internet access, and intention to pursue higher education | Before G1 and G2 are available |
| Updated G2 persistence | Second-period grade (G2) | After the second period |

G3 and full-year absences are excluded from model inputs. Full-year absences may include days after the prediction cutoff. The early questionnaire fields are retrospective. The dataset does not establish that all answers were available before the first grades. Updated research candidates may also use G1. The app's updated estimate equals G2.

Travel time and study time are category codes. The app shows their ranges with each input. Parental education ranges from 0 (none) to 4 (higher education). Past failures use the dataset's coded count. The input schema rejects out-of-range values. Missing values supplied to the prediction API are filled using training data. Accuracy and interval coverage with missing inputs have not been measured. The [data inspection](../reports/data_summary.json) records observed missingness in the source.

This is a small, historical, observational dataset. Random row splits cannot establish accuracy in future cohorts or universities. The file lacks stable student or household identifiers, and fields such as age and parent education can reflect disadvantage. The models have not been assessed for fairness or for decisions about admissions, grading, discipline, or eligibility.

See the [historical audit](../reports/ml_audit.md) and [version 3 development evaluation](../reports/development-evaluation-v3.md) for results, interval limitations, and the requirements for testing on university data. Attribution for the bundled data and reports is in [third-party notices](third-party-notices.md).
