"""Training-only selection, untouched calibration and a reused historical test audit."""
import hashlib
import json
import math
import platform
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import make_scorer, mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from src.data import DATA_PATH, ROOT, load_data
from src.estimators import LatestGradeRegressor
from src.reliability import build_reference, interval_diagnostics
from src.schema import FEATURES, SCHEMA_VERSION, SPECS, validate_stage

SEED = 42
ALPHA = .10
SELECTION_RULE = ('Simplest candidate within one standard error of minimum five-fold training CV MAE. '
                  'Fixed order: mean, median, updated G2 persistence, updated prior-grades linear, full linear, '
                  'Ridge alpha1/10/100, gradient boosting, random forest. No selection on calibration or test.')
EVALUATION_CONTEXT = ('Reused historical 130-row test audit, already inspected in Phase1; not fresh holdout evidence. '
                      'Selection uses training CV only. External/prospective validation remains necessary.')


def split_indices(n):
    train_cal, test = train_test_split(np.arange(n), test_size=.2, random_state=SEED)
    train, calibration = train_test_split(train_cal, test_size=.25, random_state=SEED)
    return train, calibration, test


def build_preprocessor(fields, scale=True):
    categorical = [f for f in fields if 'options' in SPECS[f]]
    numeric = [f for f in fields if f not in categorical]
    numeric_steps = [('impute', SimpleImputer(strategy='median'))]
    if scale:
        numeric_steps.append(('scale', StandardScaler()))
    return ColumnTransformer([
        ('numeric', Pipeline(numeric_steps), numeric),
        ('categorical', Pipeline([('impute', SimpleImputer(strategy='most_frequent')),
                                 ('encode', OneHotEncoder(handle_unknown='ignore', sparse_output=False))]), categorical)])


def build_pipeline(stage, model, fields=None):
    validate_stage(stage)
    fields = FEATURES[stage] if fields is None else fields
    return Pipeline([('preprocess', build_preprocessor(fields, scale=not isinstance(model, LatestGradeRegressor))),
                     ('model', model)])


def candidate_pipelines(stage):
    """Declared before the iteration2 experiment; insertion order is simplicity priority."""
    definitions = {
        'DummyRegressor': (DummyRegressor(strategy='mean'), None),
        'MedianRegressor': (DummyRegressor(strategy='median'), None),
    }
    if stage == 'updated':
        definitions.update({'G2Persistence': (LatestGradeRegressor(), ['G2']),
                            'PriorGradesLinear': (LinearRegression(), ['G1', 'G2'])})
    definitions.update({
        'LinearRegression': (LinearRegression(), None),
        'Ridge(alpha=1)': (Ridge(alpha=1), None),
        'Ridge(alpha=10)': (Ridge(alpha=10), None),
        'Ridge(alpha=100)': (Ridge(alpha=100), None),
        'GradientBoostingRegressor': (GradientBoostingRegressor(n_estimators=100, learning_rate=.05, max_depth=2, min_samples_leaf=5, random_state=SEED), None),
        'RandomForestRegressor': (RandomForestRegressor(n_estimators=250, min_samples_leaf=3, max_features=.8, random_state=SEED, n_jobs=1), None),
    })
    return {name: build_pipeline(stage, model, fields) for name, (model, fields) in definitions.items()}


def bounded_mae(y, prediction):
    return mean_absolute_error(y, np.clip(prediction, 0, 20))


def bounded_rmse(y, prediction):
    return float(np.sqrt(mean_squared_error(y, np.clip(prediction, 0, 20))))


def bounded_r2(y, prediction):
    return r2_score(y, np.clip(prediction, 0, 20))


def metrics(y, predicted):
    return {'mae': float(mean_absolute_error(y, predicted)),
            'rmse': float(np.sqrt(mean_squared_error(y, predicted))), 'r2': float(r2_score(y, predicted))}


def conformal_radius(residuals, alpha=ALPHA):
    errors = np.asarray(residuals, dtype=float)
    if errors.ndim != 1 or not len(errors) or not np.isfinite(errors).all() or (errors < 0).any() or not 0 < alpha < 1:
        raise ValueError('Need finite nonnegative calibration residuals and alpha in (0,1).')
    rank = math.ceil((len(errors) + 1) * (1 - alpha))
    return float('inf') if rank > len(errors) else float(np.sort(errors)[rank - 1])


def select_simplest(comparison):
    if not comparison:
        raise ValueError('No candidates supplied.')
    best = min(comparison, key=lambda row: row['mae'])
    cutoff = best['mae'] + best['mae_se']
    return next(row['model'] for row in comparison if row['mae'] <= cutoff + 1e-12), cutoff


def train_all():
    frame = load_data()
    train, calibration, test = split_indices(len(frame))
    (ROOT/'models').mkdir(exist_ok=True)
    (ROOT/'reports').mkdir(exist_ok=True)
    scoring = {'mae': make_scorer(bounded_mae, greater_is_better=False),
               'rmse': make_scorer(bounded_rmse, greater_is_better=False), 'r2': make_scorer(bounded_r2)}
    all_metrics, prediction_rows, importance_rows = {}, [], []
    for stage, features in FEATURES.items():
        X, y = frame[features], frame['G3']
        candidates = candidate_pipelines(stage)
        comparison = []
        for name, pipeline in candidates.items():
            cv = cross_validate(pipeline, X.iloc[train], y.iloc[train],
                                cv=KFold(5, shuffle=True, random_state=SEED), scoring=scoring,
                                error_score='raise', n_jobs=1)
            fold_mae = -cv['test_mae']
            comparison.append({'model': name, 'mae': float(fold_mae.mean()),
                'rmse': float(-cv['test_rmse'].mean()), 'r2': float(cv['test_r2'].mean()),
                'mae_std': float(fold_mae.std(ddof=1)), 'mae_se': float(fold_mae.std(ddof=1)/np.sqrt(5)),
                'fold_mae': fold_mae.tolist()})
        selected, cutoff = select_simplest(comparison)
        pipeline = candidates[selected].fit(X.iloc[train], y.iloc[train])
        calibration_prediction = np.clip(pipeline.predict(X.iloc[calibration]), 0, 20)
        radius = conformal_radius(np.abs(y.iloc[calibration].to_numpy()-calibration_prediction))
        predicted = np.clip(pipeline.predict(X.iloc[test]), 0, 20)
        lower, upper = np.maximum(0, predicted-radius), np.minimum(20, predicted+radius)
        diagnostics = interval_diagnostics(y.iloc[test].to_numpy(), lower, upper, X.iloc[test])
        test_metrics = metrics(y.iloc[test], predicted)
        test_metrics.update({key: diagnostics['overall'][key] for key in ['coverage','mean_interval_width']})
        baseline_names = ['DummyRegressor', 'MedianRegressor']
        if stage == 'updated':
            baseline_names += ['G2Persistence', 'PriorGradesLinear']
        baselines = {}
        for name in baseline_names:
            baseline_pipeline = candidates[name].fit(X.iloc[train], y.iloc[train])
            baselines[name] = metrics(y.iloc[test], np.clip(baseline_pipeline.predict(X.iloc[test]), 0, 20))
        result = {'selected_model': selected, 'cv_results': comparison, 'test': test_metrics,
            'baseline_test': baselines['DummyRegressor'], 'baselines': baselines,
            'split_sizes': {'train': len(train), 'calibration': len(calibration), 'test': len(test)},
            'interval_nominal_coverage': 1-ALPHA, 'interval_radius': radius,
            'interval_diagnostics': diagnostics, 'selection_rule': SELECTION_RULE,
            'selection_cutoff_mae': cutoff, 'evaluation_context': EVALUATION_CONTEXT}
        all_metrics[stage] = result
        active_features = ['G2'] if selected == 'G2Persistence' else (['G1', 'G2'] if selected == 'PriorGradesLinear' else features)
        reference = build_reference(X.iloc[train][active_features], build_preprocessor(active_features))
        bundle = {'pipeline': pipeline, 'stage': stage, 'features': features,
            'model_name': selected, 'active_features': active_features, 'interval_radius': radius, 'schema_version': SCHEMA_VERSION, 'artifact_version': 2,
            'sklearn_version': sklearn.__version__, 'dataset_sha256': hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
            'seed': SEED, 'nominal_coverage': 1-ALPHA, 'evaluation': result, 'reference': reference,
            'evaluation_context': EVALUATION_CONTEXT}
        joblib.dump(bundle, ROOT/'models'/f'{stage}.joblib')
        for idx, truth, point, low, high in zip(test, y.iloc[test], predicted, lower, upper):
            prediction_rows.append({'stage': stage, 'row_id': int(idx), 'actual': float(truth), 'predicted': float(point),
                'residual': float(truth-point), 'lower': float(low), 'upper': float(high)})
        importance = permutation_importance(pipeline, X.iloc[calibration], y.iloc[calibration], scoring=scoring['mae'], n_repeats=20, random_state=SEED)
        for feature, value, std in zip(features, importance.importances_mean, importance.importances_std):
            importance_rows.append({'stage': stage, 'feature': feature, 'importance': float(value), 'std': float(std)})
        print(f'{stage}: {selected}; test {test_metrics}; baselines {baselines}', flush=True)
    (ROOT/'reports'/'metrics.json').write_text(json.dumps(all_metrics, indent=2), encoding='utf-8', newline='\n')
    pd.DataFrame(prediction_rows).to_csv(ROOT/'reports'/'predictions.csv', index=False, lineterminator='\n')
    pd.DataFrame(importance_rows).to_csv(ROOT/'reports'/'importance.csv', index=False, lineterminator='\n')
    summary = {'rows': len(frame), 'columns': len(frame.columns), 'missing': frame.isna().sum().to_dict(),
        'target': 'G3', 'scale': [0,20], 'subject': 'Portuguese', 'duplicate_full_rows': int(frame.duplicated().sum()),
        'numeric_summary': frame.select_dtypes('number').describe().to_dict(),
        'feature_distributions': {f: {str(k): int(v) for k,v in frame[f].value_counts().sort_index().items()} for f in FEATURES['updated']},
        'correlations': frame[FEATURES['early'][:6]+['G1','G2','G3']].corr().to_dict()}
    (ROOT/'reports'/'data_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8', newline='\n')
    audit = {'seed': SEED, 'train': train.tolist(), 'calibration': calibration.tolist(), 'test': test.tolist(),
        'dataset_sha256': hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
        'python': platform.python_version(), 'sklearn': sklearn.__version__, 'numpy': np.__version__, 'pandas': pd.__version__,
        'cv': '5-fold KFold(shuffle=True, random_state=42), training subset only', 'selection_rule': SELECTION_RULE,
        'evaluation_context': EVALUATION_CONTEXT, 'point_postprocessing': 'clip all CV/calibration/test/inference predictions to [0,20]'}
    (ROOT/'reports'/'split_manifest.json').write_text(json.dumps(audit, indent=2), encoding='utf-8', newline='\n')
    from src.audit import write_audit_reports
    write_audit_reports(all_metrics, frame)
    return all_metrics


if __name__ == '__main__':
    train_all()
