"""Coverage is measured; train-only novelty screens cannot certify applicability."""
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from src.schema import FEATURES, SPECS, validate_inputs

ROOT = Path(__file__).resolve().parents[1]


def profile(stage="early"):
    return {field: SPECS[field]["default"] for field in FEATURES[stage]}


def test_coverage_counts_are_inclusive_and_wilson_bounds_are_not_guarantees():
    from src.reliability import coverage_summary, wilson_interval
    result = coverage_summary([0, 1, 2, 3], [0, 0, 1, 0], [0, 2, 2, 2])
    assert result["n"] == 4 and result["covered"] == 3
    assert result["coverage"] == .75
    lower, upper = result["coverage_95ci"]
    assert 0 <= lower < .75 < upper <= 1
    assert result["mean_interval_width"] == 1.25
    assert wilson_interval(0, 10) == pytest.approx([0, .2775327999])
    assert wilson_interval(10, 10) == pytest.approx([.7224672001, 1])


@pytest.mark.parametrize("y,lower,upper", [([], [], []), ([1], [2], [1]), ([1], [0, 1], [2]),
                                                   ([float("nan")], [0], [2])])
def test_invalid_coverage_arrays_rejected(y, lower, upper):
    from src.reliability import coverage_summary
    with pytest.raises(ValueError):
        coverage_summary(y, lower, upper)


def test_novelty_reference_fit_is_training_only_and_assessment_does_not_refit():
    from src.reliability import assess_reliability, build_reference
    from src.train import build_pipeline
    train = pd.DataFrame([{**profile(), "age": age} for age in [15, 16, 17, 18]])
    preprocessor = build_pipeline("early", LinearRegression()).named_steps["preprocess"]
    reference = build_reference(train, preprocessor)
    assert reference["n_train"] == 4
    assert reference["support"]["age"]["min"] == 15
    assert reference["support"]["age"]["max"] == 18
    before = reference["transformed_train"].copy()
    outside = {**profile(), "age": 22}
    warnings, reliability = assess_reliability(outside, validate_inputs(outside, "early"), reference)
    assert reliability["status"] == "caution"
    assert any("outside" in warning.lower() and "age" in warning for warning in warnings)
    assert any("joint" in warning.lower() for warning in warnings)
    np.testing.assert_array_equal(reference["transformed_train"], before)
    assert reference["support"]["age"]["max"] == 18


@pytest.mark.integration
@pytest.mark.parametrize("stage", ["early", "updated"])
def test_prediction_exposes_model_bound_evaluation_and_missingness_warning(stage):
    from src.predict import load_bundle, predict
    bundle = load_bundle(stage, ROOT / "models")
    result = predict(profile(stage), stage, ROOT / "models")
    assert result["evaluation"] == bundle["evaluation"]
    assert result["nominal_coverage"] == .9
    assert "reused" in result["evaluation_context"].lower()
    assert result["reliability"]["n_train"] == 389
    assert isinstance(result["warnings"], list)
    missing = {field: None for field in FEATURES[stage]}
    imputed = predict(missing, stage, ROOT / "models")
    assert imputed["reliability"]["status"] == "caution"
    assert any("missing" in warning.lower() and "coverage" in warning.lower() for warning in imputed["warnings"])


@pytest.mark.integration
def test_stage_baselines_and_interval_diagnostics_are_real_audit_measurements():
    from src.predict import load_bundle
    metrics = json.loads((ROOT / "reports" / "metrics.json").read_text())
    predictions = pd.read_csv(ROOT / "reports" / "predictions.csv")
    for stage in FEATURES:
        result = metrics[stage]
        assert "selection_rule" in result and "evaluation_context" in result
        assert "reused" in result["evaluation_context"].lower()
        assert len(result["baselines"]) >= 2
        if stage == "updated":
            assert any("g2" in name.lower() for name in result["baselines"])
        else:
            assert any("median" in name.lower() for name in result["baselines"])
        rows = predictions[predictions["stage"] == stage]
        covered = ((rows["actual"] >= rows["lower"]) & (rows["actual"] <= rows["upper"])).sum()
        overall = result["interval_diagnostics"]["overall"]
        assert overall["n"] == 130
        assert overall["covered"] == covered
        assert overall["coverage"] == pytest.approx(covered / 130)
        assert result["test"]["coverage"] == pytest.approx(covered / 130)
        assert len(overall["coverage_95ci"]) == 2
        for group in result["interval_diagnostics"]["groups"].values():
            assert 0 <= group["covered"] <= group["n"] <= 130
        bundle = load_bundle(stage, ROOT / "models")
        # Frozen release values and regenerated research reports may differ only
        # in platform-level floating point rounding. Preserve numerical parity.
        assert bundle["evaluation"]["test"] == pytest.approx(result["test"], rel=0, abs=1e-9)


@pytest.mark.integration
@pytest.mark.parametrize("inconsistency", ["evaluation_radius", "nonfinite_reference", "invalid_nominal", "old_version"])
def test_inconsistent_artifact_metadata_rejected_before_inference(tmp_path, inconsistency):
    from src.predict import load_bundle
    bundle = copy.deepcopy(load_bundle("updated", ROOT / "models"))
    if inconsistency == "evaluation_radius":
        bundle["evaluation"]["interval_radius"] += 1
    elif inconsistency == "nonfinite_reference":
        bundle["reference"]["transformed_train"][0, 0] = np.nan
    elif inconsistency == "invalid_nominal":
        bundle["nominal_coverage"] = 0
    else:
        bundle["artifact_version"] = 1
    from src.predict import _validate_bundle
    with pytest.raises(ValueError):
        _validate_bundle(bundle, "updated")
