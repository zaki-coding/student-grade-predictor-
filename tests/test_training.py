"""Mechanistic leakage safeguards, not a proxy for prospective validation."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline

from src.schema import FEATURES, SPECS
from src.train import build_pipeline, conformal_radius, split_indices

ROOT = Path(__file__).resolve().parents[1]


def test_split_is_reproducible_disjoint_and_exhaustive():
    train, calibration, test = split_indices(649)
    again = split_indices(649)
    for left, right in zip((train, calibration, test), again):
        np.testing.assert_array_equal(left, right)
    assert [len(train), len(calibration), len(test)] == [389, 130, 130]
    assert not set(train) & set(calibration)
    assert not set(train) & set(test)
    assert not set(calibration) & set(test)
    assert set(train) | set(calibration) | set(test) == set(range(649))


def test_preprocessing_is_inside_pipeline_and_fit_uses_training_rows():
    stage = "early"
    rows = [{field: SPECS[field]["default"] for field in FEATURES[stage]} for _ in range(4)]
    for row, age in zip(rows, [15, 16, 17, 22]):
        row["age"] = age
    frame = pd.DataFrame(rows)
    pipeline = build_pipeline(stage, LinearRegression())
    assert isinstance(pipeline, Pipeline)
    pipeline.fit(frame.iloc[:3], [8, 10, 12])
    numeric = pipeline.named_steps["preprocess"].named_transformers_["numeric"]
    # A validation-only age of 22 must not influence the fitted training median.
    assert numeric.named_steps["impute"].statistics_[0] == 16
    before = numeric.named_steps["impute"].statistics_.copy()
    pipeline.predict(frame.iloc[3:])
    np.testing.assert_array_equal(numeric.named_steps["impute"].statistics_, before)


def test_conformal_quantile_is_finite_sample_order_statistic():
    assert conformal_radius(np.arange(1, 10), alpha=.2) == 8
    assert conformal_radius([1], alpha=.1) == float("inf")
    with pytest.raises(ValueError):
        conformal_radius([])
    with pytest.raises(ValueError):
        conformal_radius([float("nan")])


def test_manifest_matches_deterministic_splits_when_generated():
    path = ROOT / "reports" / "split_manifest.json"
    if not path.exists():
        pytest.skip("Train artifacts first: python -m src.train")
    manifest = json.loads(path.read_text())
    for key, expected in zip(["train", "calibration", "test"], split_indices(649)):
        assert manifest[key] == expected.tolist()
    assert manifest["seed"] == 42
    assert len(manifest["dataset_sha256"]) == 64


def test_generated_reports_use_canonical_lf_for_portable_content_hashes():
    names = ['metrics.json', 'predictions.csv', 'importance.csv', 'data_summary.json',
             'split_manifest.json', 'ml_audit.json', 'ml_audit.md']
    if not all((ROOT / 'reports' / name).exists() for name in names):
        pytest.skip('Train artifacts first: python -m src.train')
    for name in names:
        raw = (ROOT / 'reports' / name).read_bytes()
        assert b'\r' not in raw, f'{name} must preserve canonical LF bytes across platforms'
