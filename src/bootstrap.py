"""XC_VM-compatible bootstrap helpers for StreamRev.

This module centralizes runtime directory preparation and environment bootstrapping
similarly to XC_VM's bootstrap entrypoint.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.core.config import settings


@dataclass(frozen=True)
class RuntimePaths:
    """Resolved runtime paths used across service/update/streaming flows."""

    base: Path
    content: Path
    backups: Path
    tmp: Path
    signals: Path
    logs: Path
    epg: Path


def _required_subdirs() -> Iterable[Path]:
    yield Path("content")
    yield Path("content/archive")
    yield Path("content/epg")
    yield Path("content/playlists")
    yield Path("content/streams")
    yield Path("content/vod")
    yield Path("content/video")
    yield Path("backups")
    yield Path("tmp")
    yield Path("signals")
    yield Path("logs")


def resolve_runtime_paths() -> RuntimePaths:
    base = Path(settings.BASE_DIR)
    return RuntimePaths(
        base=base,
        content=Path(settings.CONTENT_DIR),
        backups=Path(settings.BACKUP_DIR),
        tmp=Path(settings.TMP_DIR),
        signals=base / "signals",
        logs=base / "logs",
        epg=Path(settings.EPG_DIR),
    )


def ensure_runtime_dirs() -> RuntimePaths:
    paths = resolve_runtime_paths()
    for rel in _required_subdirs():
        os.makedirs(paths.base / rel, exist_ok=True)
    return paths


def main() -> int:
    paths = ensure_runtime_dirs()
    print(f"Runtime prepared under: {paths.base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
