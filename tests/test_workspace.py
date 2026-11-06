"""Workspace exports retain settings as well as marks, without hidden disk writes."""
import copy
import json

import pytest


def old_export():
    return {"version": 1, "courses": {"Statistics": [
        {"name": "Exam", "weight": 60, "mark": 80},
        {"name": "Project", "weight": 40, "mark": None},
    ]}}


def test_legacy_course_export_migrates_to_complete_workspace():
    from app.persistence import validate_workspace
    legacy = old_export()
    before = copy.deepcopy(legacy)
    workspace = validate_workspace(legacy)
    assert workspace["version"] == 2
    assert workspace["courses"] == legacy["courses"]
    assert workspace["targets"] == {"Statistics": 70}
    assert isinstance(workspace["thresholds"], dict) and workspace["thresholds"]
    assert legacy == before


def test_workspace_roundtrip_preserves_targets_thresholds_and_isolation():
    from app.persistence import validate_workspace, workspace_payload
    courses = old_export()["courses"]
    targets = {"Statistics": 85}
    thresholds = {"Distinction": 85, "Pass": 50, "Below pass": 0}
    encoded = workspace_payload(courses, targets, thresholds)
    restored = validate_workspace(json.loads(json.dumps(encoded, allow_nan=False)))
    assert restored == {"version": 2, "courses": courses, "targets": targets, "thresholds": thresholds}
    restored["courses"]["Statistics"][0]["mark"] = 0
    restored["targets"]["Statistics"] = 1
    restored["thresholds"]["Pass"] = 1
    assert courses["Statistics"][0]["mark"] == 80
    assert targets["Statistics"] == 85
    assert thresholds["Pass"] == 50


@pytest.mark.parametrize("target", [-1, 101, float("nan"), float("inf"), True, "70"])
def test_workspace_invalid_targets_rejected(target):
    from app.persistence import validate_workspace
    payload = {"version": 2, "courses": old_export()["courses"],
               "targets": {"Statistics": target}, "thresholds": {"Pass": 50}}
    with pytest.raises((ValueError, TypeError)):
        validate_workspace(payload)


@pytest.mark.parametrize("targets", [{}, {"Other": 70}, {"Statistics": 70, "Other": 60}])
def test_workspace_target_names_must_match_courses(targets):
    from app.persistence import validate_workspace
    payload = {"version": 2, "courses": old_export()["courses"],
               "targets": targets, "thresholds": {"Pass": 50}}
    with pytest.raises((ValueError, TypeError)):
        validate_workspace(payload)


@pytest.mark.parametrize("thresholds", [{}, [], {"Pass": float("nan")}, {"Pass": True}, {"Pass": 101}])
def test_workspace_invalid_thresholds_rejected(thresholds):
    from app.persistence import validate_workspace
    payload = {"version": 2, "courses": old_export()["courses"],
               "targets": {"Statistics": 70}, "thresholds": thresholds}
    with pytest.raises((ValueError, TypeError)):
        validate_workspace(payload)


def test_workspace_rejects_partial_invalid_import_without_mutation():
    from app.persistence import validate_workspace
    payload = {"version": 2, "courses": old_export()["courses"],
               "targets": {"Statistics": 70}, "thresholds": {"Pass": 50}}
    payload["courses"]["Invalid"] = [{"name": "Exam", "weight": 120, "mark": None}]
    payload["targets"]["Invalid"] = 70
    before = copy.deepcopy(payload)
    with pytest.raises(ValueError):
        validate_workspace(payload)
    assert payload == before
