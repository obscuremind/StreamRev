"""XC_VM-like service command wrapper for StreamRev."""
from __future__ import annotations

import argparse

from src.bootstrap import ensure_runtime_dirs
from src.core.process.orchestrator import orchestrator


def start() -> int:
    ensure_runtime_dirs(context="service")
    return orchestrator.start_all()


def stop() -> int:
    return orchestrator.stop_all()


def status() -> int:
    status_map = orchestrator.status()
    if not status_map:
        print("streamrev status: stopped")
        return 1

    running = [name for name, meta in status_map.items() if meta["running"]]
    critical_down = [
        name for name, meta in status_map.items() if (not meta["running"] and meta.get("critical", True))
    ]

    for name, meta in status_map.items():
        state = "running" if meta["running"] else "stopped"
        crit = "critical" if meta.get("critical", True) else "optional"
        print(f"{name}: {state} ({crit}, pid={meta['pid']})")

    if critical_down:
        print(f"streamrev status: degraded (critical down: {', '.join(critical_down)})")
        return 2

    if running:
        print(f"streamrev status: running ({len(running)}/{len(status_map)} services)")
        return 0

    print("streamrev status: stopped")
    return 1


def heal() -> int:
    result = orchestrator.reconcile()
    if result["restarted"]:
        print("restarted critical services:", ", ".join(result["restarted"]))
    else:
        print("all critical services healthy")
    return 0


def restart() -> int:
    stop()
    return start()


def main() -> int:
    parser = argparse.ArgumentParser(description="StreamRev service command wrapper")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "heal"])
    args = parser.parse_args()
    return {
        "start": start,
        "stop": stop,
        "restart": restart,
        "status": status,
        "heal": heal,
    }[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
