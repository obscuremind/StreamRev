import os
import platform
import subprocess

import psutil
from fastapi import APIRouter, Depends
from src.domain.models import User
from src.streaming.engine import streaming_engine

from .dependencies import get_current_admin

router = APIRouter(prefix="/diagnostics", tags=["Admin Diagnostics"])


@router.get("")
def get_diagnostics(admin: User = Depends(get_current_admin)):
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    ffmpeg_version = _get_version(settings.FFMPEG_PATH)
    python_version = platform.python_version()
    return {
        "system": {
            "platform": platform.platform(),
            "python_version": python_version,
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "load_avg": list(os.getloadavg()),
        },
        "memory": {"total": mem.total, "used": mem.used, "available": mem.available, "percent": mem.percent},
        "disk": {"total": disk.total, "used": disk.used, "free": disk.free, "percent": disk.percent},
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
        },
        "ffmpeg": {"path": settings.FFMPEG_PATH, "version": ffmpeg_version},
        "streaming": streaming_engine.get_stats(),
        "content_sizes": _get_content_sizes(),
    }


@router.get("/processes")
def get_processes(admin: User = Depends(get_current_admin)):
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "cmdline"]):
        try:
            if "ffmpeg" in (p.info["name"] or "").lower() or "uvicorn" in (p.info["name"] or "").lower():
                procs.append(
                    {
                        "pid": p.info["pid"],
                        "name": p.info["name"],
                        "cpu": p.info["cpu_percent"],
                        "memory": p.info["memory_percent"],
                        "cmdline": " ".join(p.info["cmdline"] or [])[:200],
                    }
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return {"processes": procs}


@router.get("/certificates")
def get_certificates(admin: User = Depends(get_current_admin)):
    nginx_conf = settings.NGINX_CONF_DIR or os.path.join(settings.BASE_DIR, "bin", "nginx", "conf")
    cert_path = os.path.join(nginx_conf, "server.crt")
    if not os.path.exists(cert_path):
        return {"status": "no_certificate", "path": cert_path}
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-dates", "-subject", "-issuer"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {"status": "ok", "path": cert_path, "info": result.stdout}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/nginx/reload")
def reload_nginx(admin: User = Depends(get_current_admin)):
    try:
        result = subprocess.run(
            [settings.NGINX_BIN, "-s", "reload"], capture_output=True, text=True, timeout=10
        )
        return {"status": "ok" if result.returncode == 0 else "error", "output": result.stderr or result.stdout}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/nginx/test")
def test_nginx(admin: User = Depends(get_current_admin)):
    try:
        result = subprocess.run([settings.NGINX_BIN, "-t"], capture_output=True, text=True, timeout=10)
        return {"status": "ok" if result.returncode == 0 else "error", "output": result.stderr or result.stdout}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _get_version(binary_path: str) -> str:
    try:
        result = subprocess.run([binary_path, "-version"], capture_output=True, text=True, timeout=5)
        return result.stdout.split("\n")[0] if result.returncode == 0 else "not found"
    except Exception:
        return "not found"


def _get_content_sizes() -> dict:
    sizes = {}
    for name in ["streams", "archive", "vod", "epg"]:
        path = os.path.join(settings.CONTENT_DIR, name)
        if os.path.isdir(path):
            total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(path) for f in fs)
            sizes[name] = total
        else:
            sizes[name] = 0
    return sizes
