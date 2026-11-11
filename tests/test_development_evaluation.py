"""Guard the split and out-of-fold calculations used in the v3 experiment."""

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.model_selection import LeaveOneGroupOut

from src import development_evaluation as evaluation
from src.schema import FEATURES, SPECS


def test_group_folds_fit_on_other_group_and_clip_to_grade_bounds():
    predictors = pd.DataFrame({"period_grade": [0, 1, 18, 19]})
    target = np.array([0, 0, 22, 24])
    predictions = evaluation.compare_candidates(
        predictors, target, {"mean": DummyRegressor()}, LeaveOneGroupOut(),
        (0, 20), groups=["A", "A", "B", "B"],
    )
    np.testing.assert_array_equal(predictions["mean"], [20, 20, 0, 0])


def test_experiment_excludes_calibration_and_audit_rows(monkeypatch):
    rows = 30
    frame = pd.DataFrame({field: [spec["default"]] * rows for field, spec in SPECS.items()})
    frame["school"] = ["GP", "MS"] * (rows // 2)
    frame["G3"] = 12
    training_rows, calibration_rows, audit_rows = evaluation.split_indices(rows)
    frame.loc[calibration_rows, "G3"] = -1
    frame.loc[audit_rows, "G3"] = -2
    stages_seen = []

    def compare(predictors, target, candidates, cv, bounds, *, groups=None):
        assert predictors.index.to_list() == training_rows.tolist()
        assert "G3" not in predictors.columns and "school" not in predictors.columns
        assert list(predictors) in FEATURES.values()
        assert (target == 12).all()
        if groups is not None:
            np.testing.assert_array_equal(groups, frame.loc[training_rows, "school"])
        stages_seen.append(cv.get_n_splits(groups=groups))
        return {candidate: target.copy() for candidate in candidates}

    monkeypatch.setattr(evaluation, "compare_candidates", compare)
    report = evaluation.evaluate_development(frame)
    assert report["n"] == len(training_rows)
    assert stages_seen == [5, 2, 5, 2]
