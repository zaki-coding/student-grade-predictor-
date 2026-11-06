"""Verified, in-memory initialization of the two approved release models.

Only reviewed public data and code are used. No pickle/joblib object is loaded,
no network request is made, and no user inputs or predictions enter this cache.
Checksums detect accidental/stale/tampered resources in the reviewed checkout;
they are not a signing boundary against someone replacing the whole program.
"""
from copy import deepcopy
import hashlib
import io
import json
from threading import Lock

import numpy as np
import pandas as pd
import sklearn

from src.data import ROOT, EXPECTED_CSV_SHA256, validate_dataset
from src.schema import FEATURES, SCHEMA_VERSION
from src.train import (ALPHA, SEED, build_preprocessor, candidate_pipelines,
                       conformal_radius, metrics, split_indices)
from src.reliability import build_reference, interval_diagnostics

RELEASE_VERSION = 'student-success-ai-1.0.0-iteration2'
MANIFEST_PATH = ROOT / 'resources' / 'model-release.json'
# The reviewed manifest pins data, evaluation and canonical-LF recipe sources.
EXPECTED_MANIFEST_SHA256 = '9b01ca13ebdaa54caf5077c7b6a9f04d324627dcf3cab10884e19907fc651a42'
APPROVED_MODELS = {'early': 'LinearRegression', 'updated': 'G2Persistence'}
RECIPE_FILES = ('src/train.py', 'src/data.py', 'src/schema.py',
                'src/reliability.py', 'src/estimators.py')
_CACHE = None
_LOCK = Lock()
PARITY_ATOL = 1e-9


class ModelPreparationError(ValueError):
    """Safe public error category; messages contain no host paths or user data."""


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical_source(raw):
    return raw.replace(b'\r\n', b'\n')


def _read_verified_resources():
    """Verify everything before fitting; files cannot select executable classes."""
    try:
        raw = MANIFEST_PATH.read_bytes()
        if _sha256(_canonical_source(raw)) != EXPECTED_MANIFEST_SHA256:
            raise ModelPreparationError('Model initialization failed: release manifest checksum mismatch. The calculator remains available.')
        manifest = json.loads(raw)
        if (manifest['release_version'] != RELEASE_VERSION or manifest['schema_version'] != SCHEMA_VERSION
                or manifest['artifact_version'] != 2 or manifest['sklearn_version'] != sklearn.__version__
                or manifest['selected_models'] != APPROVED_MODELS or manifest['seed'] != SEED):
            raise ModelPreparationError('Model initialization failed: release or dependency version mismatch. The calculator remains available.')
        if set(manifest['recipe_sha256']) != set(RECIPE_FILES):
            raise ModelPreparationError('Model initialization failed: approved recipe metadata mismatch. The calculator remains available.')
        for name in RECIPE_FILES:
            if _sha256(_canonical_source((ROOT / name).read_bytes())) != manifest['recipe_sha256'][name]:
                raise ModelPreparationError('Model initialization failed: approved recipe checksum mismatch. The calculator remains available.')
        data_bytes = (ROOT / 'resources' / 'student-por.csv').read_bytes()
        if manifest['dataset_sha256'] != EXPECTED_CSV_SHA256 or _sha256(data_bytes) != EXPECTED_CSV_SHA256:
            raise ModelPreparationError('Model initialization failed: public dataset checksum mismatch. The calculator remains available.')
        evaluation_bytes = (ROOT / 'resources' / 'release-metrics.json').read_bytes()
        predictions_bytes = (ROOT / 'resources' / 'release-predictions.csv').read_bytes()
        if (_sha256(_canonical_source(evaluation_bytes)) != manifest['metrics_sha256']
                or _sha256(_canonical_source(predictions_bytes)) != manifest['predictions_sha256']):
            raise ModelPreparationError('Model initialization failed: approved evaluation checksum mismatch. The calculator remains available.')
        evaluation = json.loads(evaluation_bytes)
        if set(evaluation) != set(FEATURES) or any(evaluation[s]['selected_model'] != APPROVED_MODELS[s] for s in FEATURES):
            raise ModelPreparationError('Model initialization failed: approved method mismatch. The calculator remains available.')
        frame = validate_dataset(pd.read_csv(io.BytesIO(data_bytes), sep=';'))
        approved_predictions = pd.read_csv(io.BytesIO(predictions_bytes))
        return manifest, frame, evaluation, approved_predictions
    except ModelPreparationError:
        raise
    except (OSError, ValueError, KeyError, TypeError, UnicodeError):
        raise ModelPreparationError('Model initialization failed: required release resources are unavailable or invalid. The calculator remains available; retry after the operator restores the reviewed release.') from None


def read_release_resources():
    """Verify and read isolated public release data/evaluation without fitting.

    Returns (manifest, source DataFrame, evaluation dict, audit predictions
    DataFrame). No visitor records or globally mutable data are returned.
    """
    return _read_verified_resources()


def _check_close(actual, expected):
    if not np.allclose(actual, expected, rtol=0, atol=PARITY_ATOL, equal_nan=False):
        raise ModelPreparationError('Model initialization failed: numerical parity with the approved release could not be verified. The calculator remains available.')


def _prepare_verified_models():
    manifest, frame, evaluation, approved_predictions = _read_verified_resources()
    train, calibration, test = split_indices(len(frame))
    bundles = {}
    for stage, fields in FEATURES.items():
        X, y = frame[fields], frame['G3']
        name = APPROVED_MODELS[stage]
        # Candidates are a fixed, reviewed code allowlist; no CV/tuning is run here.
        pipeline = candidate_pipelines(stage)[name].fit(X.iloc[train], y.iloc[train])
        calibration_prediction = np.clip(pipeline.predict(X.iloc[calibration]), 0, 20)
        radius = conformal_radius(np.abs(y.iloc[calibration].to_numpy()-calibration_prediction))
        approved = evaluation[stage]
        _check_close(radius, approved['interval_radius'])
        point = np.clip(pipeline.predict(X.iloc[test]), 0, 20)
        rows = approved_predictions[approved_predictions['stage'] == stage].set_index('row_id')
        if len(rows) != len(test) or rows.index.has_duplicates or set(rows.index) != set(test):
            raise ModelPreparationError('Model initialization failed: approved audit rows do not match. The calculator remains available.')
        _check_close(point, rows.loc[test, 'predicted'].to_numpy())
        _check_close(y.iloc[test].to_numpy(), rows.loc[test, 'actual'].to_numpy())
        for key, value in metrics(y.iloc[test], point).items():
            _check_close(value, approved['test'][key])
        # Keep the approved calibrated radius after checking its reconstructed value.
        radius = float(approved['interval_radius'])
        lower, upper = np.maximum(0, point-radius), np.minimum(20, point+radius)
        diagnostics = interval_diagnostics(y.iloc[test].to_numpy(), lower, upper, X.iloc[test])
        for key in ('coverage', 'mean_interval_width'):
            _check_close(diagnostics['overall'][key], approved['test'][key])
        active = ['G2'] if stage == 'updated' else list(fields)
        reference = build_reference(X.iloc[train][active], build_preprocessor(active))
        bundles[stage] = {
            'pipeline': pipeline, 'stage': stage, 'features': list(fields), 'model_name': name,
            'active_features': active, 'interval_radius': radius, 'schema_version': SCHEMA_VERSION,
            'artifact_version': 2, 'sklearn_version': sklearn.__version__,
            'dataset_sha256': manifest['dataset_sha256'], 'seed': SEED,
            'nominal_coverage': 1-ALPHA, 'evaluation': deepcopy(approved), 'reference': reference,
            'evaluation_context': approved['evaluation_context'],
            'model_version': RELEASE_VERSION, 'provisioning_checksum': EXPECTED_MANIFEST_SHA256,
        }
    return bundles


def prepare_models():
    """Prepare both approved models once per process and return isolated copies.

    The lock prevents concurrent cold starts doing duplicate work. A failed build
    is never assigned to the cache, so a subsequent request can retry. The shared
    state contains public training data/models only, never visitor records.
    """
    global _CACHE
    with _LOCK:
        if _CACHE is None:
            try:
                prepared = _prepare_verified_models()
            except ModelPreparationError:
                raise
            except Exception:
                raise ModelPreparationError('Model initialization failed unexpectedly. The calculator remains available; retry or contact the app operator.') from None
            _CACHE = prepared
        return deepcopy(_CACHE)


def clear_prepared_models():
    """Explicit test/operator reset; never invoked on every user interaction."""
    global _CACHE
    with _LOCK:
        _CACHE = None


if __name__ == '__main__':
    prepared = prepare_models()
    for stage, bundle in prepared.items():
        print(f'{stage}: {bundle["model_name"]}; version={bundle["model_version"]}; manifest={bundle["provisioning_checksum"]}')
