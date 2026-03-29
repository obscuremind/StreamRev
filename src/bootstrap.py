"""XC_VM-compatible bootstrap helpers for StreamRev."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from src.core.config import settings
from src.core.logging.logger import logger

BootstrapContext = Literal["minimal", "cli", "stream", "admin", "service"]


@dataclass(frozen=True)
class RuntimePaths:
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


def _apply_context(paths: RuntimePaths, context: BootstrapContext) -> None:
    if context in {"admin", "service"}:
        os.makedirs(paths.base / "www", exist_ok=True)

    if context in {"stream", "service"}:
        os.makedirs(paths.content / "streams", exist_ok=True)
        if not os.path.exists(settings.FFMPEG_PATH):
            logger.warning("FFmpeg not found at configured path: %s", settings.FFMPEG_PATH)

    if context == "cli":
        os.environ["STREAMREV_CONTEXT"] = "cli"


def ensure_runtime_dirs(context: BootstrapContext = "minimal") -> RuntimePaths:
    paths = resolve_runtime_paths()
    for rel in _required_subdirs():
        os.makedirs(paths.base / rel, exist_ok=True)

    _apply_context(paths, context)
    logger.info("Bootstrap context initialized: %s", context)
    return paths


def main() -> int:
    paths = ensure_runtime_dirs(context="cli")
    print(f"Runtime prepared under: {paths.base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
