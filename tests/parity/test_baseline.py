import json
from pathlib import Path

from src.bootstrap import ensure_runtime_dirs
from src.core.process.orchestrator import orchestrator
from src.core.config import settings
from src.streaming.drm.provider import DRMProvider


def test_bootstrap_contexts():
    paths = ensure_runtime_dirs(context="service")
    assert paths.base.exists()
    assert (paths.base / "tmp").exists()


def test_orchestrator_plan_has_core_processes():
    names = [p.name for p in orchestrator.process_plan()]
    assert "api" in names
    assert "watchdog" in names
    assert "queue-worker" in names
    assert "scheduler-worker" in names


def test_orchestrator_api_process_has_uvicorn_command():
    api = [p for p in orchestrator.process_plan() if p.name == "api"][0]
    joined = " ".join(api.command)
    assert "uvicorn" in joined
    assert "src.main:app" in joined


def test_drm_static_provider_returns_key(monkeypatch):
    fixture = Path("tests/parity/fixtures/drm_static_keys.json").read_text()
    monkeypatch.setattr(settings, "DRM_PROVIDER_MODE", "static")
    monkeypatch.setattr(settings, "DRM_STATIC_KEYS_JSON", fixture)
    provider = DRMProvider()
    keys = __import__("asyncio").run(provider.get_keys(stream_id=100, username="alice"))
    assert len(keys) == 1
    assert keys[0].kid == "abc"
