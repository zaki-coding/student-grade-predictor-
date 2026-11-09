"""Compare fixed grade models on the original training rows only."""

import hashlib
import io
import json
import platform

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import HuberRegressor, QuantileRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold, LeaveOneGroupOut, cross_val_predict

from src.data import EXPECTED_CSV_SHA256, ROOT, validate_dataset
from src.provisioning import APPROVED_MODELS
from src.schema import FEATURES
from src.train import SEED, build_pipeline, candidate_pipelines, metrics, split_indices


def compare_candidates(predictors, target, candidates, cv, bounds, *, groups=None):
    """Return paired out-of-fold predictions on a known numeric target scale."""
    return {
        name: np.clip(cross_val_predict(pipeline, predictors, target, cv=cv, groups=groups), *bounds)
        for name, pipeline in candidates.items()
    }


def _error_by_grade_band(target, predicted):
    bands = {
        "0": target == 0,
        "1–9": (target > 0) & (target < 10),
        "10–20": target >= 10,
    }
    residual = target - predicted
    return {
        name: {
            "n": int(mask.sum()),
            "mae": float(np.abs(residual[mask]).mean()),
            "mean_residual": float(residual[mask].mean()),
        }
        for name, mask in bands.items()
        if mask.any()
    }


def evaluate_development(frame: pd.DataFrame) -> dict:
    """Use the historical training partition for all fitting and scoring."""
    train, _, _ = split_indices(len(frame))
    development = frame.iloc[train]
    target = development["G3"].to_numpy()
    school = development["school"].to_numpy()
    bounds = (0, 20)
    folds = KFold(n_splits=5, shuffle=True, random_state=SEED)
    results = {}
    for stage, fields in FEATURES.items():
        predictors = development[fields]
        original = candidate_pipelines(stage)
        current = APPROVED_MODELS[stage]
        if stage == "early":
            names = ("MedianRegressor", current)
            trial = build_pipeline(stage, HuberRegressor(max_iter=1000))
            trial_name = "Huber"
        else:
            names = ("MedianRegressor", current, "PriorGradesLinear")
            trial = build_pipeline(stage, QuantileRegressor(quantile=0.5, alpha=0.01), ["G1", "G2"])
            trial_name = "PriorGradesMedian"
        candidates = {name: original[name] for name in names}
        candidates[trial_name] = trial
        predictions = compare_candidates(predictors, target, candidates, folds, bounds)
        current_mae = mean_absolute_error(target, predictions[current])
        comparison = {}
        for name, prediction in predictions.items():
            scores = metrics(target, prediction)
            comparison[name] = {**scores, "mae_difference_vs_current": scores["mae"] - current_mae}

        transfer = compare_candidates(
            predictors, target, {current: candidates[current], trial_name: trial},
            LeaveOneGroupOut(), bounds, groups=school,
        )
        school_transfer = {}
        for code in sorted(set(school)):
            held_out = school == code
            school_transfer[code] = {
                "n": int(held_out.sum()),
                "mae": {
                    name: float(mean_absolute_error(target[held_out], prediction[held_out]))
                    for name, prediction in transfer.items()
                },
            }
        results[stage] = {
            "current": current,
            "development_cv": comparison,
            "current_error_by_grade_band": _error_by_grade_band(target, predictions[current]),
            "school_transfer": school_transfer,
        }
    return {"n": len(development), "seed": SEED, "stages": results}


def main():
    raw = (ROOT / "resources" / "student-por.csv").read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_CSV_SHA256:
        raise ValueError("The bundled Portuguese dataset does not match the expected checksum.")
    frame = validate_dataset(pd.read_csv(io.BytesIO(raw), sep=";"))
    result = evaluate_development(frame)
    result["environment"] = {
        "python": platform.python_version(),
        "scikit_learn": sklearn.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
