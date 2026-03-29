"""Long-running worker entrypoints used by orchestrator."""
from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time

_RUNNING = True


def _handle_stop(_signum, _frame):
    global _RUNNING
    _RUNNING = False


def _run_console(command: str) -> int:
    return subprocess.call([sys.executable, "-m", "src.cli.console", command])


def queue_worker(interval: int) -> int:
    while _RUNNING:
        _run_console("cron:queue")
        time.sleep(interval)
    return 0


def scheduler_worker(interval: int) -> int:
    while _RUNNING:
        for cmd in ["cron:connections", "cron:recordings", "cron:audit", "cron:archive"]:
            if not _RUNNING:
                break
            _run_console(cmd)
        time.sleep(interval)
    return 0


def migration_worker(interval: int) -> int:
    while _RUNNING:
        _run_console("cmd:migrate")
        time.sleep(interval)
    return 0


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    parser = argparse.ArgumentParser(description="StreamRev worker launcher")
    parser.add_argument("worker", choices=["queue", "scheduler", "migrations"])
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()

    if args.worker == "queue":
        return queue_worker(args.interval)
    if args.worker == "scheduler":
        return scheduler_worker(args.interval)
    return migration_worker(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
