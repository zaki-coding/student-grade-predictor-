"""Inference initializes verified public resources without serialized model files."""
import json
from pathlib import Path

import numpy as np
import pytest

from src.predict import compare_scenario, load_bundle, predict
from src.schema import FEATURES, SPECS

ROOT = Path(__file__).resolve().parents[1]


def values(stage):
    return {field: SPECS[field]["default"] for field in FEATURES[stage]}


@pytest.fixture(scope="module")
def artifacts():
    return ROOT / "models"


@pytest.mark.integration
@pytest.mark.parametrize("stage", ["early", "updated"])
def test_trusted_bundle_and_prediction_roundtrip(artifacts, stage):
    bundle = load_bundle(stage, artifacts)
    assert bundle["stage"] == stage
    assert bundle["features"] == FEATURES[stage]
    assert "pipeline" in bundle and "schema_version" in bundle
    first = predict(values(stage), stage, artifacts)
    second = predict(values(stage), stage, artifacts)
    assert first == second
    assert 0 <= first["lower"] <= first["prediction"] <= first["upper"] <= 20
    assert first["model_name"] == bundle["model_name"]


@pytest.mark.integration
@pytest.mark.parametrize("stage", ["early", "updated"])
def test_missing_data_inference_uses_fitted_preprocessing(artifacts, stage):
    sample = values(stage)
    sample["studytime"] = None
    sample["internet"] = None
    assert np.isfinite(predict(sample, stage, artifacts)["prediction"])


@pytest.mark.integration
def test_hypothetical_comparison_delta_and_changed_fields(artifacts):
    original = values("updated")
    adjusted = {**original, "G2": 17}
    result = compare_scenario(original, adjusted, "updated", artifacts)
    assert result["delta"] == pytest.approx(result["adjusted"]["prediction"] - result["original"]["prediction"])
    assert result["changes"] == {"G2": [original["G2"], 17]}
    unchanged = compare_scenario(original, original, "updated", artifacts)
    assert unchanged["delta"] == 0
    assert unchanged["changes"] == {}


def test_missing_artifact_fails_clearly(tmp_path):
    with pytest.raises((FileNotFoundError, ValueError)):
        load_bundle("early", tmp_path)


@pytest.mark.integration
def test_incompatible_feature_schema_is_rejected(artifacts, tmp_path):
    from src.predict import _validate_bundle
    bundle = dict(load_bundle("early", artifacts))
    bundle["features"] = ["G3"]
    with pytest.raises((ValueError, RuntimeError)):
        _validate_bundle(bundle, "early")


@pytest.mark.integration
def test_report_contains_selected_and_baseline_measured_results(artifacts):
    metrics = json.loads((ROOT / "reports" / "metrics.json").read_text())
    for stage in FEATURES:
        result = metrics[stage]
        assert len(result["cv_results"]) >= 4
        assert result["selected_model"] in [row["model"] for row in result["cv_results"]]
        for section in ["test", "baseline_test"]:
            assert result[section]["mae"] >= 0
            assert result[section]["rmse"] >= result[section]["mae"] - 1e-9
            assert np.isfinite(result[section]["r2"])
        assert sum(result["split_sizes"].values()) == 649
        assert 0 <= result["test"]["coverage"] <= 1
