"""Trusted artifact loading, schema validation and candid reliability warnings."""
from copy import deepcopy
from numbers import Real
from pathlib import Path
import numpy as np
import sklearn
from src.data import ROOT
from src.schema import FEATURES, SCHEMA_VERSION, validate_inputs, validate_stage
from src.reliability import assess_reliability


def _finite_number(value):
    return isinstance(value, Real) and not isinstance(value, (bool, np.bool_)) and np.isfinite(value)


def _validate_bundle(bundle, stage):
    """Detect stale/inconsistent local metadata, not malicious-pickle security."""
    required = {'pipeline', 'stage', 'features', 'model_name', 'interval_radius', 'schema_version',
                'sklearn_version', 'evaluation', 'reference', 'evaluation_context', 'nominal_coverage', 'active_features'}
    if not isinstance(bundle, dict) or not required <= bundle.keys() or bundle.get('artifact_version') != 2:
        raise ValueError('Invalid or outdated model artifact; retrain using python -m src.train.')
    if bundle['schema_version'] != SCHEMA_VERSION or bundle['stage'] != stage or bundle['features'] != FEATURES[stage]:
        raise ValueError('Model feature/schema compatibility check failed; retrain.')
    if bundle['sklearn_version'] != sklearn.__version__:
        raise ValueError('Model was fitted with a different scikit-learn version; retrain in this environment.')
    pipeline = bundle['pipeline']
    if list(getattr(pipeline, 'feature_names_in_', [])) != FEATURES[stage]:
        raise ValueError('Fitted pipeline feature order does not match the schema.')
    active = bundle['active_features']
    if (not isinstance(active, list) or not active or not all(isinstance(f,str) for f in active)
            or len(set(active)) != len(active) or not set(active) <= set(FEATURES[stage])):
        raise ValueError('Invalid active feature metadata; retrain.')
    preprocessing = pipeline.named_steps['preprocess']
    used = [field for name, transformer, fields in preprocessing.transformers_
            if transformer != 'drop' for field in fields]
    if set(used) != set(active) or len(used) != len(active):
        raise ValueError('Fitted preprocessing and active feature metadata differ; retrain.')
    radius, nominal = bundle['interval_radius'], bundle['nominal_coverage']
    if not _finite_number(radius) or radius < 0:
        raise ValueError('Invalid calibration interval radius.')
    if not _finite_number(nominal) or not 0 < nominal < 1:
        raise ValueError('Invalid nominal interval coverage.')
    evaluation = bundle['evaluation']
    if not isinstance(evaluation,dict) or evaluation.get('selected_model') != bundle['model_name']:
        raise ValueError('Artifact model and embedded evaluation do not match; retrain.')
    for field,expected in [('interval_radius',radius),('interval_nominal_coverage',nominal)]:
        if not _finite_number(evaluation.get(field)) or not np.isclose(evaluation[field],expected,rtol=0,atol=1e-12):
            raise ValueError('Artifact interval and embedded evaluation do not match; retrain.')
    reference = bundle['reference']
    if not isinstance(reference,dict) or set(reference['support']) != set(active):
        raise ValueError('Training reference schema mismatch; retrain.')
    if list(reference['preprocessor'].feature_names_in_) != active:
        raise ValueError('Training reference preprocessing schema mismatch; retrain.')
    matrix = np.asarray(reference['transformed_train'])
    n_train = reference['n_train']
    if (type(n_train) is not int or n_train <= 1 or matrix.ndim != 2 or matrix.shape[0] != n_train
            or matrix.shape[1] != len(reference['preprocessor'].get_feature_names_out())
            or not np.issubdtype(matrix.dtype,np.number) or not np.isfinite(matrix).all()
            or evaluation['split_sizes']['train'] != n_train):
        raise ValueError('Invalid training reference shape or count; retrain.')
    if not _finite_number(reference['distance_threshold']) or reference['distance_threshold'] < 0:
        raise ValueError('Invalid training support threshold; retrain.')
    for support in reference['support'].values():
        counts = support['counts']
        if (not isinstance(counts,dict) or not counts or any(type(n) is not int or n < 0 for n in counts.values())
                or sum(counts.values()) > n_train):
            raise ValueError('Invalid training support counts; retrain.')
        if 'min' in support and (not _finite_number(support['min']) or not _finite_number(support['max']) or support['min'] > support['max']):
            raise ValueError('Invalid training support bounds; retrain.')
    return bundle


def load_bundle(stage: str, model_dir=Path('models')) -> dict:
    """Return an isolated, verified in-memory model; never load serialized files.

    ``model_dir`` remains for API compatibility. Only the registered default is
    allowed; arbitrary paths are rejected without inspecting/deserializing them.
    Research .joblib exports produced by src.train are not app dependencies.
    """
    validate_stage(stage)
    try:
        requested = Path(model_dir)
        registered = requested == Path('models') or requested.resolve() == (ROOT/'models').resolve()
    except (TypeError, ValueError, OSError):
        registered = False
    if not registered:
        raise ValueError('Unregistered model location: serialized model files are never loaded by this application.')
    from src.provisioning import prepare_models
    return _validate_bundle(prepare_models()[stage], stage)


def predict(values: dict, stage: str, model_dir=Path('models')) -> dict:
    frame = validate_inputs(values, stage)
    bundle = load_bundle(stage, model_dir)
    point = float(np.clip(bundle['pipeline'].predict(frame)[0], 0, 20))
    if not np.isfinite(point):
        raise ValueError('Model returned a nonfinite prediction.')
    radius = bundle['interval_radius']
    warnings, reliability = assess_reliability(values, frame, bundle['reference'])
    return {'prediction': point, 'lower': max(0., point-radius), 'upper': min(20., point+radius),
        'model_name': bundle['model_name'], 'stage': stage, 'active_features': list(bundle['active_features']),
        'warnings': warnings, 'reliability': reliability, 'evaluation': deepcopy(bundle['evaluation']),
        'nominal_coverage': bundle['nominal_coverage'], 'evaluation_context': bundle['evaluation_context'],
        'model_version': bundle['model_version'], 'provisioning_checksum': bundle['provisioning_checksum']}


def compare_scenario(original: dict, adjusted: dict, stage: str, model_dir=Path('models')) -> dict:
    original_result = predict(original, stage, model_dir)
    adjusted_result = predict(adjusted, stage, model_dir)
    return {'original': original_result, 'adjusted': adjusted_result,
        'delta': adjusted_result['prediction']-original_result['prediction'],
        'changes': {f: [original[f], adjusted[f]] for f in FEATURES[stage] if original[f] != adjusted[f]}}
