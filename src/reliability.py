"""Descriptive interval diagnostics and training-only input support checks.

Novelty warnings are heuristics. They neither certify in-distribution inputs nor
validate interval coverage for a new student, institution, or missingness pattern.
"""
import math
import numpy as np
from sklearn.neighbors import NearestNeighbors
from src.schema import FEATURES, SPECS


def wilson_interval(successes, n, z=1.959963984540054):
    if n <= 0 or not 0 <= successes <= n:
        raise ValueError('Coverage requires 0 <= successes <= n and n > 0.')
    p = successes / n
    denominator = 1 + z*z/n
    center = (p + z*z/(2*n)) / denominator
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    return [max(0., center-radius), min(1., center+radius)]


def coverage_summary(y, lower, upper):
    y, lower, upper = [np.asarray(v, dtype=float) for v in (y, lower, upper)]
    if y.ndim != 1 or len(y) == 0 or y.shape != lower.shape or y.shape != upper.shape:
        raise ValueError('Coverage arrays must be aligned nonempty vectors.')
    if not all(np.isfinite(v).all() for v in (y, lower, upper)) or (lower > upper).any():
        raise ValueError('Coverage arrays must be finite and ordered.')
    covered = int(np.sum((y >= lower) & (y <= upper)))
    return {'n': int(len(y)), 'covered': covered, 'coverage': covered/len(y),
            'coverage_95ci': wilson_interval(covered, len(y)),
            'mean_interval_width': float(np.mean(upper-lower))}


def interval_diagnostics(y, lower, upper, X):
    """Predeclared descriptive groups; not fairness or conditional coverage proof."""
    result = {'overall': coverage_summary(y, lower, upper), 'groups': {},
              'group_caveat': 'Descriptive small-sample groups; no simultaneous or conditional coverage guarantee.'}
    masks = {'age_15_17': X['age'].to_numpy() <= 17,
             'age_18_22': X['age'].to_numpy() >= 18,
             'studytime_1_2': X['studytime'].to_numpy() <= 2,
             'studytime_3_4': X['studytime'].to_numpy() >= 3,
             'interval_midpoint_below_10': (np.asarray(lower)+np.asarray(upper))/2 < 10,
             'interval_midpoint_at_least_10': (np.asarray(lower)+np.asarray(upper))/2 >= 10}
    # The last pair groups by interval midpoint, a prediction-derived value, not G3.
    for label, mask in masks.items():
        if np.any(mask):
            result['groups'][label] = coverage_summary(np.asarray(y)[mask], np.asarray(lower)[mask], np.asarray(upper)[mask])
    return result


def build_reference(X_train, preprocessor):
    """Fit novelty geometry exclusively on training rows, without G3."""
    transformed = np.asarray(preprocessor.fit_transform(X_train), dtype=float)
    distances, _ = NearestNeighbors(n_neighbors=2).fit(transformed).kneighbors(transformed)
    threshold = float(np.quantile(distances[:, 1], .95, method='higher'))
    support = {}
    for field in X_train.columns:
        values = X_train[field].dropna()
        if 'options' in SPECS[field]:
            support[field] = {'counts': {str(k): int(v) for k,v in values.value_counts().items()}}
        else:
            support[field] = {'min': float(values.min()), 'max': float(values.max()),
                              'counts': {str(float(k)): int(v) for k,v in values.value_counts().items()}}
    return {'preprocessor': preprocessor, 'transformed_train': transformed,
            'distance_threshold': threshold, 'support': support, 'n_train': len(X_train),
            'method': 'Nearest-neighbor distance in training-fitted standardized/one-hot space; threshold95th percentile of training leave-one-out distances.'}


def assess_reliability(values, frame, reference):
    messages = []
    for field in reference['support']:
        value = values[field]
        if value is None:
            messages.append(f'{field} is missing and was imputed; interval coverage for missing inputs has not been validated.')
            continue
        support = reference['support'][field]
        if 'min' in support and not support['min'] <= value <= support['max']:
            messages.append(f'{field}={value} is outside observed training support [{support["min"]:g}, {support["max"]:g}].')
        counts = support['counts']
        key = str(value) if 'options' in SPECS[field] else str(float(value))
        if counts.get(key, 0) < 5:
            messages.append(f'{field}={value} was observed in fewer than five training records; this estimate has limited support.')
    transformed = np.asarray(reference['preprocessor'].transform(frame), dtype=float)
    matrix = reference['transformed_train']
    distance = float(np.sqrt(np.sum((matrix-transformed[0])**2, axis=1)).min())
    if distance > reference['distance_threshold'] + 1e-12:
        messages.append('This joint input profile is unusually distant from the training records. Treat the estimate and interval with additional caution.')
    return messages, {'status': 'caution' if messages else 'in_distribution',
                      'nearest_distance': distance, 'distance_threshold': reference['distance_threshold'],
                      'n_train': reference['n_train'],
                      'method': reference['method'],
                      'caveat': 'Heuristic support check only; an unflagged profile is not proof of applicability or coverage.'}
