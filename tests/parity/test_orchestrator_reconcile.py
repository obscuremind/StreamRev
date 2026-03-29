from pathlib import Path

from src.core.process.orchestrator import RuntimeOrchestrator


class DummyProc:
    def __init__(self, pid: int):
        self.pid = pid


def test_reconcile_restarts_missing_critical(monkeypatch, tmp_path):
    orch = RuntimeOrchestrator()
    orch.pid_file = tmp_path / "state.json"
    orch.repo_root = Path(".")

    # Dead API PID in state
    orch.pid_file.write_text('{"api": {"pid": 999, "name": "api", "command": ["x"], "critical": true}}')

    monkeypatch.setattr(orch, "_is_alive", lambda pid: False)

    started = []

    def fake_popen(*args, **kwargs):
        started.append(args[0])
        return DummyProc(12345)

    monkeypatch.setattr("subprocess.Popen", fake_popen)

    result = orch.reconcile()
    assert "api" in result["restarted"]
    assert started


def test_reconcile_when_healthy(monkeypatch, tmp_path):
    orch = RuntimeOrchestrator()
    orch.pid_file = tmp_path / "state.json"
    orch.pid_file.write_text('{"api": {"pid": 123, "name": "api", "command": ["x"], "critical": true}}')

    monkeypatch.setattr(orch, "_is_alive", lambda pid: True)

    result = orch.reconcile()
    assert result["restarted"] == []
    assert result["healthy"] == ["api"]
