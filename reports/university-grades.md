# Forecasting the next assessment and the next semester

Two university archives support different questions. At the Open University, a forecast one week before a tutor-marked assignment averaged **12.97 points of absolute error out of 100**. Carrying forward the last available mark averaged **13.13**. At the Polytechnic Institute of Portalegre, a forecast made after semester one averaged **0.72 points of error out of 20** among students with a usable semester-two average. Carrying forward the first-semester average gave **0.79**.

Both experiments stay in the research part of the repository. The first depends on an unverified assumption about when feedback arrived. The second requires knowing which students eventually had a reportable average to interpret its accuracy. Neither study establishes performance at another university, including UDST.

## Open University assignments

Kuzilek, Hlosta and Zdrahal released OULAD under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It covers seven distance-learning modules. The archive documents deadlines, submission days, transferred marks and daily clicks. It contains 28,785 distinct students and 173,912 student-assessment records. Assignment and student identifiers link tables within the archive. [UCI dataset and citation](https://doi.org/10.24432/C5KK69)

**What was predicted.** Seven days before each dated tutor-marked assignment, estimate the eventual mark for a submission still outstanding. Each prediction concerns that scheduled assignment. Exams and computer-marked work are outside the task. Of 98,426 records for dated tutor-marked assignments, 1,338 had marks carried over from an earlier presentation. Another 172 lacked a mark. Removing 6,810 submissions already made on or before the cutoff left 90,106 eligible observations across all four presentations. A recorded zero is a grade. An absent submission has no observed target. Errors therefore describe eventual submitters and cannot answer who will submit.

| Input | Availability rule |
| --- | --- |
| Last mark, mean mark and count of earlier assignments | Same student, module and presentation. A mark qualifies only when 28 days after the **later** of its deadline and submission falls strictly before the cutoff. “Last” means the most recent qualifying assignment by scheduled deadline. |
| Recent learning activity | Sum of clicks for that student in the same module and presentation over the 14 complete days before the cutoff. No recorded clicks in that window gives zero. |
| No eligible prior grade | Count is zero. The persistence baselines use the training target median. Fitted models impute missing features from their training partition and include missingness indicators. |

Submission time is recorded, but feedback time is unknown. The 28-day delay is a proxy. The clicks-only comparison shows what the model could do without assuming access to any grades. The target submission day determines eligibility during evaluation. Neither that day, target marks, student IDs, final course outcomes nor future clicks enter the predictor.

**Splits.** Train on February 2013, choose the learned model and the baseline separately by October 2013 validation MAE, then refit on both partitions and evaluate on October 2014. To allow time for grading before the next partition, training labels must have reached their assumed release by day 180 and validation labels by day 320. February 2014 overlaps the test presentation and is excluded. When a student appears in several partitions, retain their later partition and drop earlier observations. This prevents student overlap but changes the mix of returning students in development.

| Partition | Students | Scheduled assessments | Scored submissions |
| --- | ---: | ---: | ---: |
| Training | 3,564 | 13 | 11,990 |
| Validation | 6,369 | 29 | 24,734 |
| Test | 7,884 | 32 | 29,362 |

Errors below weight each scored submission equally. MAE is the mean absolute miss in grade points. RMSE gives larger misses more weight. The selection rule used only validation MAE. The table includes all fixed comparisons so the effect of adding clicks is visible.

| Method | Validation MAE | Validation RMSE | Test MAE | Test RMSE |
| --- | ---: | ---: | ---: | ---: |
| Training median | 12.86 | 17.10 | 15.15 | 20.22 |
| Last available mark | 11.12 | 15.16 | 13.13 | 18.59 |
| Mean of available marks | 10.94 | 15.01 | 14.19 | 19.66 |
| Linear regression, grade history | 11.34 | 14.70 | 13.25 | 18.29 |
| Linear regression, history and clicks | 11.32 | 14.58 | 13.05 | 18.01 |
| Histogram gradient boosting, grade history | 11.18 | 14.66 | 13.25 | 18.32 |
| Histogram gradient boosting, history and clicks | 10.99 | 14.29 | 12.97 | 17.97 |
| Histogram gradient boosting, clicks only | 12.49 | 16.01 | 14.75 | 19.38 |

Adding clicks lowered test MAE by 0.28 points for boosting. The prior mean beat every learned model on validation but deteriorated on the test presentation. The learned model's test MAE was 1.22 points lower than that validation-selected baseline (paired 95% bootstrap interval for model minus baseline, −1.30 to −1.15). Its lead over the last-mark baseline on the same test data was only 0.16. For 12,277 test submissions, the delay rule left no usable earlier mark.

| Test module | Submissions | Prior mean MAE | History + clicks MAE | Same model trained on other modules only, MAE |
| --- | ---: | ---: | ---: | ---: |
| AAA | 1,445 | 8.91 | 8.94 | 9.03 |
| BBB | 6,428 | 22.02 | 18.49 | 18.43 |
| CCC | 4,061 | 13.45 | 13.15 | 13.15 |
| DDD | 6,445 | 13.04 | 12.43 | 12.71 |
| EEE | 3,033 | 13.13 | 11.85 | 12.17 |
| FFF | 6,639 | 10.63 | 10.11 | 10.34 |
| GGG | 1,311 | 10.16 | 9.50 | 9.62 |

For the last column we refit the selected model after excluding the test module from both development partitions. CCC was already absent from those partitions. Even within one institution, a single pooled error understates the misses in BBB. The data offer only one final presentation. Confirmed mark-release dates and another held-out presentation would make a stronger test. [Full OULAD results, including per-module RMSE](oulad-evaluation.json)

## Portalegre semester averages

Realinho, Vieira Martins, Machado and Baptista published 4,424 student records under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Each row is one student. Admission information precedes enrollment, and academic summaries are produced at the end of each semester. This experiment predicts the recorded second-semester average on a 0–20 scale. Individual assessment results are unavailable. This is a separate task from OULAD. [UCI dataset](https://doi.org/10.24432/C5MC89) · [Authors’ data description](https://www.mdpi.com/2306-5729/7/11/146)

**Prediction time.** After semester one closes, use admission grade (0–200) and six first-semester fields: the average grade and counts of credited units, enrolled units, evaluations, approved units and units without evaluations. A first-semester average of zero coincided with zero approved units in all 718 such cases. Treat that average as unavailable. Eight held-out students needed this fallback. The course code identifies reporting groups only. All second-semester fields, eventual dropout status, demographic fields, and administrative or financial status are excluded from the inputs.

**Whose grade is observable.** All 870 students with a zero second-semester average had zero approved units. Of those, 469 had at least one evaluation and 401 had none. The records cannot distinguish a meaningful numeric semester average for these groups. The target therefore requires a positive recorded average and at least one approved unit. Positive averages ranged from 10.00 to 18.57. Eventual dropout status is used below only to audit who was excluded.

| Eventual status | Usable average | Excluded | Coverage |
| --- | ---: | ---: | ---: |
| Dropout | 694 | 727 | 48.8% |
| Enrolled | 726 | 68 | 91.4% |
| Graduate | 2,134 | 75 | 96.6% |
| All | 3,554 | 870 | 80.3% |

Split eligible students once into training (2,132), validation (711) and test (711) with seed 42. There is one row per student, with no entry-year field for a later-cohort test. All preprocessing was fit on training data for validation and on combined training and validation data for the final test. The first-semester baseline uses the training target median when that student's first average is unavailable.

| Method | Validation MAE | Validation RMSE | Test MAE | Test RMSE |
| --- | ---: | ---: | ---: | ---: |
| Training median | 1.10 | 1.39 | 1.09 | 1.36 |
| First-semester average | 0.79 | 1.08 | 0.79 | 1.06 |
| Linear regression | 0.76 | 1.00 | 0.75 | 0.97 |
| Histogram gradient boosting | 0.74 | 0.99 | 0.72 | 0.94 |

Boosting reduced held-out MAE by 0.07 points versus the first-semester average (paired 95% interval for the difference, −0.11 to −0.03). In course 9147 the MAE fell from 1.12 to 0.85 across 77 students. In course 9500 it rose from 0.42 to 0.43 across 131. Some courses have fewer than five test students. At prediction time, eligibility for the measured target is unknown. A prospective cohort with a documented grade for students who fail or withdraw would address a larger uncertainty than the small improvement in average error. [All course results](portalegre-evaluation.json)

## Reproduce the comparisons

Download the original ZIP files from the UCI records above. The scripts read them locally and check the SHA-256 digests before opening any tables. The supplied OULAD ZIP also matched an independent download from UCI. Both archives passed ZIP integrity checks. Only aggregate results are stored in this repository.

| Archive | SHA-256 |
| --- | --- |
| UCI 349, OULAD | `f2ed1902616c1fe8d2824d872c0b7d2d72be435bf0124d077044fe4be2c6d3e4` |
| UCI 697, Portalegre | `e90e55fd65ec462ae283ebeb2cca409319e3460ed898d8754f62fb35cc83a65d` |

Using the repository's existing dependencies, run the two commands separately. Each prints aggregate JSON. The ordinary Streamlit app and the tests require neither archive.

```console
python -m src.university_evaluation oulad "path/to/open+university+learning+analytics+dataset.zip"
python -m src.university_evaluation portalegre "path/to/predict+students+dropout+and+academic+success.zip"
```

The recorded run used Python 3.13.3, scikit-learn 1.8.0, NumPy 2.5.5 and pandas 3.1.1. Models used ordinary least squares or histogram gradient boosting with 100 iterations, at most 15 leaves, and seed 42. Learned predictions were clipped to the documented grade scales. No hyperparameter search was performed. The paired intervals resample test students 1,000 times with replacement and keep each student's submissions together. They describe sampling variation in the difference in MAE for the fitted models. Individual prediction intervals and uncertainty across institutions or future cohorts were not evaluated.
