#!/usr/bin/env python3
"""
IPTV Panel CLI - Console command runner (XC_VM-equivalent surface).
Usage:
    python -m src.cli.console <command> [args]

Service / ops:
    cmd:service:start|stop|restart|status  - Manage uvicorn (panel HTTP)
    cmd:scanner       - Probe provider domains from stream sources
    cmd:balancer      - Report load-balancer / server assignment state
    cmd:archive       - Prune TV archive directories past per-stream retention
    cmd:ondemand      - start|stop|status <stream_id> for on-demand ffmpeg
    cmd:record        - List streams allowed to record and archive disk usage
    cmd:thumbnail     - Fetch channel icons into per-stream thumb files
    cmd:certbot       - Check TLS cert on disk (openssl); optional certbot renew
    cmd:signals       - List or clear signal files under data/signals
    cmd:tools         - rescue | ports | access-codes

Cron:
    cron:activity, cron:stats, cron:vod, cron:series, cron:errors,
    cron:lines-logs, cron:streams-logs, cron:providers, cron:certbot, cron:tmp
    (plus existing cron:* tasks)
"""
import glob
import json
import os
import signal
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.config import settings
from src.core.database import SessionLocal, Base, engine
from src.core.logging.logger import logger


def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def cmd_startup():
    logger.info("Starting IPTV Panel services...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified")
    logger.info("Startup complete")


def cmd_monitor():
    from src.streaming.engine import streaming_engine
    stats = streaming_engine.get_stats()
    print(f"Active streams: {stats['active']}")
    print(f"Total tracked: {stats['total_tracked']}")
    print(f"Failed: {stats['failed']}")

    from src.core.process.manager import ProcessManager
    sys_info = ProcessManager.get_system_info()
    print(f"\nCPU: {sys_info['cpu_percent']}%")
    print(f"Memory: {sys_info['memory']['percent']}%")
    print(f"Disk: {sys_info['disk']['percent']}%")


def cmd_watchdog():
    from src.streaming.engine import streaming_engine
    logger.info("Watchdog: Checking stream health...")
    active = streaming_engine.get_active_streams()
    restarted = 0
    for sid, info in active.items():
        if not info.get("running"):
            logger.warning(f"Stream {sid} is down, restarting...")
            streaming_engine.restart_stream(sid)
            restarted += 1
    logger.info(f"Watchdog complete: {restarted} streams restarted")


def cron_streams():
    logger.info("Running streams cron...")
    db = get_db()
    try:
        from src.domain.stream.service import StreamService
        svc = StreamService(db)
        stats = svc.get_stats()
        logger.info(f"Stream stats: {stats}")
    finally:
        db.close()


def cron_users():
    logger.info("Running users cron...")
    db = get_db()
    try:
        from src.domain.user.service import UserService
        from src.domain.models import User
        from datetime import datetime, timezone
        svc = UserService(db)
        now = datetime.now(timezone.utc)
        expired = db.query(User).filter(User.exp_date <= now, User.enabled == True).all()
        for user in expired:
            user.enabled = False
            logger.info(f"Disabled expired user: {user.username}")
        db.commit()
        logger.info(f"Users cron complete. Disabled {len(expired)} expired users.")
    finally:
        db.close()


def cron_epg():
    logger.info("Running EPG cron...")
    db = get_db()
    try:
        import json

        from src.domain.epg.service import EpgService
        from src.domain.server.settings_service import SettingsService

        svc = EpgService(db)
        cleared = svc.clear_old(days=7)

        settings_svc = SettingsService(db)
        sources = settings_svc.get("epg_sources", default=[])
        if isinstance(sources, str):
            try:
                sources = json.loads(sources)
            except (json.JSONDecodeError, TypeError):
                sources = []
        if not isinstance(sources, list):
            sources = []

        total_imported = 0
        for item in sources:
            if isinstance(item, str):
                url = item.strip()
            elif isinstance(item, dict):
                url = (item.get("url") or "").strip()
            else:
                url = ""
            if not url:
                continue
            try:
                n = svc.fetch_and_import(url)
                total_imported += n
                logger.info(f"EPG imported {n} programmes from {url}")
            except Exception as e:
                logger.warning(f"EPG fetch failed for {url}: {e}")

        linked = svc.link_channels()
        logger.info(
            f"EPG cron complete. Cleared {cleared} old entries, "
            f"imported {total_imported} programmes, linked {linked} channel rows."
        )
    finally:
        db.close()


def cron_cleanup():
    import time
    from datetime import datetime, timedelta

    from src.domain.models import Line, StreamLog

    logger.info("Running cleanup cron...")
    db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        q = db.query(Line).filter(Line.date < cutoff)
        stale_count = q.count()
        q.delete(synchronize_session=False)
        db.commit()
        logger.info(f"Removed {stale_count} stale line(s) older than 24h.")

        removed_tmp = 0
        tmp_dir = settings.TMP_DIR
        if os.path.isdir(tmp_dir):
            threshold = time.time() - 86400
            for root, _dirs, files in os.walk(tmp_dir):
                for name in files:
                    path = os.path.join(root, name)
                    try:
                        if os.path.isfile(path) and os.path.getmtime(path) < threshold:
                            os.remove(path)
                            removed_tmp += 1
                    except OSError:
                        pass
        logger.info(f"Removed {removed_tmp} temp file(s) older than 24h.")

        log_cutoff = datetime.utcnow() - timedelta(days=30)
        log_deleted = (
            db.query(StreamLog)
            .filter(StreamLog.date < log_cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(f"Deleted {log_deleted} stream log row(s) older than 30 days.")
    finally:
        db.close()


def cron_cache():
    logger.info("Running cache cron...")
    try:
        import redis

        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        r.ping()
        dbsize = r.dbsize()
        mem = r.info("memory")
        used = mem.get("used_memory_human", "?")
        db = get_db()
        try:
            from src.domain.server.settings_service import SettingsService

            SettingsService(db).set("last_redis_dbsize", dbsize, "int")
            SettingsService(db).set(
                "last_redis_memory_human", str(used), "string"
            )
        finally:
            db.close()
        logger.info(
            f"Cache cron complete. Redis dbsize={dbsize}, memory={used}."
        )
    except Exception as e:
        logger.warning(f"Cache cron: Redis unavailable or error: {e}")


def cron_servers():
    logger.info("Running servers cron...")
    db = get_db()
    try:
        from src.domain.server.service import ServerService
        svc = ServerService(db)
        stats = svc.get_stats()
        logger.info(f"Server stats: {stats}")
    finally:
        db.close()


def cron_backups():
    import shutil
    from datetime import datetime
    logger.info("Running backup cron...")
    backup_dir = os.path.join(settings.BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}"
    logger.info(f"Backup cron complete: {backup_name}")


def cmd_migrate():
    logger.info("Running database migrations...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database migration complete")


def cmd_create_admin():
    db = get_db()
    try:
        from src.domain.user.service import UserService
        svc = UserService(db)
        username = input("Admin username: ").strip() or "admin"
        password = input("Admin password: ").strip() or "admin"
        existing = svc.get_by_username(username)
        if existing:
            print(f"User '{username}' already exists")
            return
        svc.create({
            "username": username, "password": password,
            "is_admin": True, "enabled": True, "max_connections": 1,
        })
        print(f"Admin user '{username}' created successfully")
    finally:
        db.close()


def cmd_reset_admin():
    db = get_db()
    try:
        from src.domain.user.service import UserService
        svc = UserService(db)
        admin = svc.get_by_username("admin")
        if not admin:
            print("Admin user not found")
            return
        new_pass = input("New password: ").strip() or "admin"
        svc.update(admin.id, {"password": new_pass})
        print("Admin password reset successfully")
    finally:
        db.close()


def cmd_import_epg():
    url = input("EPG URL (XMLTV format): ").strip()
    if not url:
        print("URL required")
        return
    import urllib.request
    logger.info(f"Downloading EPG from {url}...")
    try:
        response = urllib.request.urlopen(url)
        content = response.read().decode("utf-8")
        db = get_db()
        try:
            from src.domain.epg.service import EpgService
            svc = EpgService(db)
            count = svc.import_xmltv(content)
            linked = svc.link_channels()
            print(f"Imported {count} EPG entries, linked {linked} rows to channels")
        finally:
            db.close()
    except Exception as e:
        print(f"Failed to import EPG: {e}")


def cmd_stats():
    db = get_db()
    try:
        from src.domain.stream.service import StreamService
        from src.domain.user.service import UserService
        from src.domain.vod.service import MovieService, SeriesService
        from src.domain.server.service import ServerService

        print("=" * 50)
        print("IPTV Panel Statistics")
        print("=" * 50)

        stats = StreamService(db).get_stats()
        print(f"\nStreams: {stats['total']} total, {stats['enabled']} enabled, {stats['disabled']} disabled")
        print(f"  Live: {stats['live']}, Movies: {stats['movies']}, Radio: {stats['radio']}")

        stats = UserService(db).get_stats()
        print(f"\nUsers: {stats['total']} total, {stats['active']} active, {stats['expired']} expired")
        print(f"  Online: {stats['online']}, Disabled: {stats['disabled']}, Trial: {stats['trial']}")

        stats = MovieService(db).get_stats()
        print(f"\nMovies: {stats['total']}")

        stats = SeriesService(db).get_stats()
        print(f"Series: {stats['total_series']}, Episodes: {stats['total_episodes']}")

        stats = ServerService(db).get_stats()
        print(f"\nServers: {stats['total']} total, {stats['online']} online, {stats['offline']} offline")

        from src.core.process.manager import ProcessManager
        sys_info = ProcessManager.get_system_info()
        print(f"\nSystem: CPU {sys_info['cpu_percent']}%, RAM {sys_info['memory']['percent']}%")
        print("=" * 50)
    finally:
        db.close()


def _project_root() -> str:
    return os.path.abspath(os.path.join(settings.BASE_DIR, ".."))


def _uvicorn_pid_path() -> str:
    os.makedirs(settings.TMP_DIR, exist_ok=True)
    return os.path.join(settings.TMP_DIR, "panel_uvicorn.pid")


def _kill_uvicorn_processes() -> int:
    import psutil

    killed = 0
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = proc.info["cmdline"] or []
            flat = " ".join(cmd)
            if "uvicorn" in flat and "src.main:app" in flat:
                proc.send_signal(signal.SIGTERM)
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return killed


def cmd_service_start():
    import psutil

    pid_path = _uvicorn_pid_path()
    if os.path.isfile(pid_path):
        try:
            with open(pid_path, "r") as f:
                old_pid = int(f.read().strip())
            if psutil.pid_exists(old_pid):
                print(f"Panel already running (PID {old_pid})")
                return
        except (ValueError, OSError):
            pass

    root = _project_root()
    env = os.environ.copy()
    env["PYTHONPATH"] = root
    log_dir = os.path.join(settings.BASE_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "uvicorn.log")
    out = open(log_path, "ab", buffering=0)
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.main:app",
        "--host",
        settings.SERVER_HOST,
        "--port",
        str(settings.SERVER_PORT),
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=root,
        env=env,
        stdout=out,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    with open(pid_path, "w") as f:
        f.write(str(proc.pid))
    print(f"Started panel uvicorn PID {proc.pid} (logs: {log_path})")


def cmd_service_stop():
    import psutil

    pid_path = _uvicorn_pid_path()
    stopped = 0
    if os.path.isfile(pid_path):
        try:
            with open(pid_path, "r") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                os.kill(pid, signal.SIGTERM)
                stopped += 1
                for _ in range(20):
                    if not psutil.pid_exists(pid):
                        break
                    time.sleep(0.5)
                if psutil.pid_exists(pid):
                    os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, ValueError, OSError):
            pass
        try:
            os.remove(pid_path)
        except OSError:
            pass
    extra = _kill_uvicorn_processes()
    stopped += extra
    print(f"Stop complete. Terminated {stopped} uvicorn process(es).")


def cmd_service_restart():
    cmd_service_stop()
    time.sleep(1)
    cmd_service_start()


def cmd_service_status():
    import psutil

    import httpx

    pid_path = _uvicorn_pid_path()
    if os.path.isfile(pid_path):
        try:
            with open(pid_path, "r") as f:
                pid = int(f.read().strip())
            alive = psutil.pid_exists(pid)
            print(f"Pid file: {pid_path} -> PID {pid} ({'running' if alive else 'stale'})")
        except (ValueError, OSError) as e:
            print(f"Pid file unreadable: {e}")
    else:
        print("No pid file (panel may not have been started via cmd:service:start)")

    host = "127.0.0.1" if settings.SERVER_HOST in ("0.0.0.0", "::") else settings.SERVER_HOST
    url = f"http://{host}:{settings.SERVER_PORT}/health"
    try:
        r = httpx.get(url, timeout=3.0)
        print(f"HTTP health {url}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"HTTP health check failed: {e}")


def cmd_scanner():
    import httpx

    db = get_db()
    try:
        from src.domain.stream.provider_service import ProviderService

        providers = ProviderService(db).get_providers()
        if not providers:
            print("No provider domains inferred from stream sources.")
            return
        for p in providers:
            domain = p.get("domain") or ""
            if not domain:
                continue
            url = f"https://{domain}/"
            try:
                r = httpx.head(url, timeout=8.0, follow_redirects=True)
                logger.info(
                    f"Scanner: {domain} -> HEAD {r.status_code} "
                    f"({p.get('stream_count', 0)} streams)"
                )
            except Exception as e:
                logger.warning(f"Scanner: {domain} unreachable: {e}")
        print(f"Scanned {len(providers)} provider domain(s). See logs for detail.")
    finally:
        db.close()


def cmd_balancer():
    db = get_db()
    try:
        from sqlalchemy import func

        from src.domain.models import Server, ServerStream

        servers = db.query(Server).order_by(Server.id.asc()).all()
        if not servers:
            print("No servers in database.")
            return
        for s in servers:
            n_streams = (
                db.query(func.count(ServerStream.id))
                .filter(ServerStream.server_id == s.id)
                .scalar()
                or 0
            )
            print(
                f"id={s.id} name={s.server_name!r} status={s.status} "
                f"clients={s.total_clients} streams_assigned={n_streams} "
                f"ip={s.server_ip}"
            )
    finally:
        db.close()


def cmd_archive():
    from datetime import datetime, timedelta

    db = get_db()
    try:
        from src.domain.models import Stream

        archive_root = os.path.join(settings.CONTENT_DIR, "archive")
        if not os.path.isdir(archive_root):
            print("No archive directory on disk.")
            return
        removed_dirs = 0
        for stream in db.query(Stream).filter(Stream.tv_archive.is_(True)).all():
            days = stream.tv_archive_duration or 7
            cutoff = datetime.utcnow().date() - timedelta(days=max(days, 1))
            sdir = os.path.join(archive_root, str(stream.id))
            if not os.path.isdir(sdir):
                continue
            for name in os.listdir(sdir):
                sub = os.path.join(sdir, name)
                if not os.path.isdir(sub):
                    continue
                try:
                    day = datetime.strptime(name, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if day < cutoff:
                    shutil.rmtree(sub, ignore_errors=True)
                    removed_dirs += 1
                    logger.info(
                        f"Archive prune: removed {sub} (stream {stream.id}, "
                        f"retention {days}d)"
                    )
        print(f"Archive maintenance done. Removed {removed_dirs} day-folder(s).")
    finally:
        db.close()


def cmd_ondemand():
    argv = sys.argv[2:]
    if len(argv) < 1:
        print("Usage: cmd:ondemand start <stream_id> | stop <stream_id> | status")
        return
    action = argv[0].lower()
    db = get_db()
    try:
        from src.domain.stream.service import StreamService
        from src.streaming.engine import streaming_engine

        if action == "status":
            active = streaming_engine.get_active_streams()
            print(json.dumps(active, indent=2, default=str))
            return
        if len(argv) < 2 or action not in ("start", "stop"):
            print("Usage: cmd:ondemand start <stream_id> | stop <stream_id> | status")
            return
        sid = int(argv[1])
        stream = StreamService(db).get_by_id(sid)
        if not stream:
            print(f"Stream {sid} not found")
            return
        sources = StreamService(db).get_sources(sid)
        if action == "start":
            if not sources:
                print("No sources configured for this stream")
                return
            pid = streaming_engine.start_stream(
                sid,
                sources[0],
                container=stream.target_container or "ts",
                custom_ffmpeg=stream.custom_ffmpeg,
                read_native=stream.read_native,
            )
            print(f"On-demand start stream {sid}: pid={pid}")
        else:
            ok = streaming_engine.stop_stream(sid)
            print(f"On-demand stop stream {sid}: ok={ok}")
    finally:
        db.close()


def cmd_record():
    db = get_db()
    try:
        from src.domain.models import Stream

        rec = (
            db.query(Stream)
            .filter(Stream.allow_record.is_(True), Stream.enabled.is_(True))
            .all()
        )
        archive_root = os.path.join(settings.CONTENT_DIR, "archive")
        print(f"Streams with recording enabled: {len(rec)}")
        total_bytes = 0
        for s in rec:
            ap = os.path.join(archive_root, str(s.id))
            sz = 0
            if os.path.isdir(ap):
                for root, _dirs, files in os.walk(ap):
                    for fn in files:
                        fp = os.path.join(root, fn)
                        try:
                            sz += os.path.getsize(fp)
                        except OSError:
                            pass
            total_bytes += sz
            print(f"  stream {s.id} {s.stream_display_name!r} archive_bytes={sz}")
        print(f"Total archive bytes (record-enabled streams): {total_bytes}")
    finally:
        db.close()


def cmd_thumbnail():
    import httpx

    db = get_db()
    try:
        from src.domain.models import Stream

        q = (
            db.query(Stream)
            .filter(Stream.enabled.is_(True), Stream.stream_type == 1)
            .all()
        )
        updated = 0
        for s in q:
            icon = (s.stream_icon or "").strip()
            if not icon.startswith("http"):
                continue
            base = os.path.join(settings.CONTENT_DIR, "streams", str(s.id))
            os.makedirs(base, exist_ok=True)
            dest = os.path.join(base, "thumb.jpg")
            try:
                r = httpx.get(icon, timeout=20.0, follow_redirects=True)
                if r.status_code == 200 and r.content:
                    with open(dest, "wb") as f:
                        f.write(r.content)
                    updated += 1
                    logger.info(f"Thumbnail saved for stream {s.id}")
            except Exception as e:
                logger.warning(f"Thumbnail failed stream {s.id}: {e}")
        print(f"Thumbnail job finished. Updated {updated} stream(s).")
    finally:
        db.close()


def cmd_certbot():
    argv = sys.argv[2:]
    nginx_conf = settings.NGINX_CONF_DIR or os.path.join(
        settings.BASE_DIR, "..", "bin", "nginx", "conf"
    )
    cert_path = os.path.join(nginx_conf, "server.crt")
    if os.path.isfile(cert_path):
        try:
            proc = subprocess.run(
                ["openssl", "x509", "-in", cert_path, "-noout", "-dates", "-subject"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            print(proc.stdout or proc.stderr)
        except FileNotFoundError:
            print("openssl not installed; cannot inspect certificate.")
        except Exception as e:
            print(f"Certificate inspect error: {e}")
    else:
        print(f"No certificate at {cert_path}")

    if "renew" in argv:
        try:
            proc = subprocess.run(
                ["certbot", "renew", "--non-interactive"],
                capture_output=True,
                text=True,
                timeout=600,
            )
            print(proc.stdout)
            if proc.stderr:
                print(proc.stderr)
            print(f"certbot renew exit code {proc.returncode}")
        except FileNotFoundError:
            print("certbot binary not found (install certbot to renew).")


def cmd_signals():
    argv = sys.argv[2:]
    sig_dir = os.path.join(settings.BASE_DIR, "signals")
    os.makedirs(sig_dir, exist_ok=True)
    if not argv:
        names = sorted(os.listdir(sig_dir))
        print("Signal files:", names)
        return
    if argv[0] == "clear" and len(argv) > 1:
        for n in argv[1:]:
            p = os.path.join(sig_dir, os.path.basename(n))
            if os.path.isfile(p):
                os.remove(p)
                print(f"Removed {p}")
        return
    print("Usage: cmd:signals  |  cmd:signals clear <name> [<name>...]")


def cmd_tools():
    argv = sys.argv[2:]
    if not argv:
        print("Usage: cmd:tools rescue | ports | access-codes")
        return
    sub = argv[0].lower()
    if sub == "rescue":
        from sqlalchemy import text

        db = get_db()
        try:
            db.execute(text("SELECT 1"))
            db.commit()
            print("Database: OK (SELECT 1)")
        except Exception as e:
            print(f"Database: FAILED {e}")
        finally:
            db.close()
        return
    if sub == "ports":
        import psutil

        listeners = []
        for c in psutil.net_connections(kind="inet"):
            if c.status == psutil.CONN_LISTEN and c.laddr:
                listeners.append(f"{c.laddr.ip}:{c.laddr.port} pid={c.pid}")
        listeners.sort()
        print("LISTEN sockets (sample):")
        for line in listeners[:80]:
            print(" ", line)
        if len(listeners) > 80:
            print(f"  ... ({len(listeners)} total)")
        return
    if sub in ("access-codes", "access"):
        db = get_db()
        try:
            from src.domain.server.settings_service import SettingsService

            keys = (
                "rescue_code",
                "server_api_key",
                "mag_access_code",
            )
            svc = SettingsService(db)
            for k in keys:
                v = svc.get(k, default="")
                show = "(empty)" if not v else ("*" * min(len(str(v)), 12))
                print(f"  {k}: {show}")
        finally:
            db.close()
        return
    print("Unknown subcommand. Use rescue | ports | access-codes")


def cron_activity():
    from datetime import datetime, timedelta

    from src.domain.models import UserActivity

    logger.info("Running activity cron...")
    db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(days=90)
        n = (
            db.query(UserActivity)
            .filter(UserActivity.date_start < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(f"Activity cron: deleted {n} old user_activity row(s).")
    finally:
        db.close()


def cron_stats():
    from datetime import datetime, timezone

    logger.info("Running stats cron...")
    db = get_db()
    try:
        from src.core.process.manager import ProcessManager
        from src.domain.server.settings_service import SettingsService

        payload = dict(ProcessManager.get_system_info())
        payload["captured_at"] = datetime.now(timezone.utc).isoformat()
        SettingsService(db).set("cron_last_stats", payload, "json")
        logger.info("Stats cron: wrote cron_last_stats setting.")
    finally:
        db.close()


def cron_vod():
    logger.info("Running VOD maintenance cron...")
    db = get_db()
    try:
        from sqlalchemy import or_

        from src.domain.models import Movie, SeriesEpisode

        empty_movies = (
            db.query(Movie)
            .filter(or_(Movie.stream_source.is_(None), Movie.stream_source == ""))
            .count()
        )
        empty_eps = (
            db.query(SeriesEpisode)
            .filter(
                or_(
                    SeriesEpisode.stream_source.is_(None),
                    SeriesEpisode.stream_source == "",
                )
            )
            .count()
        )
        vod_cache = os.path.join(settings.CONTENT_DIR, "vod")
        removed = 0
        if os.path.isdir(vod_cache):
            for name in os.listdir(vod_cache):
                p = os.path.join(vod_cache, name)
                if os.path.isfile(p) and time.time() - os.path.getmtime(p) > 86400 * 30:
                    try:
                        os.remove(p)
                        removed += 1
                    except OSError:
                        pass
        logger.info(
            f"VOD cron: empty movie rows={empty_movies}, empty episode rows={empty_eps}, "
            f"removed {removed} stale cache file(s)."
        )
    finally:
        db.close()


def cron_series():
    from datetime import datetime

    from sqlalchemy import func

    logger.info("Running series metadata cron...")
    db = get_db()
    try:
        from src.domain.models import Series, SeriesEpisode

        touched = 0
        for series in db.query(Series).all():
            cnt = (
                db.query(func.count(SeriesEpisode.id))
                .filter(SeriesEpisode.series_id == series.id)
                .scalar()
                or 0
            )
            if cnt == 0:
                continue
            series.last_modified = datetime.utcnow()
            touched += 1
        db.commit()
        logger.info(f"Series cron: refreshed last_modified on {touched} series.")
    finally:
        db.close()


def cron_errors():
    logger.info("Running error / log rotation cron...")
    log_dir = os.path.join(settings.BASE_DIR, "logs")
    if not os.path.isdir(log_dir):
        logger.info("No logs directory.")
        return
    max_bytes = 50 * 1024 * 1024
    rotated = 0
    for path in glob.glob(os.path.join(log_dir, "*.log")):
        try:
            if os.path.getsize(path) <= max_bytes:
                continue
            backup = path + ".1"
            shutil.move(path, backup)
            with open(path, "w") as fresh:
                fresh.write(f"# truncated at {time.time()}\n")
            rotated += 1
            logger.info(f"Rotated oversized log {os.path.basename(path)}")
        except OSError as e:
            logger.warning(f"Log rotate failed for {path}: {e}")
    logger.info(f"Errors cron: rotated {rotated} file(s).")


def cron_lines_logs():
    from datetime import datetime, timedelta

    from src.domain.models import Line

    logger.info("Running lines log cleanup cron...")
    db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=48)
        n = (
            db.query(Line)
            .filter(Line.date < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(f"Lines logs cron: removed {n} line row(s) older than 48h.")
    finally:
        db.close()


def cron_streams_logs():
    from datetime import datetime, timedelta

    from src.domain.models import StreamLog

    logger.info("Running stream logs cleanup cron...")
    db = get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(days=14)
        n = (
            db.query(StreamLog)
            .filter(StreamLog.date < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(f"Streams logs cron: removed {n} stream_logs row(s) older than 14d.")
    finally:
        db.close()


def cron_providers():
    import httpx

    logger.info("Running provider health cron...")
    db = get_db()
    try:
        from src.domain.stream.provider_service import ProviderService

        providers = ProviderService(db).get_providers()
        ok = 0
        fail = 0
        for p in providers:
            domain = (p.get("domain") or "").strip()
            if not domain:
                continue
            try:
                r = httpx.head(
                    f"https://{domain}/",
                    timeout=6.0,
                    follow_redirects=True,
                )
                if r.status_code < 500:
                    ok += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
        from src.domain.server.settings_service import SettingsService

        SettingsService(db).set("cron_providers_ok", ok, "int")
        SettingsService(db).set("cron_providers_fail", fail, "int")
        logger.info(
            f"Providers cron: {len(providers)} domain(s), ok={ok}, fail={fail}."
        )
    finally:
        db.close()


def cron_certbot():
    logger.info("Running certificate check cron...")
    nginx_conf = settings.NGINX_CONF_DIR or os.path.join(
        settings.BASE_DIR, "..", "bin", "nginx", "conf"
    )
    cert_path = os.path.join(nginx_conf, "server.crt")
    detail = "missing"
    if os.path.isfile(cert_path):
        try:
            proc = subprocess.run(
                ["openssl", "x509", "-in", cert_path, "-noout", "-enddate"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            detail = (proc.stdout or proc.stderr or "").strip()
        except Exception as e:
            detail = str(e)
    db = get_db()
    try:
        from src.domain.server.settings_service import SettingsService

        SettingsService(db).set("cron_cert_enddate", detail[:512], "string")
    finally:
        db.close()
    logger.info(f"Cert cron: {detail[:120]}")


def cron_tmp():
    logger.info("Running temp cleanup cron...")
    tmp_dir = settings.TMP_DIR
    if not os.path.isdir(tmp_dir):
        logger.info("No tmp dir.")
        return
    threshold = time.time() - 3600
    removed = 0
    for root, dirs, files in os.walk(tmp_dir):
        for name in files:
            path = os.path.join(root, name)
            try:
                if os.path.isfile(path) and os.path.getmtime(path) < threshold:
                    os.remove(path)
                    removed += 1
            except OSError:
                pass
    logger.info(f"Tmp cron: removed {removed} file(s) older than 1h.")


COMMANDS = {
    "startup": cmd_startup,
    "monitor": cmd_monitor,
    "watchdog": cmd_watchdog,
    "cron:streams": cron_streams,
    "cron:users": cron_users,
    "cron:epg": cron_epg,
    "cron:cleanup": cron_cleanup,
    "cron:cache": cron_cache,
    "cron:servers": cron_servers,
    "cron:backups": cron_backups,
    "cron:activity": cron_activity,
    "cron:stats": cron_stats,
    "cron:vod": cron_vod,
    "cron:series": cron_series,
    "cron:errors": cron_errors,
    "cron:lines-logs": cron_lines_logs,
    "cron:streams-logs": cron_streams_logs,
    "cron:providers": cron_providers,
    "cron:certbot": cron_certbot,
    "cron:tmp": cron_tmp,
    "cmd:migrate": cmd_migrate,
    "cmd:create-admin": cmd_create_admin,
    "cmd:reset-admin": cmd_reset_admin,
    "cmd:import-epg": cmd_import_epg,
    "cmd:stats": cmd_stats,
    "cmd:service:start": cmd_service_start,
    "cmd:service:stop": cmd_service_stop,
    "cmd:service:restart": cmd_service_restart,
    "cmd:service:status": cmd_service_status,
    "cmd:scanner": cmd_scanner,
    "cmd:balancer": cmd_balancer,
    "cmd:archive": cmd_archive,
    "cmd:ondemand": cmd_ondemand,
    "cmd:record": cmd_record,
    "cmd:thumbnail": cmd_thumbnail,
    "cmd:certbot": cmd_certbot,
    "cmd:signals": cmd_signals,
    "cmd:tools": cmd_tools,
}


def main():
    if len(sys.argv) < 2:
        print("IPTV Panel CLI")
        print(f"Usage: python -m src.cli.console <command>")
        print(f"\nAvailable commands:")
        for cmd in sorted(COMMANDS.keys()):
            print(f"  {cmd}")
        sys.exit(1)

    command = sys.argv[1]
    if command not in COMMANDS:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(sorted(COMMANDS.keys()))}")
        sys.exit(1)

    COMMANDS[command]()


if __name__ == "__main__":
    main()
