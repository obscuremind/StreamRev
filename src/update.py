"""XC_VM-like update entrypoint for StreamRev.

Applies migrations and prepares runtime directories.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.bootstrap import ensure_runtime_dirs


def run() -> int:
    ensure_runtime_dirs()
    repo_root = Path(__file__).resolve().parent.parent

    alembic_ini = repo_root / "alembic.ini"
    if alembic_ini.exists():
        cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
        print("Running:", " ".join(cmd))
        return subprocess.call(cmd, cwd=str(repo_root))

    print("No alembic.ini found; falling back to schema-based migration command.")
    cmd = [sys.executable, "-m", "src.cli.console", "cmd:migrate"]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(repo_root))


if __name__ == "__main__":
    raise SystemExit(run())
