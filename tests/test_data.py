"""Data source validation is exercised without network access."""
import hashlib
import json

import pandas as pd
import pytest

import src.data as data
from src.schema import FEATURES, SPECS


def frame():
    row = {field: SPECS[field]["default"] for field in FEATURES["updated"]}
    row["G3"] = 12
    return pd.DataFrame([row] * 649)


def test_target_missing_or_wrong_source_shape_rejected():
    with pytest.raises(ValueError):
        data.validate_dataset(frame().iloc[:-1])
    with pytest.raises(ValueError):
        data.validate_dataset(frame().drop(columns="G3"))
    missing = frame()
    missing.loc[0, "G3"] = float("nan")
    with pytest.raises(ValueError):
        data.validate_dataset(missing)


def test_feature_corruption_rejected():
    corrupted = frame()
    corrupted.loc[0, "internet"] = "unknown"
    with pytest.raises(ValueError):
        data.validate_dataset(corrupted)


def test_disabled_download_never_uses_network(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA_PATH", tmp_path / "student-por.csv")
    with pytest.raises(FileNotFoundError):
        data.load_data(download=False)


def test_cached_checksum_mismatch_is_detected(tmp_path, monkeypatch):
    path = tmp_path / "student-por.csv"
    path.write_text("tampered")
    path.with_suffix(".provenance.json").write_text(json.dumps({"csv_sha256": hashlib.sha256(b"original").hexdigest()}))
    monkeypatch.setattr(data, "DATA_PATH", path)
    with pytest.raises(ValueError, match="checksum"):
        data.load_data(download=False)
