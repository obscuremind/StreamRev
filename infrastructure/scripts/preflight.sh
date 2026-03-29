#!/usr/bin/env bash
set -euo pipefail

command -v python3 >/dev/null || { echo "python3 missing"; exit 1; }
command -v ffmpeg >/dev/null || { echo "ffmpeg missing"; exit 1; }

python3 - <<'PY'
import importlib
for pkg in ["fastapi", "sqlalchemy", "uvicorn"]:
    importlib.import_module(pkg)
print("python deps: ok")
PY

echo "preflight: OK"
