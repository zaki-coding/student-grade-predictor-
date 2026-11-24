"""Run the two grade experiments from verified, local UCI archives."""

import argparse
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from threadpoolctl import threadpool_limits

from src.university_data import (
    FIRST_TERM, OU_ACTIVITY, OU_HISTORY, PT_FEATURES, chronological_parts,
    load_oulad_delays, load_portalegre,
)

SEED = 42


def metrics(target, predicted):
    return {"mae": round(float(mean_absolute_error(target, predicted)), 4),
            "rmse": round(float(root_mean_squared_error(target, predicted)), 4)}


def predict(train, holdout, spec, maximum):
    method, fields = spec
    median = train["score"].median()
    if method == "median":
        return np.full(len(holdout), median)
    if method == "carry":
        return holdout[fields[0]].fillna(median).to_numpy()
    regressor = (LinearRegression() if method == "linear" else
                 HistGradientBoostingRegressor(max_iter=100, max_leaf_nodes=15,
                                               early_stopping=False, random_state=SEED))
    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), regressor)
    model.fit(train[fields], train["score"])
    return model.predict(holdout[fields]).clip(0, maximum)


def model_specs(academic, baselines, activity=None):
    specs = {"median": ("median", [])}
    specs.update({name: ("carry", [field]) for name, field in baselines.items()})
    for method in ("linear", "boosting"):
        specs[method] = (method, academic)
        if activity:
            specs[method + "_clicks"] = (method, academic + [activity])
    if activity:
        specs["clicks_only"] = ("boosting", [activity])
    return specs


def paired_error_interval(rows, prediction, baseline, student):
    delta = np.abs(rows["score"].to_numpy() - prediction) - np.abs(rows["score"].to_numpy() - baseline)
    ids = rows[student].to_numpy() if student else rows.index.to_numpy()
    groups = pd.DataFrame({"id": ids, "delta": delta}).groupby("id")["delta"].agg(["sum", "size"])
    rng = np.random.default_rng(SEED)
    sums, sizes = groups["sum"].to_numpy(), groups["size"].to_numpy()
    draws = []
    for _ in range(1000):
        sample = rng.integers(len(groups), size=len(groups))
        draws.append(sums[sample].sum() / sizes[sample].sum())
    return np.quantile(draws, [0.025, 0.975]).round(4).tolist()


def compare_last_mark(test, prediction, last):
    delta = mean_absolute_error(test["score"], prediction) - mean_absolute_error(test["score"], last)
    return {"mae_model_minus_last": round(float(delta), 4),
            "student_bootstrap_95": paired_error_interval(test, prediction, last, "id_student")}


def evaluate(parts, specs, maximum, course, student=None):
    train, valid, test = parts
    validation = {name: metrics(valid["score"], predict(train, valid, spec, maximum))
                  for name, spec in specs.items()}
    def best(names):
        return min(names, key=lambda name: (validation[name]["mae"], name))

    baseline = best(name for name, (method, _) in specs.items() if method in {"median", "carry"})
    selected = best(name for name, (method, _) in specs.items() if method in {"linear", "boosting"})
    development = pd.concat([train, valid])
    preds = {name: predict(development, test, spec, maximum) for name, spec in specs.items()}
    courses = {}
    for name in sorted(test[course].unique()):
        mask = test[course].eq(name)
        subset = test[mask]
        row = {"rows": len(subset), "baseline": metrics(subset["score"], preds[baseline][mask]),
               "selected": metrics(subset["score"], preds[selected][mask])}
        if student:
            other_courses = development.loc[development[course].ne(name)]
            row["unseen_course"] = metrics(subset["score"], predict(other_courses, subset, specs[selected], maximum))
            row["unseen_baseline"] = metrics(subset["score"], predict(other_courses, subset, specs[baseline], maximum))
        courses[str(name)] = row
    counts = [{"rows": len(part), "students": part[student].nunique() if student else len(part),
               "assessments": part["id_assessment"].nunique() if student else None}
              for part in parts]
    result = {"splits": counts, "validation": validation, "selected": selected, "baseline": baseline,
              "test": {name: metrics(test["score"], p) for name, p in preds.items()},
              "paired_mae_difference_95": paired_error_interval(test, preds[selected], preds[baseline], student),
              "by_course": courses}
    if student:
        result["paired_vs_last"] = compare_last_mark(test, preds[selected], preds["last"])
    prior = "last_grade" if student else FIRST_TERM[0]
    result["test_without_prior"] = int(test[prior].isna().sum())
    return result


def evaluate_oulad(path):
    specs = model_specs(OU_HISTORY, {"last": "last_grade", "prior_mean": "mean_grade"}, OU_ACTIVITY)
    tables = load_oulad_delays(path, [28, 14, 42])
    primary_delay, primary_rows = next(tables)
    primary_parts = chronological_parts(primary_rows)
    report = evaluate(primary_parts, specs, 100, "code_module", "id_student")
    selected = report["selected"]
    methods = ["median", "last", "prior_mean", selected]

    def history_counts(parts):
        return {name: {"rows": len(part), "with_prior": int(part["prior_count"].gt(0).sum())}
                for name, part in zip(("train", "validation", "test"), parts)}

    report["primary_feedback_days"] = primary_delay
    comparisons = {str(primary_delay): {
        "history": history_counts(primary_parts),
        "validation": {name: report["validation"][name] for name in methods},
        "test": {name: report["test"][name] for name in methods},
        "paired_vs_last": report["paired_vs_last"],
    }}
    for delay, rows in tables:
        parts = chronological_parts(rows)
        train, valid, test = parts
        # Refit the primary recipe on the labels available under this delay.
        development = pd.concat([train, valid])
        predictions = {name: predict(development, test, specs[name], 100) for name in methods}
        comparisons[str(delay)] = {
            "history": history_counts(parts),
            "validation": {name: metrics(valid["score"], predict(train, valid, specs[name], 100))
                           for name in methods},
            "test": {name: metrics(test["score"], predictions[name]) for name in methods},
            "paired_vs_last": compare_last_mark(test, predictions[selected], predictions["last"]),
        }
    report["feedback_delays"] = comparisons
    return report


def portuguese_parts(rows):
    development, test = train_test_split(rows, test_size=0.2, random_state=SEED)
    train, valid = train_test_split(development, test_size=0.25, random_state=SEED)
    return train, valid, test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", choices=["oulad", "portalegre"])
    parser.add_argument("archive")
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        if args.experiment == "oulad":
            report = evaluate_oulad(args.archive)
        else:
            rows, coverage = load_portalegre(args.archive)
            specs = model_specs(PT_FEATURES, {"first_term": FIRST_TERM[0]})
            report = evaluate(portuguese_parts(rows), specs, 20, "Course")
            report["target_coverage"] = coverage
    print(json.dumps(report, indent=2, default=int))


if __name__ == "__main__":
    main()
