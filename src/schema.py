"""Strict, shared inference schema for the two prediction stages."""
from numbers import Real
import numpy as np
import pandas as pd

SCHEMA_VERSION = 1
SPECS = {
    'age': {'label': 'Age', 'min': 15, 'max': 22, 'default': 17},
    'Medu': {'label': "Mother's education (0 none; 4 higher)", 'min': 0, 'max': 4, 'default': 2},
    'Fedu': {'label': "Father's education (0 none; 4 higher)", 'min': 0, 'max': 4, 'default': 2},
    'traveltime': {'label': 'Travel time (1 <15m; 2 15–30m; 3 30–60m; 4 >60m)', 'min': 1, 'max': 4, 'default': 1},
    'studytime': {'label': 'Weekly study (1 <2h; 2 2–5h; 3 5–10h; 4 >10h)', 'min': 1, 'max': 4, 'default': 2},
    'failures': {'label': 'Past class failures (dataset code 0–4)', 'min': 0, 'max': 4, 'default': 0},
    'internet': {'label': 'Internet access at home', 'options': ['yes', 'no'], 'default': 'yes'},
    'higher': {'label': 'Intends to pursue higher education', 'options': ['yes', 'no'], 'default': 'yes'},
    'G1': {'label': 'First-period grade / 20', 'min': 0, 'max': 20, 'default': 12},
    'G2': {'label': 'Second-period grade / 20', 'min': 0, 'max': 20, 'default': 12},
}
FEATURES = {'early': list(SPECS)[:8], 'updated': list(SPECS)}


def validate_stage(stage):
    if not isinstance(stage, str) or stage not in FEATURES:
        raise ValueError('Stage must be early or updated.')


def validate_inputs(values: dict, stage: str) -> pd.DataFrame:
    """Validate all keys and values; explicit None requests training-fitted imputation."""
    validate_stage(stage)
    if not isinstance(values, dict):
        raise ValueError('Inputs must be a dictionary.')
    if not all(isinstance(key, str) for key in values):
        raise ValueError('Feature names must be strings.')
    expected = set(FEATURES[stage])
    if set(values) != expected:
        raise ValueError(f'Feature mismatch: missing={sorted(expected-set(values))}, extra={sorted(set(values)-expected)}')
    clean = {}
    for name in FEATURES[stage]:
        value, spec = values[name], SPECS[name]
        if value is None:
            clean[name] = np.nan
        elif 'options' in spec:
            if not isinstance(value, str) or value not in spec['options']:
                raise ValueError(f'{name} must be one of {spec["options"]}.')
            clean[name] = value
        else:
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not np.isfinite(value):
                raise ValueError(f'{name} must be a finite integer or None.')
            if not float(value).is_integer() or not spec['min'] <= value <= spec['max']:
                raise ValueError(f'{name} must be an integer in [{spec["min"]}, {spec["max"]}].')
            clean[name] = float(value)
    return pd.DataFrame([clean], columns=FEATURES[stage])
