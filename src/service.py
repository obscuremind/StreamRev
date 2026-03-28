"""XC_VM-like service command wrapper for StreamRev.

Usage:
  PYTHONPATH=$(pwd) python -m src.service start
  PYTHONPATH=$(pwd) python -m src.service status
"""
from __future__ import annotations

import argparse
import signal
import subprocess
import sys
from pathlib import Path

from src.bootstrap import ensure_runtime_dirs
from src.core.config import settings

PID_FILE = Path(settings.BASE_DIR) / "tmp" / "streamrev.pid"


def _is_running(pid: int) -> bool:
    try:
        Path(f"/proc/{pid}").exists() or __import__("os").kill(pid, 0)
        return True
    except Exception:
        return False


def start() -> int:
    ensure_runtime_dirs()
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if _is_running(pid):
                print(f"streamrev already running (pid={pid})")
                return 0
        except ValueError:
            pass

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.main:app",
        "--host",
        settings.SERVER_HOST,
        "--port",
        str(settings.SERVER_PORT),
        "--workers",
        "4",
    ]
    proc = subprocess.Popen(cmd, cwd=str(Path(settings.BASE_DIR).parent))
    PID_FILE.write_text(str(proc.pid))
    print(f"streamrev started (pid={proc.pid})")
    return 0


def stop() -> int:
    if not PID_FILE.exists():
        print("streamrev is not running (no pid file)")
        return 0

    pid = int(PID_FILE.read_text().strip())
    try:
        __import__("os").kill(pid, signal.SIGTERM)
        print(f"stopped streamrev (pid={pid})")
    except ProcessLookupError:
        print(f"process {pid} not found; cleaning stale pid file")
    PID_FILE.unlink(missing_ok=True)
    return 0


def status() -> int:
    if not PID_FILE.exists():
        print("streamrev status: stopped")
        return 1

    try:
        pid = int(PID_FILE.read_text().strip())
    except ValueError:
        print("streamrev status: invalid pid file")
        return 2

    if _is_running(pid):
        print(f"streamrev status: running (pid={pid})")
        return 0
    print("streamrev status: stopped (stale pid file)")
    return 1


def restart() -> int:
    stop()
    return start()


def main() -> int:
    parser = argparse.ArgumentParser(description="StreamRev service command wrapper")
    parser.add_argument("command", choices=["start", "stop", "restart", "status"])
    args = parser.parse_args()
    return {"start": start, "stop": stop, "restart": restart, "status": status}[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
