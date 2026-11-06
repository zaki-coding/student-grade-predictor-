"""Input timing and strict contracts keep the final target out of inference."""
import math

import pytest

from src.schema import FEATURES, SPECS, validate_inputs


def values(stage="early"):
    return {field: SPECS[field]["default"] for field in FEATURES[stage]}


def test_stage_features_and_no_future_data():
    assert "G3" not in FEATURES["early"] + FEATURES["updated"]
    assert "absences" not in FEATURES["early"] + FEATURES["updated"]
    assert "G1" not in FEATURES["early"] and "G2" not in FEATURES["early"]
    assert set(FEATURES["updated"]) == set(FEATURES["early"]) | {"G1", "G2"}


@pytest.mark.parametrize("stage", ["early", "updated"])
def test_column_order_is_independent_of_dictionary_order(stage):
    data = dict(reversed(list(values(stage).items())))
    assert list(validate_inputs(data, stage).columns) == FEATURES[stage]


def test_missing_values_are_explicitly_supported():
    data = values()
    data["studytime"] = None
    data["internet"] = None
    assert validate_inputs(data, "early").isna().sum().sum() == 2


@pytest.mark.parametrize("field,value", [
    ("age", 14), ("age", 23), ("studytime", 0), ("studytime", 2.5),
    ("studytime", math.nan), ("studytime", math.inf), ("studytime", True),
    ("internet", "sometimes"), ("age", "18"),
])
def test_invalid_feature_values_rejected(field, value):
    data = values()
    data[field] = value
    with pytest.raises((ValueError, TypeError)):
        validate_inputs(data, "early")


def test_missing_and_unexpected_keys_rejected():
    data = values()
    del data["age"]
    with pytest.raises((ValueError, TypeError)):
        validate_inputs(data, "early")
    data = values()
    data["G3"] = 15
    with pytest.raises((ValueError, TypeError)):
        validate_inputs(data, "early")


def test_unknown_stage_rejected():
    with pytest.raises((ValueError, KeyError)):
        validate_inputs(values(), "future")
