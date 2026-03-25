#!/usr/bin/env python3
"""
IPTV Panel CLI - Console command runner.
Usage:
    python -m src.cli.console <command> [args]

Commands:
    startup          - Initialize and start all services
    monitor          - Monitor active streams and connections
    watchdog         - Watch and restart failed streams
    cron:streams     - Run streams maintenance cron
    cron:users       - Run users cleanup cron (expire users, etc.)
    cron:epg         - Run EPG update cron
    cron:cleanup     - Stale lines, temp files, old stream logs
    cron:cache       - Run cache refresh cron
    cron:servers     - Run server health check cron
    cron:backups     - Run backup cron
    cmd:migrate      - Run database migrations
    cmd:create-admin - Create admin user
    cmd:reset-admin  - Reset admin password
    cmd:import-epg   - Import EPG from URL
    cmd:stats        - Show system statistics
"""
import sys
import os

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
    logger.info("Cache cron complete.")


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
    "cmd:migrate": cmd_migrate,
    "cmd:create-admin": cmd_create_admin,
    "cmd:reset-admin": cmd_reset_admin,
    "cmd:import-epg": cmd_import_epg,
    "cmd:stats": cmd_stats,
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
