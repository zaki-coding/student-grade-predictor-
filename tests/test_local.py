"""Local launch stays loopback-bound without constraining hosted configuration."""
from types import SimpleNamespace

from src import local


def test_local_launcher_sets_loopback_and_repository_config(monkeypatch):
    captured = {}
    def run(command, **kwargs):
        captured.update(command=command, **kwargs)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(local.subprocess, 'run', run)
    assert local.main(['--port', '8512']) == 0
    command = captured['command']
    assert command[command.index('--server.address') + 1] == '127.0.0.1'
    assert command[command.index('--server.port') + 1] == '8512'
    assert captured['cwd'] == local.ROOT
