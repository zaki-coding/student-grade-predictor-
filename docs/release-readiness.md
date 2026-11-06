# Release readiness

The final release-preparation work is described in [the deployment checklist](deployment.md), [privacy explanation](privacy.md) and [release validation](release-validation.md).

The approved base commit `73083aa` is already pushed and all four CI jobs passed. The current release branch still requires review; a passing base build does not prove that a new hosted deployment has succeeded. Neither repository visibility nor public hosting has been changed.

The application is intended as a transparent educational portfolio demonstration. Its scientific limitations remain: a reused historical audit, retrospective early inputs, limited early accuracy, broad intervals, small-group coverage failures, and no prospective/external or completed fairness validation. Public availability would not remove those limits.

The recommended sequence is review the release PR and its CI, verify the clean-start evidence and privacy wording, approve any repository rename/visibility change separately, and approve a clearly labeled hosted demonstration separately. Use synthetic data in public demonstrations. No accounts, persistent personal-grade database or analytics service are introduced.
