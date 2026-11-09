"""Release UX uses only synthetic records and keeps visitor sessions separate."""
from datetime import date
import json
from pathlib import Path
import tomllib

import pytest
from streamlit.testing.v1 import AppTest

from app.persistence import decode_workspace_bytes

ROOT = Path(__file__).resolve().parents[1]


def app():
    return AppTest.from_file(str(ROOT / 'app' / 'Home.py'), default_timeout=30).run()


def test_one_click_demo_replaces_only_this_session_and_preserves_example_settings():
    visitor = app()
    other = app()
    visitor.session_state['targets'] = {'My first course': 99}
    visitor.session_state['thresholds'] = {'Private boundary': 1}
    visitor.session_state['threshold_editor'] = 'private draft'
    visitor.session_state['target_stale'] = 99
    visitor.session_state['scenario_stale'] = 1
    visitor.session_state['last_prediction'] = {'private': 'draft'}
    visitor.button(key='load_demo').click().run()
    assert not visitor.exception
    expected = json.loads((ROOT / 'docs' / 'example-semester.json').read_text(encoding='utf-8'))
    shift = date.today() - date(2026, 11, 9)
    for records in expected['courses'].values():
        for record in records:
            if 'due' in record:
                record['due'] = (date.fromisoformat(record['due']) + shift).isoformat()
    assert visitor.session_state['courses'] == expected['courses']
    assert visitor.session_state['planning'] == expected['planning']
    assert visitor.session_state['targets'] == expected['targets']
    assert visitor.session_state['thresholds'] == expected['thresholds']
    for key in ['threshold_editor', 'target_stale', 'scenario_stale', 'last_prediction']:
        assert key not in visitor.session_state
    assert list(other.session_state['courses']) == ['My first course']
    visitor.session_state['courses'][next(iter(expected['courses']))][0]['mark'] = 0
    visitor.button(key='load_demo').click().run()
    assert visitor.session_state['courses'] == expected['courses']


def test_demo_failure_preserves_workspace_and_does_not_disclose_server_path(monkeypatch):
    visitor = app()
    original = dict(visitor.session_state['courses'])
    real_read = Path.read_bytes

    def unreadable(path):
        if path.name == 'example-semester.json':
            raise OSError('secret/internal/operator/path')
        return real_read(path)

    monkeypatch.setattr(Path, 'read_bytes', unreadable)
    visitor.button(key='load_demo').click().run()
    assert not visitor.exception
    assert visitor.session_state['courses'] == original
    messages = ' '.join(element.value for element in visitor.info)
    assert 'could not be loaded' in messages
    assert 'secret/internal' not in messages


@pytest.mark.parametrize('raw', [b'', b'\xff', b'[]', b'{"version":1,"version":2}',
    b'{"version":2,"courses":{},"targets":{},"thresholds":{"A":NaN}}',
    b'[' * 2000 + b']' * 2000, b' ' * 1_000_001])
def test_untrusted_upload_rejected_with_safe_bounded_message(raw):
    with pytest.raises(ValueError) as error:
        decode_workspace_bytes(raw)
    assert len(str(error.value)) < 250
    assert '\xff' not in str(error.value)


def test_upload_parser_restores_v1_and_v2_without_aliasing():
    for payload in [
        {'version': 1, 'courses': {'Synthetic': [{'name': 'Quiz', 'weight': 20, 'mark': 80}]}},
        json.loads((ROOT / 'docs' / 'example-workspace.json').read_text(encoding='utf-8')),
    ]:
        restored = decode_workspace_bytes(json.dumps(payload).encode())
        assert restored['version'] == 2
        assert restored['courses'] == payload['courses']
        restored['courses'][next(iter(restored['courses']))][0]['mark'] = 0
        assert payload['courses'][next(iter(payload['courses']))][0]['mark'] != 0


def test_privacy_notices_explain_hosted_transmission_without_device_only_claim():
    visitor = app()
    text = ' '.join(element.value for element in visitor.markdown)
    assert 'hosting provider' in text
    assert 'synthetic' in text
    assert 'operational logs' in text
    assert 'shared model cache' in text
    assert 'stays on your device' not in text


def test_preparation_failure_is_safe_and_calculator_still_works(monkeypatch):
    import src.predict as inference

    def unavailable(*args, **kwargs):
        raise ValueError('secret/internal/operator/path')

    monkeypatch.setattr(inference, 'load_bundle', unavailable)
    visitor = app()
    visitor.radio(key='page').set_value('AI Predictor').run()
    assert not visitor.exception
    text = ' '.join(element.value for element in visitor.info)
    assert 'temporarily unavailable' in text
    assert 'secret/internal' not in text
    assert any(button.label == 'Retry model initialization' for button in visitor.button)
    visitor.radio(key='page').set_value('Grade Calculator').run()
    assert not visitor.exception
    assert any(metric.label == 'Earned contribution' for metric in visitor.metric)


def test_shared_cloud_config_bounds_uploads_hides_tracebacks_and_keeps_security_defaults():
    config = tomllib.loads((ROOT / '.streamlit' / 'config.toml').read_text(encoding='utf-8'))
    assert 'address' not in config['server']
    assert config['server']['maxUploadSize'] == 1
    assert config['client']['showErrorDetails'] == 'none'
    assert config['browser']['gatherUsageStats'] is False
    assert config['server'].get('enableCORS', True)
    assert config['server'].get('enableXsrfProtection', True)


def test_oversized_assessment_editor_does_not_poison_a_valid_workspace():
    import hashlib
    visitor = app()
    visitor.radio(key='page').set_value('Grade Calculator').run()
    before = [dict(row) for row in visitor.session_state['courses']['My first course']]
    digest = hashlib.sha256(b'My first course').hexdigest()[:12]
    visitor.session_state[f'assessments_{digest}_0'] = {
        'edited_rows': {}, 'deleted_rows': [],
        'added_rows': [{'name': 'Synthetic extra', 'weight': 0.0, 'mark': None} for _ in range(101)]}
    next(widget for widget in visitor.button if widget.label == 'Save assessments').click().run()
    assert not visitor.exception
    assert visitor.session_state['courses']['My first course'] == before
    assert any('not saved' in widget.value.lower() for widget in visitor.error)
