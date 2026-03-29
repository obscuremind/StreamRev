from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

from src.core.config import settings
from src.core.logging.logger import logger


@dataclass
class ManagedProcess:
    name: str
    command: List[str]
    critical: bool = True


class RuntimeOrchestrator:
    """Small process supervisor used by `src.service`."""

    def __init__(self) -> None:
        base = Path(settings.BASE_DIR)
        self.pid_file = base / "tmp" / "streamrev-supervisor.json"
        self.repo_root = base.parent

    def process_plan(self) -> List[ManagedProcess]:
        python = sys.executable
        return [
            ManagedProcess(
                name="api",
                command=[
                    python,
                    "-m",
                    "uvicorn",
                    "src.main:app",
                    "--host",
                    settings.SERVER_HOST,
                    "--port",
                    str(settings.SERVER_PORT),
                    "--workers",
                    "4",
                ],
                critical=True,
            ),
            ManagedProcess(
                name="watchdog",
                command=[python, "-m", "src.cli.console", "watchdog"],
                critical=False,
            ),
            ManagedProcess(
                name="monitor",
                command=[python, "-m", "src.cli.console", "monitor"],
                critical=False,
            ),
            ManagedProcess(
                name="queue-worker",
                command=[python, "-m", "src.cli.workers", "queue", "--interval", "30"],
                critical=False,
            ),
            ManagedProcess(
                name="scheduler-worker",
                command=[python, "-m", "src.cli.workers", "scheduler", "--interval", "60"],
                critical=False,
            ),
            ManagedProcess(
                name="migration-worker",
                command=[python, "-m", "src.cli.workers", "migrations", "--interval", "21600"],
                critical=False,
            ),
        ]

    def critical_processes(self) -> List[ManagedProcess]:
        return [proc for proc in self.process_plan() if proc.critical]

    def _read_state(self) -> Dict[str, dict]:
        if not self.pid_file.exists():
            return {}
        try:
            return json.loads(self.pid_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_state(self, state: Dict[str, dict]) -> None:
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(json.dumps(state, indent=2, sort_keys=True))

    @staticmethod
    def _is_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _spawn(self, proc: ManagedProcess, state: Dict[str, dict]) -> None:
        popen = subprocess.Popen(
            proc.command,
            cwd=str(self.repo_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )
        state[proc.name] = {"pid": popen.pid, **asdict(proc)}
        logger.info("Started '%s' with PID %s", proc.name, popen.pid)

    def start_all(self) -> int:
        state = self._read_state()
        for proc in self.process_plan():
            current = state.get(proc.name)
            if current and self._is_alive(int(current.get("pid", 0))):
                logger.info("Process '%s' already running (%s)", proc.name, current["pid"])
                continue
            self._spawn(proc, state)

        self._write_state(state)
        return 0

    def reconcile(self) -> dict:
        """Ensure all critical processes are running; restart if missing."""
        state = self._read_state()
        restarted: List[str] = []
        healthy: List[str] = []

        for proc in self.critical_processes():
            current = state.get(proc.name)
            if current and self._is_alive(int(current.get("pid", 0))):
                healthy.append(proc.name)
                continue
            self._spawn(proc, state)
            restarted.append(proc.name)

        self._write_state(state)
        return {"healthy": healthy, "restarted": restarted}

    def stop_all(self) -> int:
        state = self._read_state()
        if not state:
            logger.info("No managed processes found")
            return 0

        for name, meta in state.items():
            pid = int(meta.get("pid", 0))
            if pid <= 0:
                continue
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                logger.info("Stopped '%s' (%s)", name, pid)
            except ProcessLookupError:
                logger.info("Process '%s' (%s) already stopped", name, pid)
            except OSError as exc:
                logger.warning("Failed to stop '%s' (%s): %s", name, pid, exc)

        self.pid_file.unlink(missing_ok=True)
        return 0

    def status(self) -> Dict[str, dict]:
        state = self._read_state()
        out: Dict[str, dict] = {}
        for name, meta in state.items():
            pid = int(meta.get("pid", 0))
            out[name] = {
                "pid": pid,
                "running": self._is_alive(pid) if pid > 0 else False,
                "command": meta.get("command", []),
                "critical": bool(meta.get("critical", True)),
            }
        return out


orchestrator = RuntimeOrchestrator()
