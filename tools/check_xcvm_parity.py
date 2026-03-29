#!/usr/bin/env python3
"""Quick local parity signal checker (StreamRev-side only)."""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def count(pattern: str) -> int:
    total = 0
    for p in (ROOT / "src").rglob("*.py"):
        text = p.read_text(errors="ignore")
        total += len(re.findall(pattern, text))
    return total


def exists(rel: str) -> bool:
    return (ROOT / rel).exists()


if __name__ == "__main__":
    print("XC_VM parity local signals")
    print("=========================")
    print(f"orchestrator: {'yes' if exists('src/core/process/orchestrator.py') else 'no'}")
    print(f"drm provider: {'yes' if exists('src/streaming/drm/provider.py') else 'no'}")
    print(f"install script: {'yes' if exists('infrastructure/scripts/install_ubuntu.sh') else 'no'}")
    print(f"parity tests: {'yes' if exists('tests/parity/test_baseline.py') else 'no'}")
    print("python 'pass' count:", count(r'\bpass\b'))
    print("NotImplementedError count:", count(r'NotImplementedError'))
