# Dataset card

Source: [UCI Student Performance](https://archive.ics.uci.edu/dataset/320/student+performance).
Citation: Cortez, P. (2008). *Student Performance* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5TG7T.
License: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). Attribution must remain with redistributed data and derived reports. Downloaded data retains its original license; the project code uses MIT.

The application uses only `student-por.csv`: 649 Portuguese-language course records from two Portuguese secondary schools. The mathematics file is not pooled with it because students can occur in both subjects. Target `G3` is final-period academic performance on the original 0–20 scale. This is regression, not a university GPA or percentage predictor. The source reports no missing values; the generated `reports/data_summary.json` records the actual inspection. Pipeline imputers support explicitly missing inference values, which is a robustness feature rather than evidence of accuracy under missingness.

| Stage | Candidate schema / active predictors | Intended timing |
| --- | --- | --- |
| Early | age, mother's and father's education (`Medu`, `Fedu`), travel time, weekly study-time category, past failures, home internet access, higher-education aspiration | Before G1/G2 assessment results; retrospective proxy only |
| Updated | Candidate schema accepts early inputs plus G1/G2; the selected G2Persistence baseline actively uses only G2 | After the second assessment period |

The full source contains additional demographic, family, social, support, health, attendance and assessment variables. This application deliberately uses a small documented subset. G3 never enters predictors. Whole-year absences and ambiguously timed variables are excluded to reduce temporal leakage. The underlying questionnaires do not establish prospective availability of every selected early input; early results are a retrospective benchmark and need prospective validation.

Numeric codes retain UCI meanings: study time 1=<2 hours/week, 2=2–5, 3=5–10, 4=>10; travel time 1=<15 minutes, 2=15–30, 3=30–60, 4=>60. Parental education is 0=none, 1=primary, 2=5th–9th grade, 3=secondary, 4=higher. Past failures retain the supplied coded count (0–4). Values outside the validated schema are rejected instead of extrapolated silently. Valid but rare or unusual active-input profiles can still receive heuristic training-support warnings; those warnings do not establish out-of-distribution accuracy or calibrated coverage. Inactive compatibility fields do not affect the selected updated estimate.

The small, historical, observational sample cannot establish causal effects or reliable accuracy for a different country, institution, subject, or current student population. Random row splits estimate performance on similar records, not generalization to unseen schools or future cohorts. Potential household relationships cannot be audited because stable student/household identifiers are unavailable in this file. Age and parental education can encode disadvantage; excluding other sensitive fields does not establish fairness. This application is for learning and reflection, not admissions, grading, discipline, eligibility or high-stakes decisions.
