"""Build research tables from the two original UCI ZIP files."""

from hashlib import file_digest, sha256
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

OU_HASH = "f2ed1902616c1fe8d2824d872c0b7d2d72be435bf0124d077044fe4be2c6d3e4"
PT_HASH = "e90e55fd65ec462ae283ebeb2cca409319e3460ed898d8754f62fb35cc83a65d"
PRESENTATION = ["code_module", "code_presentation"]
ENTRY = PRESENTATION + ["id_student"]
OU_HISTORY = ["last_grade", "mean_grade", "prior_count"]
OU_ACTIVITY = "clicks_last_14_days"
FIRST_TERM = [f"Curricular units 1st sem ({field})" for field in
              ("grade", "approved", "enrolled", "evaluations", "credited", "without evaluations")]
PT_FEATURES = FIRST_TERM + ["Admission grade"]


def verified_zip(path, expected):
    with Path(path).open("rb") as source:
        digest = file_digest(source, sha256).hexdigest()
    if digest != expected:
        raise ValueError(f"Unexpected SHA-256 for {Path(path).name}: {digest}")
    return ZipFile(path)


def assessment_rows(schedule, results, lag=28):
    if lag < 0:
        raise ValueError("Grade delay must be nonnegative.")
    schedule = schedule.loc[schedule["assessment_type"].eq("TMA") & schedule["date"].notna()]
    grades = results.merge(schedule, on="id_assessment", validate="many_to_one")
    grades = grades.loc[grades["is_banked"].eq(0) & grades["date_submitted"].notna()
                       & grades["score"].between(0, 100)].copy()
    grades["available"] = grades[["date", "date_submitted"]].max(axis=1) + lag
    grades["cutoff"] = grades["date"] - 7
    rows = []
    for _, course in grades.groupby(PRESENTATION):
        for due, target in course.groupby("date"):
            cutoff = due - 7
            # A score for an early submission might already be known at the cutoff.
            target = target.loc[target["date_submitted"] > cutoff].copy()
            prior = course.loc[(course["date"] < due) & (course["available"] < cutoff)]
            summary = (prior.sort_values(["date", "id_assessment"]).groupby("id_student")["score"]
                       .agg(last_grade="last", mean_grade="mean", prior_count="size"))
            target = target.join(summary, on="id_student")
            target["prior_count"] = target["prior_count"].fillna(0)
            rows.append(target)
    return pd.concat(rows, ignore_index=True)


def activity_totals(chunks, schedule):
    totals = []
    windows = {key: group["cutoff"].unique() for key, group in schedule.groupby(PRESENTATION)}
    for chunk in chunks:
        for key, activity in chunk.groupby(PRESENTATION):
            for cutoff in windows.get(key, ()):
                recent = activity.loc[activity["date"].between(cutoff - 14, cutoff - 1)]
                if recent.empty:
                    continue
                clicks = recent.groupby("id_student")["sum_click"].sum().reset_index()
                clicks["code_module"], clicks["code_presentation"] = key
                clicks["cutoff"] = cutoff
                totals.append(clicks)
    keys = ENTRY + ["cutoff"]
    if not totals:
        return pd.DataFrame(columns=keys + [OU_ACTIVITY])
    return (pd.concat(totals).groupby(keys, as_index=False)["sum_click"].sum()
            .rename(columns={"sum_click": OU_ACTIVITY}))


def load_oulad(path):
    with verified_zip(path, OU_HASH) as archive:
        schedule = pd.read_csv(archive.open("assessments.csv"), na_values="?")
        results = pd.read_csv(archive.open("studentAssessment.csv"), na_values="?")
        rows = assessment_rows(schedule, results)
        # The February 2014 run overlaps the October 2014 test run.
        rows = rows.loc[rows["code_presentation"].ne("2014B")].copy()
        with archive.open("studentVle.csv") as stream:
            chunks = pd.read_csv(stream, chunksize=250_000, usecols=ENTRY + ["date", "sum_click"])
            clicks = activity_totals(chunks, rows)
    rows = rows.merge(clicks, on=ENTRY + ["cutoff"], how="left", validate="many_to_one")
    rows[OU_ACTIVITY] = rows[OU_ACTIVITY].fillna(0)
    return rows


def chronological_parts(rows):
    period = rows["code_presentation"]
    test = rows.loc[period.eq("2014J")].copy()
    # February and October starts are at least 215 days apart. The buffer
    # also keeps late, still-unmarked training submissions out of validation.
    valid = rows.loc[period.eq("2013J") & rows["available"].le(320)
                     & ~rows["id_student"].isin(test["id_student"])].copy()
    later = pd.concat([valid["id_student"], test["id_student"]])
    train = rows.loc[period.eq("2013B") & rows["available"].le(180)
                     & ~rows["id_student"].isin(later)].copy()
    return train, valid, test


def load_portalegre(path):
    with verified_zip(path, PT_HASH) as archive:
        frame = pd.read_csv(archive.open("data.csv"), sep=";")
    return portalegre_rows(frame)


def portalegre_rows(frame):
    grade = frame["Curricular units 2nd sem (grade)"]
    approved = frame["Curricular units 2nd sem (approved)"]
    eligible = grade.between(0, 20, inclusive="right") & approved.gt(0)
    coverage = pd.crosstab(frame["Target"], eligible).to_dict()
    rows = frame.loc[eligible, PT_FEATURES + ["Course"]].copy()
    rows["score"] = grade[eligible]
    # A zero first-term average has the same no-approved-units pattern.
    rows[FIRST_TERM[0]] = rows[FIRST_TERM[0]].where(rows[FIRST_TERM[0]].gt(0))
    return rows, coverage
