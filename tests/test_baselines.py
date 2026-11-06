"""Stage-appropriate simple baselines and conservative model choice."""
import numpy as np
import pandas as pd
import pytest

from src.schema import FEATURES, SPECS


def profile():
    return {field: SPECS[field]["default"] for field in FEATURES["updated"]}


def test_updated_latest_grade_baseline_really_returns_g2_and_uses_train_median_for_missing():
    from src.train import candidate_pipelines
    training = pd.DataFrame([{**profile(), "G2": grade} for grade in [5, 10, 15]])
    # Targets deliberately unrelated: persistence must not quietly learn a regression.
    pipeline = candidate_pipelines("updated")["G2Persistence"].fit(training, [20, 0, 1])
    validation = pd.DataFrame([{**profile(), "G2": grade} for grade in [2, 17]])
    np.testing.assert_array_equal(pipeline.predict(validation), [2, 17])
    missing = pd.DataFrame([{**profile(), "G2": np.nan}])
    assert pipeline.predict(missing)[0] == 10
    altered = validation.copy()
    altered["studytime"] = 4
    altered["G1"] = 0
    np.testing.assert_array_equal(pipeline.predict(altered), [2, 17])


def test_one_standard_error_rule_prefers_simple_near_tie_but_not_large_validation_gap():
    from src.train import select_simplest
    comparison = [{"model": "simple", "mae": 1.00, "mae_se": .04},
                  {"model": "complex", "mae": .98, "mae_se": .05}]
    selected, cutoff = select_simplest(comparison)
    assert selected == "simple"
    assert cutoff == pytest.approx(1.03)
    comparison[1]["mae"] = .75
    assert select_simplest(comparison)[0] == "complex"
    with pytest.raises(ValueError):
        select_simplest([])
