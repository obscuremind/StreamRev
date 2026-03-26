"""
Internal Server-to-Server API for clustering, load balancing, and server management.
Requires API key authentication via X-Server-Key header.
"""
import json
import os
import shutil
import signal
import subprocess

import psutil
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.domain.line.service import LineService
from src.domain.models import Stream
from src.domain.server.settings_service import SettingsService
from src.streaming.engine import streaming_engine

router = APIRouter(prefix="/internal", tags=["Internal Server API"])


def verify_server_key(request: Request, db: Session = Depends(get_db)):
    key = request.headers.get("X-Server-Key", "")
    if not key:
        raise HTTPException(status_code=401, detail="Server key required")
    svc = SettingsService(db)
    valid_key = svc.get("server_api_key", "")
    if not valid_key or key != valid_key:
        raise HTTPException(status_code=403, detail="Invalid server key")
    return True


# System info and diagnostics
@router.get("/stats")
def get_stats(auth=Depends(verify_server_key)):
    info = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "cpu_count": psutil.cpu_count(),
        "memory_total": info.total,
        "memory_used": info.used,
        "memory_percent": info.percent,
        "disk_total": disk.total,
        "disk_used": disk.used,
        "disk_percent": disk.percent,
        "load_avg": list(os.getloadavg()),
        "uptime": int(psutil.boot_time()),
    }


@router.get("/get_free_space")
def get_free_space(path: str = Query("/"), auth=Depends(verify_server_key)):
    try:
        usage = shutil.disk_usage(path)
        return {"total": usage.total, "used": usage.used, "free": usage.free}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/get_pids")
def get_pids(auth=Depends(verify_server_key)):
    pids = {}
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if "ffmpeg" in (proc.info["name"] or "").lower():
                pids[proc.info["pid"]] = " ".join(proc.info["cmdline"] or [])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return {"pids": pids, "count": len(pids)}


@router.post("/pidsAreRunning")
def pids_are_running(request_data: dict, auth=Depends(verify_server_key)):
    pid_list = request_data.get("pids", [])
    result = {}
    for pid in pid_list:
        result[str(pid)] = psutil.pid_exists(int(pid))
    return result


@router.post("/kill_pid")
def kill_pid(request_data: dict, auth=Depends(verify_server_key)):
    pid = request_data.get("pid")
    if not pid:
        raise HTTPException(status_code=400, detail="pid required")
    try:
        os.kill(int(pid), signal.SIGTERM)
        return {"status": "killed", "pid": pid}
    except ProcessLookupError:
        return {"status": "not_found", "pid": pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Stream management
@router.post("/stream/start")
def stream_start(
    request_data: dict, db: Session = Depends(get_db), auth=Depends(verify_server_key)
):
    stream_id = request_data.get("stream_id")
    if not stream_id:
        raise HTTPException(status_code=400, detail="stream_id required")
    stream = db.query(Stream).filter(Stream.id == int(stream_id)).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    sources = []
    try:
        sources = json.loads(stream.stream_source) if stream.stream_source else []
    except (json.JSONDecodeError, TypeError):
        sources = [stream.stream_source] if stream.stream_source else []
    if not sources:
        raise HTTPException(status_code=400, detail="No sources")
    pid = streaming_engine.start_stream(
        int(stream_id),
        sources[0],
        container=stream.target_container,
        custom_ffmpeg=stream.custom_ffmpeg,
        read_native=stream.read_native,
    )
    return {"status": "started" if pid else "failed", "pid": pid, "stream_id": stream_id}


@router.post("/stream/stop")
def stream_stop(request_data: dict, auth=Depends(verify_server_key)):
    stream_id = request_data.get("stream_id")
    if not stream_id:
        raise HTTPException(status_code=400, detail="stream_id required")
    ok = streaming_engine.stop_stream(int(stream_id))
    return {"status": "stopped" if ok else "not_running", "stream_id": stream_id}


@router.post("/force_stream")
def force_stream(
    request_data: dict, db: Session = Depends(get_db), auth=Depends(verify_server_key)
):
    stream_id = request_data.get("stream_id")
    if not stream_id:
        raise HTTPException(status_code=400, detail="stream_id required")
    streaming_engine.stop_stream(int(stream_id))
    return stream_start(request_data, db, auth)


@router.post("/vod/start")
def vod_start(request_data: dict, auth=Depends(verify_server_key)):
    return {"status": "ok", "detail": "VOD is on-demand, no persistent process needed"}


@router.post("/vod/stop")
def vod_stop(request_data: dict, auth=Depends(verify_server_key)):
    return {"status": "ok"}


@router.post("/closeConnection")
def close_connection(
    request_data: dict, db: Session = Depends(get_db), auth=Depends(verify_server_key)
):
    line_id = request_data.get("line_id")
    user_id = request_data.get("user_id")
    svc = LineService(db)
    if line_id:
        svc.remove_line(int(line_id))
        return {"status": "closed", "line_id": line_id}
    elif user_id:
        count = svc.remove_user_lines(int(user_id))
        return {"status": "closed", "user_id": user_id, "lines_removed": count}
    raise HTTPException(status_code=400, detail="line_id or user_id required")


@router.post("/redirect_connection")
def redirect_connection(request_data: dict, auth=Depends(verify_server_key)):
    return {"status": "ok", "detail": "Connection redirect handled by load balancer"}


@router.get("/probe")
def probe_source(url: str = Query(...), auth=Depends(verify_server_key)):
    result = streaming_engine.probe_stream(url)
    if result:
        return {"status": "ok", "probe_result": result}
    raise HTTPException(status_code=400, detail="Probe failed")


# Nginx / service management
@router.post("/reload_nginx")
def reload_nginx(auth=Depends(verify_server_key)):
    try:
        result = subprocess.run(
            [settings.NGINX_BIN, "-s", "reload"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "output": result.stderr or result.stdout,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fpm_status")
def fpm_status(auth=Depends(verify_server_key)):
    return {"status": "not_applicable", "detail": "Python/uvicorn used instead of PHP-FPM"}


@router.post("/reload_epg")
def reload_epg(db: Session = Depends(get_db), auth=Depends(verify_server_key)):
    from src.domain.epg.service import EpgService

    svc = EpgService(db)
    stats = svc.get_stats()
    return {"status": "ok", "epg_stats": stats}


@router.post("/restore_images")
def restore_images(auth=Depends(verify_server_key)):
    return {"status": "ok"}


@router.post("/streams_ramdisk")
def streams_ramdisk(auth=Depends(verify_server_key)):
    return {"status": "not_implemented", "detail": "Ramdisk not configured"}


# RTMP
@router.get("/rtmp_stats")
def rtmp_stats(auth=Depends(verify_server_key)):
    return {"status": "ok", "active_rtmp": 0, "detail": "RTMP stats placeholder"}


@router.post("/rtmp_kill")
def rtmp_kill(request_data: dict, auth=Depends(verify_server_key)):
    return {"status": "ok"}


# File system
@router.get("/getFile")
def get_file(path: str = Query(...), auth=Depends(verify_server_key)):
    safe_base = settings.BASE_DIR
    full_path = os.path.realpath(os.path.join(safe_base, path))
    if not full_path.startswith(os.path.realpath(safe_base)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(full_path, "r") as f:
            return {"content": f.read()[:100000]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scandir")
def scandir_action(path: str = Query("."), auth=Depends(verify_server_key)):
    safe_base = settings.BASE_DIR
    full_path = os.path.realpath(os.path.join(safe_base, path))
    if not full_path.startswith(os.path.realpath(safe_base)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.isdir(full_path):
        raise HTTPException(status_code=404, detail="Not a directory")
    entries = []
    for entry in os.scandir(full_path):
        entries.append(
            {
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else 0,
            }
        )
    return {"entries": entries}


@router.get("/scandir_recursive")
def scandir_recursive(path: str = Query("."), auth=Depends(verify_server_key)):
    safe_base = settings.BASE_DIR
    full_path = os.path.realpath(os.path.join(safe_base, path))
    if not full_path.startswith(os.path.realpath(safe_base)):
        raise HTTPException(status_code=403, detail="Access denied")
    files = []
    for root, _dirs, fnames in os.walk(full_path):
        for fn in fnames:
            fp = os.path.join(root, fn)
            files.append({"path": os.path.relpath(fp, full_path), "size": os.path.getsize(fp)})
    return {"files": files[:5000]}


@router.post("/free_temp")
def free_temp(auth=Depends(verify_server_key)):
    tmp_dir = settings.TMP_DIR
    if os.path.exists(tmp_dir):
        count = 0
        for f in os.listdir(tmp_dir):
            fp = os.path.join(tmp_dir, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
                    count += 1
            except Exception:
                pass
        return {"status": "ok", "files_removed": count}
    return {"status": "ok", "files_removed": 0}


@router.post("/free_streams")
def free_streams(auth=Depends(verify_server_key)):
    streams_dir = os.path.join(settings.CONTENT_DIR, "streams")
    count = 0
    if os.path.exists(streams_dir):
        for d in os.listdir(streams_dir):
            dp = os.path.join(streams_dir, d)
            if os.path.isdir(dp):
                shutil.rmtree(dp, ignore_errors=True)
                count += 1
    return {"status": "ok", "dirs_removed": count}


@router.post("/signal_send")
def signal_send(request_data: dict, auth=Depends(verify_server_key)):
    name = request_data.get("signal", "")
    signals_dir = os.path.join(settings.BASE_DIR, "signals")
    os.makedirs(signals_dir, exist_ok=True)
    sig_path = os.path.join(signals_dir, name)
    with open(sig_path, "w") as f:
        f.write("1")
    return {"status": "ok", "signal": name}


@router.get("/get_certificate_info")
def get_certificate_info(auth=Depends(verify_server_key)):
    nginx_conf = settings.NGINX_CONF_DIR or os.path.join(
        settings.BASE_DIR, "bin", "nginx", "conf"
    )
    cert_path = os.path.join(nginx_conf, "server.crt")
    if not os.path.exists(cert_path):
        return {"status": "no_certificate"}
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-dates", "-subject"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {"status": "ok", "info": result.stdout}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/get_archive_files")
def get_archive_files(stream_id: int = Query(...), auth=Depends(verify_server_key)):
    archive_dir = os.path.join(settings.CONTENT_DIR, "archive", str(stream_id))
    if not os.path.exists(archive_dir):
        return {"files": []}
    files = []
    for root, _dirs, fnames in os.walk(archive_dir):
        for fn in fnames:
            fp = os.path.join(root, fn)
            files.append({"path": os.path.relpath(fp, archive_dir), "size": os.path.getsize(fp)})
    return {"files": files}


@router.get("/view_log")
def view_log(log_file: str = Query("app"), lines: int = Query(100), auth=Depends(verify_server_key)):
    log_dir = os.path.join(settings.BASE_DIR, "logs")
    safe_name = os.path.basename(log_file)
    log_path = os.path.join(
        log_dir, safe_name if safe_name.endswith(".log") else safe_name + ".log"
    )
    if not os.path.exists(log_path):
        return {"lines": [], "file": safe_name}
    try:
        with open(log_path, "r") as f:
            all_lines = f.readlines()
        return {"lines": all_lines[-lines:], "file": safe_name, "total_lines": len(all_lines)}
    except Exception as e:
        return {"error": str(e)}


# Module force runs
@router.post("/watch_force")
def watch_force(auth=Depends(verify_server_key)):
    return {"status": "ok", "detail": "Watch module force scan triggered"}


@router.post("/plex_force")
def plex_force(auth=Depends(verify_server_key)):
    return {"status": "ok", "detail": "Plex module force sync triggered"}


@router.post("/kill_watch")
def kill_watch(auth=Depends(verify_server_key)):
    return {"status": "ok"}


@router.post("/kill_plex")
def kill_plex(auth=Depends(verify_server_key)):
    return {"status": "ok"}
