"""Hosted cold starts must use only reviewed public resources, never research pickles."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.schema import FEATURES, SPECS

ROOT = Path(__file__).resolve().parents[1]


def profile(stage):
    return {name: SPECS[name]['default'] for name in FEATURES[stage]}


def test_cold_predictions_need_no_network_pickle_or_research_dataset(monkeypatch, tmp_path):
    import joblib
    import pickle
    import urllib.request
    import src.data as data
    import src.train as training
    from src.provisioning import clear_prepared_models
    from src.predict import predict

    def forbidden(*args, **kwargs):
        raise AssertionError('Cold provisioning must not deserialize, download or run the full experiment')

    clear_prepared_models()
    monkeypatch.setattr(joblib, 'load', forbidden)
    monkeypatch.setattr(pickle, 'load', forbidden)
    monkeypatch.setattr(pickle, 'loads', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    monkeypatch.setattr(data, 'urlopen', forbidden)
    monkeypatch.setattr(data, 'DATA_PATH', tmp_path / 'no-research-data.csv')
    monkeypatch.setattr(data, 'load_data', forbidden)
    monkeypatch.setattr(training, 'load_data', forbidden)
    monkeypatch.setattr(training, 'train_all', forbidden)
    try:
        early = predict(profile('early'), 'early')
        updated = predict(profile('updated'), 'updated')
        assert early['model_name'] == 'LinearRegression'
        assert updated['model_name'] == 'G2Persistence'
        assert updated['prediction'] == 12
        assert (updated['lower'], updated['upper']) == (10, 14)
        for result in [early, updated]:
            assert result['lower'] <= result['prediction'] <= result['upper']
            assert result['evaluation']['split_sizes'] == {'train': 389, 'calibration': 130, 'test': 130}
    finally:
        clear_prepared_models()


@pytest.mark.parametrize('stage', ['early', 'updated'])
def test_provisioned_points_and_intervals_preserve_all_approved_audit_predictions(stage):
    from src.predict import load_bundle
    data = pd.read_csv(ROOT / 'resources' / 'student-por.csv', sep=';')
    approved = pd.read_csv(ROOT / 'resources' / 'release-predictions.csv')
    approved = approved[approved.stage == stage]
    bundle = load_bundle(stage)
    frame = data.iloc[approved.row_id.astype(int)][FEATURES[stage]]
    points = np.clip(bundle['pipeline'].predict(frame), 0, 20)
    radius = bundle['interval_radius']
    np.testing.assert_allclose(points, approved.predicted, rtol=0, atol=1e-9)
    np.testing.assert_allclose(np.maximum(0, points-radius), approved.lower, rtol=0, atol=1e-9)
    np.testing.assert_allclose(np.minimum(20, points+radius), approved.upper, rtol=0, atol=1e-9)
