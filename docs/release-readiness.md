# Iteration 2 release-readiness notes

The current application is suitable as a local, transparent portfolio demonstration. Public availability would not establish scientific validity for new students.

## Completed in this iteration

The existing app was extended, preserving its calculator and five-section structure. Added stage-appropriate baselines, a training-only simplicity-aware selection rule, small Ridge experiments, coverage counts/Wilson intervals/descriptive groups, active-feature support checks, artifact-bound evaluation, a course dashboard, exact target scenarios, version 2 portable saves, CSV summaries and disclosed prediction reports. Regression and new tests were executed locally.

## Remaining evidence gaps

- The original test sample was inspected previously; iteration 2 calls it a reused historical audit. It cannot supply pristine evidence of improvement.
- No new school, future cohort or university population was evaluated. Questionnaire timing remains retrospective.
- Source records lack robust student IDs; a row split does not prove independence or school transferability.
- Early predictions remain weak and have wide intervals. Simplifying the model improves transparency, not necessarily accuracy.
- Updated predictions currently use a latest-grade baseline. The UI must not imply that other displayed academic factors influence this selected method.
- Overall 90% nominal conformal coverage is marginal under exchangeability. Observed groups are small and descriptive; neither fairness nor conditional coverage is certified.
- Training-only novelty checks are heuristics. Missingness and novel institution coverage remain unvalidated.
- A local Windows pass is not a remote Windows/Linux multi-version CI pass. CI must run after approval to push.
- Browser captures and automated interactions do not replace a formal accessibility/user study.

## Personal data

No accounts or cloud database were introduced. Course records and settings reside in temporary server session memory, with explicit portable downloads. Keep exported JSON/CSV/Markdown files private. Session memory is not a durable save; the user must export before closing and restore on a later visit.

## Recommended release sequence

Review model claims and downloads, run configured remote CI after push approval, conduct usability/accessibility review, then consider a clearly labeled research-demo release. External validation should precede claims of personalized predictive reliability. No public deployment or GitHub push was performed during this iteration.
