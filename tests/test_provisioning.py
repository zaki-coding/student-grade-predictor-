"""Cold, checked provisioning must never depend on serialized model files."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil

import joblib
import numpy as np
import pytest

import src.provisioning as provisioning
from src.predict import load_bundle, predict
from src.schema import FEATURES, SPECS


@pytest.fixture(autouse=True)
def reset_model_cache():
    provisioning.clear_prepared_models()
    yield
    provisioning.clear_prepared_models()


def profile(stage):
    return {name: SPECS[name]['default'] for name in FEATURES[stage]}


def isolated_release(tmp_path, monkeypatch):
    root = provisioning.ROOT
    for name in (*provisioning.RECIPE_FILES, 'resources/model-release.json',
                 'resources/student-por.csv', 'resources/release-metrics.json',
                 'resources/release-predictions.csv'):
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, destination)
    monkeypatch.setattr(provisioning, 'ROOT', tmp_path)
    monkeypatch.setattr(provisioning, 'MANIFEST_PATH', tmp_path / 'resources/model-release.json')
    return tmp_path


def test_cold_start_uses_no_research_cache_network_or_deserialization(monkeypatch, tmp_path):
    import pickle
    import urllib.request
    import src.data
    import src.train

    def forbidden(*args, **kwargs):
        raise AssertionError('Cold initialization must not use this operation')

    monkeypatch.setattr(joblib, 'load', forbidden)
    monkeypatch.setattr(pickle, 'load', forbidden)
    monkeypatch.setattr(pickle, 'loads', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    monkeypatch.setattr(src.data, 'DATA_PATH', tmp_path / 'no-data.csv')
    monkeypatch.setattr(src.train, 'load_data', forbidden)
    prepared = provisioning.prepare_models()
    assert set(prepared) == {'early', 'updated'}
    for stage in FEATURES:
        result = predict(profile(stage), stage)
        assert 0 <= result['lower'] <= result['prediction'] <= result['upper'] <= 20
        assert result['model_version'] == provisioning.RELEASE_VERSION
        assert result['provisioning_checksum'] == provisioning.EXPECTED_MANIFEST_SHA256
    assert predict(profile('updated'), 'updated')['prediction'] == 12


def test_selected_methods_and_measured_evaluation_are_unchanged():
    bundles = provisioning.prepare_models()
    expected = {'early': ('LinearRegression', 2.1351394219443534, 4.4939357175067585),
                'updated': ('G2Persistence', .676923076923077, 2.0)}
    for stage, (name, mae, radius) in expected.items():
        bundle = bundles[stage]
        assert bundle['model_name'] == name
        assert bundle['interval_radius'] == pytest.approx(radius, abs=1e-9)
        assert bundle['evaluation']['test']['mae'] == pytest.approx(mae, abs=1e-9)
        assert bundle['reference']['n_train'] == 389
        assert bundle['evaluation']['split_sizes'] == {'train': 389, 'calibration': 130, 'test': 130}


@pytest.mark.parametrize('path,change', [
    ('resources/model-release.json', b' '),
    ('resources/student-por.csv', b' '),
    ('resources/release-metrics.json', b' '),
    ('resources/release-predictions.csv', b' '),
    ('src/schema.py', b'\n# unreviewed source change'),
])
def test_tampered_resource_is_rejected_before_initialization(tmp_path, monkeypatch, path, change):
    root = isolated_release(tmp_path, monkeypatch)
    target = root / path
    target.write_bytes(target.read_bytes() + change)
    with pytest.raises(provisioning.ModelPreparationError, match='checksum mismatch'):
        provisioning.prepare_models()


def test_wrong_dependency_version_is_rejected(monkeypatch):
    monkeypatch.setattr(provisioning.sklearn, '__version__', 'unreviewed-version')
    with pytest.raises(provisioning.ModelPreparationError, match='version mismatch'):
        provisioning.prepare_models()


def test_missing_resource_error_contains_no_host_path(tmp_path, monkeypatch):
    isolated_release(tmp_path, monkeypatch)
    (tmp_path / 'resources/student-por.csv').unlink()
    with pytest.raises(provisioning.ModelPreparationError) as raised:
        provisioning.prepare_models()
    assert 'calculator remains available' in str(raised.value).lower()
    assert str(tmp_path) not in str(raised.value)


def test_numerical_drift_is_not_silently_accepted(monkeypatch):
    original = provisioning._read_verified_resources

    def changed_training_values():
        manifest, frame, metrics, predictions = original()
        frame['G3'] = 0
        return manifest, frame, metrics, predictions

    monkeypatch.setattr(provisioning, '_read_verified_resources', changed_training_values)
    with pytest.raises(provisioning.ModelPreparationError, match='numerical parity'):
        provisioning.prepare_models()


def test_concurrent_cold_starts_prepare_once_and_never_share_caller_mutations(monkeypatch):
    original = provisioning._prepare_verified_models
    count = 0

    def counted():
        nonlocal count
        count += 1
        return original()

    monkeypatch.setattr(provisioning, '_prepare_verified_models', counted)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: provisioning.prepare_models(), range(4)))
    assert count == 1
    results[0]['early']['evaluation']['test']['mae'] = -999
    results[0]['early']['pipeline'].named_steps['model'].coef_[:] = -999
    results[0]['early']['reference']['transformed_train'][:] = -999
    pristine = provisioning.prepare_models()
    assert pristine['early']['evaluation']['test']['mae'] > 0
    assert not np.all(pristine['early']['pipeline'].named_steps['model'].coef_ == -999)
    assert not np.all(pristine['early']['reference']['transformed_train'] == -999)
    assert results[1]['early']['evaluation']['test']['mae'] > 0


def test_failed_initialization_can_retry_without_poisoning_cache(monkeypatch):
    original = provisioning._prepare_verified_models
    count = 0

    def fail_once():
        nonlocal count
        count += 1
        if count == 1:
            raise RuntimeError('secret internal host path')
        return original()

    monkeypatch.setattr(provisioning, '_prepare_verified_models', fail_once)
    with pytest.raises(provisioning.ModelPreparationError) as raised:
        provisioning.prepare_models()
    assert 'secret internal host path' not in str(raised.value)
    assert set(provisioning.prepare_models()) == {'early', 'updated'}
    assert count == 2


def test_custom_serialized_artifact_is_rejected_without_loading(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Untrusted serialized data must never be loaded')

    joblib.dump({'this': 'is not an approved model'}, tmp_path / 'early.joblib')
    monkeypatch.setattr(joblib, 'load', forbidden)
    with pytest.raises(ValueError, match='serialized model files are never loaded'):
        load_bundle('early', tmp_path)


def test_research_report_mutations_cannot_change_approved_release_evaluation(monkeypatch):
    from src.data import ROOT
    original_read = Path.read_bytes

    def guarded(path):
        if path.parent == ROOT / 'reports':
            raise AssertionError('Serving must use immutable release snapshots')
        return original_read(path)

    monkeypatch.setattr(Path, 'read_bytes', guarded)
    prepared = provisioning.prepare_models()
    assert prepared['updated']['evaluation']['selected_model'] == 'G2Persistence'


def test_release_resource_reader_is_verified_and_isolated():
    first = provisioning.read_release_resources()
    second = provisioning.read_release_resources()
    assert len(first[1]) == 649
    first[2]['early']['test']['mae'] = -1
    first[1].loc[0, 'G3'] = -1
    assert second[2]['early']['test']['mae'] > 0
    assert second[1].loc[0, 'G3'] >= 0
