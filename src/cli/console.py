"""
StreamRev CLI Console
=====================

Central command dispatcher for StreamRev administrative and cron tasks.

Usage:
    python -m src.cli.console <command> [args...]

Commands are prefixed:
    cmd:*    — Interactive admin commands
    cron:*   — Scheduled cron tasks

Examples:
    python -m src.cli.console cmd:connections
    python -m src.cli.console cmd:kill 42
    python -m src.cli.console cmd:kill user 5
    python -m src.cli.console cmd:kill ip 10.0.0.1
    python -m src.cli.console cmd:kill all
    python -m src.cli.console cmd:queue
    python -m src.cli.console cmd:queue add 123
    python -m src.cli.console cmd:queue clear
    python -m src.cli.console cmd:audit
    python -m src.cli.console cmd:profiles
    python -m src.cli.console cmd:rtmp
    python -m src.cli.console cmd:sessions
    python -m src.cli.console cmd:hmac
    python -m src.cli.console cmd:proxies
    python -m src.cli.console cmd:db tables
    python -m src.cli.console cmd:db stats
    python -m src.cli.console cmd:cache:info
    python -m src.cli.console cmd:security
    python -m src.cli.console cmd:tmdb update-movies
    python -m src.cli.console cmd:tmdb update-series
    python -m src.cli.console cmd:theft scan
    python -m src.cli.console cmd:theft alerts
    python -m src.cli.console cmd:fingerprint
    python -m src.cli.console cmd:watch scan [/path]
    python -m src.cli.console cmd:archive
    python -m src.cli.console cron:queue
    python -m src.cli.console cron:connections
    python -m src.cli.console cron:recordings
    python -m src.cli.console cron:audit
    python -m src.cli.console cron:theft
    python -m src.cli.console cron:tmdb
    python -m src.cli.console cron:fingerprint
    python -m src.cli.console cron:watch
    python -m src.cli.console cron:archive
    python -m src.cli.console cron:registrations
"""

import os
import sys
import json
import hashlib
import secrets
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.core.logging.logger import logger


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------

def get_db():
    """Return a new SQLAlchemy Session (caller must close)."""
    from src.core.database import SessionLocal
    return SessionLocal()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.utcnow()


def _trunc(text: Optional[str], length: int = 40) -> str:
    """Truncate a string for display."""
    if not text:
        return ""
    return (text[:length] + "...") if len(text) > length else text


def _print_table(headers: List[str], rows: List[List[Any]]) -> None:
    """Print a simple ASCII table."""
    if not rows:
        print("  (no data)")
        return
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in col_widths]))
    for row in rows:
        print(fmt.format(*[str(c) for c in row]))


# ===========================================================================
#  CMD: CONNECTIONS — show live connections
# ===========================================================================

def cmd_connections(args: List[str]) -> None:
    """Show all active (live) connections."""
    db = get_db()
    try:
        from src.domain.models import Line, User, Stream

        lines = db.query(Line).all()
        print(f"Active connections: {len(lines)}")
        if not lines:
            return

        headers = ["LineID", "User", "Stream", "IP", "UserAgent", "Since"]
        rows = []
        for line in lines:
            user = db.query(User).filter(User.id == line.user_id).first()
            stream = db.query(Stream).filter(Stream.id == line.stream_id).first()
            uname = user.username if user else "?"
            sname = stream.stream_display_name if stream else "?"
            ua = _trunc(line.user_agent, 40) if hasattr(line, "user_agent") else ""
            since = str(line.date) if hasattr(line, "date") else ""
            rows.append([line.id, uname, sname, getattr(line, "user_ip", ""), ua, since])

        _print_table(headers, rows)
        logger.info(f"cmd:connections — listed {len(lines)} active connections")
    finally:
        db.close()


# ===========================================================================
#  CMD: KILL — kill connections
# ===========================================================================

def cmd_kill(args: List[str]) -> None:
    """
    Kill connections.
        cmd:kill <line_id>
        cmd:kill user <user_id>
        cmd:kill ip <ip_address>
        cmd:kill all
    """
    db = get_db()
    try:
        from src.domain.models import Line

        if not args:
            print("Usage: cmd:kill <line_id> | cmd:kill user <uid> | cmd:kill ip <ip> | cmd:kill all")
            return

        mode = args[0].lower()
        killed = 0

        if mode == "all":
            killed = db.query(Line).delete()
            db.commit()
            print(f"Killed ALL connections ({killed})")
            logger.warning(f"cmd:kill all — removed {killed} connections")

        elif mode == "user":
            if len(args) < 2:
                print("Usage: cmd:kill user <user_id>")
                return
            user_id = int(args[1])
            killed = db.query(Line).filter(Line.user_id == user_id).delete()
            db.commit()
            print(f"Killed {killed} connection(s) for user_id={user_id}")
            logger.info(f"cmd:kill user {user_id} — removed {killed} connections")

        elif mode == "ip":
            if len(args) < 2:
                print("Usage: cmd:kill ip <ip_address>")
                return
            ip = args[1]
            killed = db.query(Line).filter(Line.user_ip == ip).delete()
            db.commit()
            print(f"Killed {killed} connection(s) from IP={ip}")
            logger.info(f"cmd:kill ip {ip} — removed {killed} connections")

        else:
            # Treat as line_id
            try:
                line_id = int(mode)
            except ValueError:
                print(f"Unknown kill target: {mode}")
                return
            line = db.query(Line).filter(Line.id == line_id).first()
            if line:
                db.delete(line)
                db.commit()
                print(f"Killed connection line_id={line_id}")
                logger.info(f"cmd:kill {line_id} — connection removed")
            else:
                print(f"Line {line_id} not found")

    except Exception as exc:
        db.rollback()
        logger.error(f"cmd:kill error: {exc}")
        print(f"Error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CMD: QUEUE — show/manage stream queue
# ===========================================================================

def cmd_queue(args: List[str]) -> None:
    """
    Manage the stream processing queue.
        cmd:queue             — list queue items
        cmd:queue add <sid>   — add stream to queue
        cmd:queue clear       — clear completed/failed items
    """
    db = get_db()
    try:
        from src.domain.models import StreamQueue, Stream

        if not args:
            # List
            items = db.query(StreamQueue).order_by(StreamQueue.created_at.desc()).limit(100).all()
            print(f"Stream queue items: {len(items)}")
            headers = ["ID", "StreamID", "Stream", "Status", "Priority", "Created", "Error"]
            rows = []
            for item in items:
                stream = db.query(Stream).filter(Stream.id == item.stream_id).first()
                sname = _trunc(stream.stream_display_name, 30) if stream else "?"
                err = _trunc(item.error_message, 30) if item.error_message else ""
                rows.append([
                    item.id,
                    item.stream_id,
                    sname,
                    item.status,
                    item.priority,
                    str(item.created_at)[:19],
                    err,
                ])
            _print_table(headers, rows)
            return

        sub = args[0].lower()

        if sub == "add":
            if len(args) < 2:
                print("Usage: cmd:queue add <stream_id>")
                return
            stream_id = int(args[1])
            stream = db.query(Stream).filter(Stream.id == stream_id).first()
            if not stream:
                print(f"Stream {stream_id} not found")
                return
            entry = StreamQueue(
                stream_id=stream_id,
                status="pending",
                priority=0,
                created_at=_utcnow(),
            )
            db.add(entry)
            db.commit()
            print(f"Added stream {stream_id} ({stream.stream_display_name}) to queue (id={entry.id})")
            logger.info(f"cmd:queue add — stream {stream_id} queued")

        elif sub == "clear":
            cleared = db.query(StreamQueue).filter(
                StreamQueue.status.in_(["completed", "failed"])
            ).delete(synchronize_session="fetch")
            db.commit()
            print(f"Cleared {cleared} completed/failed queue item(s)")
            logger.info(f"cmd:queue clear — removed {cleared} items")

        else:
            print(f"Unknown queue sub-command: {sub}")

    except Exception as exc:
        db.rollback()
        logger.error(f"cmd:queue error: {exc}")
        print(f"Error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CMD: AUDIT — show recent audit log entries
# ===========================================================================

def cmd_audit(args: List[str]) -> None:
    """Show recent audit log entries."""
    db = get_db()
    try:
        from src.domain.models import AuditLog

        limit = 50
        if args:
            try:
                limit = int(args[0])
            except ValueError:
                pass

        entries = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
        print(f"Recent audit log entries (last {limit}):")
        headers = ["ID", "Action", "Admin", "Target", "IP", "Timestamp"]
        rows = []
        for e in entries:
            rows.append([
                e.id,
                _trunc(getattr(e, "action", ""), 25),
                getattr(e, "admin_id", ""),
                _trunc(getattr(e, "target", ""), 30),
                getattr(e, "ip_address", ""),
                str(getattr(e, "created_at", ""))[:19],
            ])
        _print_table(headers, rows)
        logger.info(f"cmd:audit — listed {len(entries)} entries")
    finally:
        db.close()


# ===========================================================================
#  CMD: PROFILES — list transcoding profiles
# ===========================================================================

def cmd_profiles(args: List[str]) -> None:
    """List all transcoding profiles."""
    db = get_db()
    try:
        from src.domain.models import TranscodingProfile

        profiles = db.query(TranscodingProfile).order_by(TranscodingProfile.id).all()
        print(f"Transcoding profiles: {len(profiles)}")
        headers = ["ID", "Name", "Cmd", "Enabled"]
        rows = []
        for p in profiles:
            rows.append([
                p.id,
                getattr(p, "profile_name", ""),
                _trunc(getattr(p, "profile_command", ""), 60),
                "Yes" if getattr(p, "enabled", False) else "No",
            ])
        _print_table(headers, rows)
        logger.info(f"cmd:profiles — listed {len(profiles)} profiles")
    finally:
        db.close()


# ===========================================================================
#  CMD: RTMP — show RTMP / streaming engine stats
# ===========================================================================

def cmd_rtmp(args: List[str]) -> None:
    """Show RTMP stats from the streaming engine."""
    db = get_db()
    try:
        from src.domain.models import Stream, Server, Line

        live_streams = db.query(Stream).filter(Stream.enabled == True, Stream.stream_type == 1).count()
        total_streams = db.query(Stream).count()
        active_conns = db.query(Line).count()
        servers = db.query(Server).all()

        print("RTMP / Streaming Engine Stats")
        print(f"  Total streams:      {total_streams}")
        print(f"  Live streams:       {live_streams}")
        print(f"  Active connections: {active_conns}")
        print()

        if servers:
            print("Servers:")
            headers = ["ID", "Name", "IP", "Status", "Clients"]
            rows = []
            for s in servers:
                rows.append([
                    s.id,
                    getattr(s, "server_name", ""),
                    getattr(s, "server_ip", ""),
                    getattr(s, "status", "unknown"),
                    getattr(s, "total_clients", 0),
                ])
            _print_table(headers, rows)

        # Try to get RTMP stats from nginx-rtmp stat endpoint
        try:
            from src.core.config import settings
            rtmp_stat_url = getattr(settings, "RTMP_STAT_URL", "http://127.0.0.1:8080/stat")
            import urllib.request
            with urllib.request.urlopen(rtmp_stat_url, timeout=3) as resp:
                data = resp.read().decode()
                print(f"\nRTMP stat endpoint ({rtmp_stat_url}): {len(data)} bytes received")
        except Exception:
            print("\n  (RTMP stat endpoint not reachable)")

        logger.info("cmd:rtmp — displayed streaming stats")
    finally:
        db.close()


# ===========================================================================
#  CMD: SESSIONS — list active admin/reseller sessions
# ===========================================================================

def cmd_sessions(args: List[str]) -> None:
    """List active admin and reseller sessions."""
    db = get_db()
    try:
        from src.domain.models import AdminSession

        sessions = db.query(AdminSession).order_by(AdminSession.id.desc()).limit(100).all()
        print(f"Active sessions: {len(sessions)}")
        headers = ["ID", "AdminID", "IP", "UserAgent", "Created", "Expires"]
        rows = []
        for s in sessions:
            rows.append([
                s.id,
                getattr(s, "admin_id", ""),
                getattr(s, "ip_address", ""),
                _trunc(getattr(s, "user_agent", ""), 30),
                str(getattr(s, "created_at", ""))[:19],
                str(getattr(s, "expires_at", ""))[:19],
            ])
        _print_table(headers, rows)
        logger.info(f"cmd:sessions — listed {len(sessions)} sessions")
    finally:
        db.close()


# ===========================================================================
#  CMD: HMAC — list / generate HMAC keys
# ===========================================================================

def cmd_hmac(args: List[str]) -> None:
    """
    HMAC key management.
        cmd:hmac            — list existing keys
        cmd:hmac generate   — generate a new key
    """
    db = get_db()
    try:
        from src.domain.models import HmacKey

        if args and args[0].lower() == "generate":
            new_key = secrets.token_hex(32)
            entry = HmacKey(
                key_value=new_key,
                description=f"Generated via CLI at {_utcnow().isoformat()}",
                enabled=True,
                created_at=_utcnow(),
            )
            db.add(entry)
            db.commit()
            print(f"Generated new HMAC key: {new_key} (id={entry.id})")
            logger.info(f"cmd:hmac generate — created key id={entry.id}")
            return

        keys = db.query(HmacKey).order_by(HmacKey.id).all()
        print(f"HMAC keys: {len(keys)}")
        headers = ["ID", "Key", "Description", "Enabled", "Created"]
        rows = []
        for k in keys:
            rows.append([
                k.id,
                _trunc(k.key_value, 20),
                _trunc(getattr(k, "description", ""), 30),
                "Yes" if getattr(k, "enabled", False) else "No",
                str(getattr(k, "created_at", ""))[:19],
            ])
        _print_table(headers, rows)
        logger.info(f"cmd:hmac — listed {len(keys)} keys")
    except Exception as exc:
        db.rollback()
        logger.error(f"cmd:hmac error: {exc}")
        print(f"Error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CMD: PROXIES — list / test proxies
# ===========================================================================

def cmd_proxies(args: List[str]) -> None:
    """
    Proxy management.
        cmd:proxies          — list proxies
        cmd:proxies test     — test all proxies
    """
    db = get_db()
    try:
        from src.domain.models import Proxy

        proxies = db.query(Proxy).order_by(Proxy.id).all()

        if args and args[0].lower() == "test":
            print(f"Testing {len(proxies)} proxies...")
            for p in proxies:
                proxy_url = f"{p.proxy_type}://{p.proxy_ip}:{p.proxy_port}"
                try:
                    import urllib.request
                    proxy_handler = urllib.request.ProxyHandler({
                        "http": proxy_url,
                        "https": proxy_url,
                    })
                    opener = urllib.request.build_opener(proxy_handler)
                    opener.open("http://httpbin.org/ip", timeout=5)
                    status = "OK"
                except Exception:
                    status = "FAIL"
                print(f"  [{status}] {proxy_url}")
            logger.info(f"cmd:proxies test — tested {len(proxies)} proxies")
            return

        print(f"Proxies: {len(proxies)}")
        headers = ["ID", "Type", "IP", "Port", "Username", "Enabled"]
        rows = []
        for p in proxies:
            rows.append([
                p.id,
                getattr(p, "proxy_type", "http"),
                getattr(p, "proxy_ip", ""),
                getattr(p, "proxy_port", ""),
                _trunc(getattr(p, "proxy_username", ""), 15),
                "Yes" if getattr(p, "enabled", True) else "No",
            ])
        _print_table(headers, rows)
        logger.info(f"cmd:proxies — listed {len(proxies)} proxies")
    finally:
        db.close()


# ===========================================================================
#  CMD: DB — database info
# ===========================================================================

def cmd_db(args: List[str]) -> None:
    """
    Database information.
        cmd:db tables   — list tables and row counts
        cmd:db stats    — database size and statistics
    """
    db = get_db()
    try:
        from sqlalchemy import text, inspect

        engine = db.get_bind()

        if not args:
            print("Usage: cmd:db tables | cmd:db stats")
            return

        sub = args[0].lower()

        if sub == "tables":
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            print(f"Database tables: {len(table_names)}")
            headers = ["Table", "Rows"]
            rows = []
            for t in sorted(table_names):
                try:
                    result = db.execute(text(f"SELECT COUNT(*) FROM `{t}`"))
                    count = result.scalar()
                except Exception:
                    count = "?"
                rows.append([t, count])
            _print_table(headers, rows)
            logger.info(f"cmd:db tables — listed {len(table_names)} tables")

        elif sub == "stats":
            print("Database Statistics:")
            try:
                # MySQL / MariaDB
                result = db.execute(text(
                    "SELECT table_schema, "
                    "ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb, "
                    "SUM(table_rows) AS total_rows "
                    "FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() "
                    "GROUP BY table_schema"
                ))
                row = result.fetchone()
                if row:
                    print(f"  Schema:     {row[0]}")
                    print(f"  Size:       {row[1]} MB")
                    print(f"  Total rows: {row[2]}")
            except Exception:
                # SQLite fallback
                try:
                    result = db.execute(text("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"))
                    size = result.scalar()
                    print(f"  Database size: {size / 1024:.1f} KB" if size else "  Database size: unknown")
                except Exception:
                    print("  Could not determine database statistics")

            inspector = inspect(engine)
            table_count = len(inspector.get_table_names())
            print(f"  Tables:     {table_count}")
            logger.info("cmd:db stats — displayed database statistics")

        else:
            print(f"Unknown db sub-command: {sub}")

    finally:
        db.close()


# ===========================================================================
#  CMD: CACHE:INFO — Redis cache info
# ===========================================================================

def cmd_cache_info(args: List[str]) -> None:
    """Show Redis cache info and key count."""
    try:
        from src.core.cache.redis_cache import redis_client

        if redis_client is None:
            print("Redis not configured / not connected")
            return

        info = redis_client.info()
        dbsize = redis_client.dbsize()

        print("Redis Cache Info")
        print(f"  Version:          {info.get('redis_version', '?')}")
        print(f"  Connected clients: {info.get('connected_clients', '?')}")
        print(f"  Used memory:      {info.get('used_memory_human', '?')}")
        print(f"  Peak memory:      {info.get('used_memory_peak_human', '?')}")
        print(f"  Total keys:       {dbsize}")
        print(f"  Uptime (seconds): {info.get('uptime_in_seconds', '?')}")
        print(f"  Hit rate:         {info.get('keyspace_hits', 0)} hits / {info.get('keyspace_misses', 0)} misses")

        evicted = info.get("evicted_keys", 0)
        if evicted:
            print(f"  Evicted keys:     {evicted}")

        logger.info(f"cmd:cache:info — Redis dbsize={dbsize}")
    except ImportError:
        print("Redis cache module not available")
    except Exception as exc:
        print(f"Redis error: {exc}")
        logger.error(f"cmd:cache:info error: {exc}")


# ===========================================================================
#  CMD: SECURITY — security overview
# ===========================================================================

def cmd_security(args: List[str]) -> None:
    """Security overview: blocked IPs, user-agents, ASNs, ISPs count."""
    db = get_db()
    try:
        from src.domain.models import BlockedIP, BlockedUserAgent, BlockedASN, BlockedISP

        blocked_ips = db.query(BlockedIP).count()
        blocked_uas = db.query(BlockedUserAgent).count()
        blocked_asns = db.query(BlockedASN).count()
        blocked_isps = db.query(BlockedISP).count()

        print("Security Overview")
        print(f"  Blocked IPs:          {blocked_ips}")
        print(f"  Blocked User-Agents:  {blocked_uas}")
        print(f"  Blocked ASNs:         {blocked_asns}")
        print(f"  Blocked ISPs:         {blocked_isps}")
        print(f"  Total blocklist:      {blocked_ips + blocked_uas + blocked_asns + blocked_isps}")

        # Check for recent blocks
        try:
            recent_cutoff = _utcnow() - timedelta(hours=24)
            recent_ips = db.query(BlockedIP).filter(BlockedIP.created_at >= recent_cutoff).count()
            if recent_ips > 0:
                print(f"\n  New blocks (last 24h): {recent_ips} IPs")
        except Exception:
            pass

        logger.info(f"cmd:security — IPs={blocked_ips}, UAs={blocked_uas}, ASNs={blocked_asns}, ISPs={blocked_isps}")
    finally:
        db.close()


# ===========================================================================
#  CMD: TMDB — TMDB metadata update
# ===========================================================================

def cmd_tmdb(args: List[str]) -> None:
    """
    TMDB metadata operations.
        cmd:tmdb update-movies   — update movies without TMDB data
        cmd:tmdb update-series   — update series without TMDB data
    """
    if not args:
        print("Usage: cmd:tmdb update-movies | cmd:tmdb update-series")
        return

    db = get_db()
    try:
        from src.domain.models import Movie, Series, Setting

        sub = args[0].lower()

        # Check for API key
        api_key_row = db.query(Setting).filter(Setting.key == "tmdb_api_key").first()
        if not api_key_row or not api_key_row.value:
            print("Error: TMDB API key not configured. Set 'tmdb_api_key' in Settings.")
            return

        if sub == "update-movies":
            movies = db.query(Movie).filter(
                (Movie.tmdb_id == None) | (Movie.tmdb_id == 0)
            ).all()
            print(f"Movies without TMDB metadata: {len(movies)}")
            if not movies:
                print("All movies have TMDB metadata.")
                return

            updated = 0
            errors = 0
            for movie in movies:
                try:
                    from src.modules.tmdb.service import TMDBService
                    svc = TMDBService(db)
                    # Use synchronous wrapper for CLI
                    import asyncio
                    result = asyncio.get_event_loop().run_until_complete(
                        svc.search_and_update_movie(movie.id)
                    )
                    if result:
                        updated += 1
                        print(f"  Updated: {movie.stream_display_name} -> tmdb_id={result.get('tmdb_id', '?')}")
                    else:
                        print(f"  Not found: {movie.stream_display_name}")
                except Exception as exc:
                    errors += 1
                    print(f"  Error for {movie.stream_display_name}: {exc}")

            print(f"\nDone. Updated: {updated}, Errors: {errors}, Skipped: {len(movies) - updated - errors}")
            logger.info(f"cmd:tmdb update-movies — updated={updated}, errors={errors}")

        elif sub == "update-series":
            series_list = db.query(Series).filter(
                (Series.tmdb_id == None) | (Series.tmdb_id == 0)
            ).all()
            print(f"Series without TMDB metadata: {len(series_list)}")
            if not series_list:
                print("All series have TMDB metadata.")
                return

            updated = 0
            errors = 0
            for series in series_list:
                try:
                    from src.modules.tmdb.service import TMDBService
                    svc = TMDBService(db)
                    import asyncio
                    result = asyncio.get_event_loop().run_until_complete(
                        svc.search_and_update_series(series.id)
                    )
                    if result:
                        updated += 1
                        print(f"  Updated: {series.series_name} -> tmdb_id={result.get('tmdb_id', '?')}")
                    else:
                        print(f"  Not found: {series.series_name}")
                except Exception as exc:
                    errors += 1
                    print(f"  Error for {series.series_name}: {exc}")

            print(f"\nDone. Updated: {updated}, Errors: {errors}, Skipped: {len(series_list) - updated - errors}")
            logger.info(f"cmd:tmdb update-series — updated={updated}, errors={errors}")

        else:
            print(f"Unknown tmdb sub-command: {sub}")

    except Exception as exc:
        logger.error(f"cmd:tmdb error: {exc}")
        print(f"Error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CMD: THEFT — theft detection
# ===========================================================================

def cmd_theft(args: List[str]) -> None:
    """
    Theft detection.
        cmd:theft scan    — run credential sharing scan
        cmd:theft alerts  — show recent theft alerts
    """
    if not args:
        print("Usage: cmd:theft scan | cmd:theft alerts")
        return

    sub = args[0].lower()

    if sub == "scan":
        db = get_db()
        try:
            from src.modules.theft_detection.service import TheftDetectionService

            svc = TheftDetectionService()
            suspects = svc.detect_credential_sharing()
            db_suspects = svc.detect_credential_sharing_db(db)

            # Merge results
            seen = {r["user_id"] for r in db_suspects}
            combined = db_suspects + [r for r in suspects if r["user_id"] not in seen]

            print(f"Theft Detection Scan Results: {len(combined)} suspicious users")
            if not combined:
                print("  No credential sharing detected.")
                return

            headers = ["UserID", "UniqueIPs", "UniqueUAs", "Risk"]
            rows = []
            for s in combined:
                rows.append([
                    s["user_id"],
                    s.get("unique_ips", 0),
                    s.get("unique_user_agents", 0),
                    s.get("risk_level", "unknown"),
                ])
            _print_table(headers, rows)
            logger.info(f"cmd:theft scan — found {len(combined)} suspicious users")
        finally:
            db.close()

    elif sub == "alerts":
        from src.modules.theft_detection.service import TheftDetectionService

        svc = TheftDetectionService()
        alerts = svc.get_alerts()
        print(f"Theft Alerts: {len(alerts)}")
        if not alerts:
            print("  No alerts.")
            return

        headers = ["Type", "UserID", "Detail", "Timestamp"]
        rows = []
        for a in alerts:
            rows.append([
                a.get("type", ""),
                a.get("user_id", ""),
                _trunc(a.get("detail", ""), 40),
                a.get("timestamp", "")[:19] if a.get("timestamp") else "",
            ])
        _print_table(headers, rows)
        logger.info(f"cmd:theft alerts — listed {len(alerts)} alerts")

    else:
        print(f"Unknown theft sub-command: {sub}")


# ===========================================================================
#  CMD: FINGERPRINT — fingerprint statistics
# ===========================================================================

def cmd_fingerprint(args: List[str]) -> None:
    """Show fingerprint statistics."""
    try:
        from src.modules.fingerprint.service import FingerprintService

        svc = FingerprintService()
        stats = svc.get_stats()

        print("Fingerprint Statistics")
        for key, val in stats.items():
            print(f"  {key}: {val}")

        logger.info("cmd:fingerprint — displayed stats")
    except ImportError:
        print("Fingerprint module not available")
    except Exception as exc:
        print(f"Error: {exc}")
        logger.error(f"cmd:fingerprint error: {exc}")


# ===========================================================================
#  CMD: WATCH — watch folder scan
# ===========================================================================

def cmd_watch(args: List[str]) -> None:
    """
    Watch folder management.
        cmd:watch scan          — scan configured watch folders
        cmd:watch scan /path    — scan a specific path
    """
    db = get_db()
    try:
        from src.modules.watch.service import WatchFolderService

        svc = WatchFolderService(db)

        if not args:
            print("Usage: cmd:watch scan [path]")
            return

        sub = args[0].lower()

        if sub == "scan":
            path = args[1] if len(args) > 1 else None
            if path:
                # Scan specific path
                import os
                if not os.path.isdir(path):
                    print(f"Error: {path} is not a directory")
                    return
                files = svc.scan_directory(path)
            else:
                # Scan all configured watch directories
                files = svc.scan_all()

            print(f"Watch scan results: {len(files)} media files found")
            if files:
                headers = ["Filename", "Path", "Size", "Ext"]
                rows = []
                for f in files[:50]:  # Limit display
                    size_mb = f.get("size", 0) / (1024 * 1024)
                    rows.append([
                        _trunc(f.get("filename", ""), 30),
                        _trunc(f.get("path", ""), 40),
                        f"{size_mb:.1f} MB",
                        f.get("extension", ""),
                    ])
                _print_table(headers, rows)
                if len(files) > 50:
                    print(f"  ... and {len(files) - 50} more files")
            logger.info(f"cmd:watch scan — found {len(files)} files")
        else:
            print(f"Unknown watch sub-command: {sub}")

    except ImportError:
        print("Watch module not available")
    except Exception as exc:
        print(f"Error: {exc}")
        logger.error(f"cmd:watch error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CMD: ARCHIVE — archive management
# ===========================================================================

def cmd_archive(args: List[str]) -> None:
    """Manage timeshift/catchup archives."""
    db = get_db()
    try:
        from src.domain.models import Stream, Setting

        # Get archive settings
        archive_path_row = db.query(Setting).filter(Setting.key == "archive_path").first()
        archive_path = archive_path_row.value if archive_path_row and archive_path_row.value else "/var/streamrev/archive"

        retention_row = db.query(Setting).filter(Setting.key == "archive_retention_days").first()
        retention_days = int(retention_row.value) if retention_row and retention_row.value else 7

        # Count streams with archive enabled
        archive_streams = db.query(Stream).filter(
            Stream.enabled == True,
            Stream.tv_archive == True,
        ).count()

        print("Archive Info")
        print(f"  Archive path:          {archive_path}")
        print(f"  Retention:             {retention_days} days")
        print(f"  Streams with archive:  {archive_streams}")

        # Check disk usage if path exists
        if os.path.isdir(archive_path):
            total_size = 0
            file_count = 0
            for root, dirs, files in os.walk(archive_path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total_size += os.path.getsize(fp)
                        file_count += 1
                    except OSError:
                        pass
            print(f"  Archive files:         {file_count}")
            print(f"  Archive size:          {total_size / (1024**3):.2f} GB")

            # Count expired files
            cutoff = _utcnow() - timedelta(days=retention_days)
            expired = 0
            for root, dirs, files in os.walk(archive_path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                        if mtime < cutoff:
                            expired += 1
                    except OSError:
                        pass
            if expired:
                print(f"  Expired files:         {expired} (older than {retention_days} days)")
        else:
            print(f"  (Archive path does not exist)")

        logger.info("cmd:archive — displayed archive info")
    finally:
        db.close()


# ===========================================================================
#  CRON: QUEUE — process pending stream queue items
# ===========================================================================

def cron_queue(args: List[str]) -> None:
    """Process pending items in the stream queue."""
    db = get_db()
    try:
        from src.domain.models import StreamQueue, Stream

        pending = db.query(StreamQueue).filter(
            StreamQueue.status == "pending"
        ).order_by(StreamQueue.priority.desc(), StreamQueue.created_at).all()

        if not pending:
            logger.info("cron:queue — no pending items")
            return

        logger.info(f"cron:queue — processing {len(pending)} pending items")
        processed = 0
        failed = 0

        for item in pending:
            try:
                # Mark as processing
                item.status = "processing"
                item.started_at = _utcnow()
                db.commit()

                stream = db.query(Stream).filter(Stream.id == item.stream_id).first()
                if not stream:
                    item.status = "failed"
                    item.error_message = "Stream not found"
                    item.completed_at = _utcnow()
                    db.commit()
                    failed += 1
                    continue

                # Attempt to start/process the stream
                try:
                    from src.streaming.engine import streaming_engine
                    streaming_engine.start_stream(stream.id)
                except ImportError:
                    pass  # Engine may not be available in CLI context

                # Mark as completed
                item.status = "completed"
                item.completed_at = _utcnow()
                db.commit()
                processed += 1
                logger.info(f"cron:queue — processed stream_id={item.stream_id}")

            except Exception as exc:
                item.status = "failed"
                item.error_message = str(exc)[:500]
                item.completed_at = _utcnow()
                db.commit()
                failed += 1
                logger.error(f"cron:queue — failed stream_id={item.stream_id}: {exc}")

        logger.info(f"cron:queue — done: processed={processed}, failed={failed}")
    except Exception as exc:
        db.rollback()
        logger.error(f"cron:queue error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CRON: CONNECTIONS — clean stale connections
# ===========================================================================

def cron_connections(args: List[str]) -> None:
    """Clean stale connections and update server total_clients counts."""
    db = get_db()
    try:
        from src.domain.models import Line, Server
        from sqlalchemy import func

        # Remove connections older than the stale threshold (default: 5 minutes)
        stale_cutoff = _utcnow() - timedelta(minutes=5)
        stale = db.query(Line).filter(Line.date < stale_cutoff).all()
        stale_count = len(stale)
        if stale_count > 0:
            for line in stale:
                db.delete(line)
            db.commit()
            logger.info(f"cron:connections — removed {stale_count} stale connections")

        # Update server total_clients counts
        servers = db.query(Server).all()
        for server in servers:
            client_count = db.query(func.count(Line.id)).filter(
                Line.server_id == server.id
            ).scalar() or 0
            if server.total_clients != client_count:
                server.total_clients = client_count
        db.commit()

        total_active = db.query(Line).count()
        logger.info(f"cron:connections — active={total_active}, cleaned={stale_count}, servers updated={len(servers)}")
    except Exception as exc:
        db.rollback()
        logger.error(f"cron:connections error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CRON: RECORDINGS — manage scheduled recordings
# ===========================================================================

def cron_recordings(args: List[str]) -> None:
    """Check scheduled recordings, start/stop recording processes."""
    db = get_db()
    try:
        from src.domain.models import Recording, Stream

        now = _utcnow()

        # Find recordings that should start now
        to_start = db.query(Recording).filter(
            Recording.status == "scheduled",
            Recording.start_time <= now,
            Recording.end_time > now,
        ).all()

        started = 0
        for rec in to_start:
            try:
                stream = db.query(Stream).filter(Stream.id == rec.stream_id).first()
                if not stream:
                    rec.status = "failed"
                    rec.error_message = "Stream not found"
                    db.commit()
                    continue

                # Start recording process
                rec.status = "recording"
                rec.actual_start = now
                db.commit()

                # Launch FFmpeg recording process
                from src.core.config import settings
                output_dir = getattr(settings, "RECORDING_PATH", "/var/streamrev/recordings")
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(
                    output_dir,
                    f"rec_{rec.id}_{stream.id}_{now.strftime('%Y%m%d_%H%M%S')}.ts"
                )

                duration_secs = int((rec.end_time - now).total_seconds())
                if duration_secs > 0 and hasattr(stream, "stream_source") and stream.stream_source:
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", stream.stream_source,
                        "-t", str(duration_secs),
                        "-c", "copy",
                        output_file,
                    ]
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    rec.pid = proc.pid
                    rec.output_path = output_file
                    db.commit()
                    started += 1
                    logger.info(f"cron:recordings — started recording id={rec.id} stream={stream.id} pid={proc.pid}")

            except Exception as exc:
                rec.status = "failed"
                rec.error_message = str(exc)[:500]
                db.commit()
                logger.error(f"cron:recordings — failed to start recording id={rec.id}: {exc}")

        # Find recordings that should have ended
        to_stop = db.query(Recording).filter(
            Recording.status == "recording",
            Recording.end_time <= now,
        ).all()

        stopped = 0
        for rec in to_stop:
            try:
                if rec.pid:
                    try:
                        os.kill(rec.pid, 15)  # SIGTERM
                    except OSError:
                        pass  # Process may have already exited
                rec.status = "completed"
                rec.actual_end = now
                db.commit()
                stopped += 1
                logger.info(f"cron:recordings — stopped recording id={rec.id}")
            except Exception as exc:
                logger.error(f"cron:recordings — error stopping recording id={rec.id}: {exc}")

        if started or stopped:
            logger.info(f"cron:recordings — started={started}, stopped={stopped}")
        else:
            logger.info("cron:recordings — no recordings to process")

    except ImportError:
        logger.warning("cron:recordings — Recording model not available")
    except Exception as exc:
        db.rollback()
        logger.error(f"cron:recordings error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CRON: AUDIT — clean old audit logs
# ===========================================================================

def cron_audit(args: List[str]) -> None:
    """Clean audit log entries older than 90 days."""
    db = get_db()
    try:
        from src.domain.models import AuditLog

        cutoff = _utcnow() - timedelta(days=90)
        deleted = db.query(AuditLog).filter(AuditLog.created_at < cutoff).delete(
            synchronize_session="fetch"
        )
        db.commit()
        logger.info(f"cron:audit — cleaned {deleted} audit log entries older than 90 days")
    except Exception as exc:
        db.rollback()
        logger.error(f"cron:audit error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CRON: THEFT — run theft detection scan
# ===========================================================================

def cron_theft(args: List[str]) -> None:
    """Run theft detection scan and log alerts."""
    db = get_db()
    try:
        from src.modules.theft_detection.service import TheftDetectionService

        svc = TheftDetectionService()

        # In-memory detection
        suspects_mem = svc.detect_credential_sharing()

        # Database detection
        suspects_db = svc.detect_credential_sharing_db(db)

        # Merge
        seen = {r["user_id"] for r in suspects_db}
        combined = suspects_db + [r for r in suspects_mem if r["user_id"] not in seen]

        if combined:
            for suspect in combined:
                svc.create_alert(
                    alert_type="credential_sharing",
                    user_id=suspect["user_id"],
                    detail=f"Unique IPs: {suspect.get('unique_ips', 0)}, Risk: {suspect.get('risk_level', 'unknown')}",
                )
            logger.warning(f"cron:theft — {len(combined)} suspicious users detected")
        else:
            logger.info("cron:theft — no suspicious activity detected")

    except ImportError:
        logger.warning("cron:theft — theft_detection module not available")
    except Exception as exc:
        logger.error(f"cron:theft error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CRON: TMDB — auto-update metadata
# ===========================================================================

def cron_tmdb(args: List[str]) -> None:
    """Auto-update movies and series without TMDB metadata."""
    db = get_db()
    try:
        from src.domain.models import Movie, Series, Setting

        api_key_row = db.query(Setting).filter(Setting.key == "tmdb_api_key").first()
        if not api_key_row or not api_key_row.value:
            logger.info("cron:tmdb — no API key configured, skipping")
            return

        # Update movies (batch of 20)
        movies = db.query(Movie).filter(
            (Movie.tmdb_id == None) | (Movie.tmdb_id == 0)
        ).limit(20).all()

        movie_updated = 0
        for movie in movies:
            try:
                from src.modules.tmdb.service import TMDBService
                svc = TMDBService(db)
                import asyncio
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(svc.search_and_update_movie(movie.id))
                loop.close()
                if result:
                    movie_updated += 1
            except Exception as exc:
                logger.error(f"cron:tmdb — movie {movie.id} error: {exc}")

        # Update series (batch of 20)
        series_list = db.query(Series).filter(
            (Series.tmdb_id == None) | (Series.tmdb_id == 0)
        ).limit(20).all()

        series_updated = 0
        for series in series_list:
            try:
                from src.modules.tmdb.service import TMDBService
                svc = TMDBService(db)
                import asyncio
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(svc.search_and_update_series(series.id))
                loop.close()
                if result:
                    series_updated += 1
            except Exception as exc:
                logger.error(f"cron:tmdb — series {series.id} error: {exc}")

        logger.info(f"cron:tmdb — movies updated={movie_updated}/{len(movies)}, series updated={series_updated}/{len(series_list)}")

    except ImportError:
        logger.warning("cron:tmdb — TMDB module not available")
    except Exception as exc:
        logger.error(f"cron:tmdb error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CRON: FINGERPRINT — analyze fingerprints for sharing detection
# ===========================================================================

def cron_fingerprint(args: List[str]) -> None:
    """Analyze connection fingerprints for sharing detection."""
    db = get_db()
    try:
        from src.modules.fingerprint.service import FingerprintService
        from src.domain.models import Line, User

        svc = FingerprintService()

        # Record fingerprints for all active connections
        lines = db.query(Line).all()
        recorded = 0
        for line in lines:
            try:
                fp = svc.record_fingerprint(
                    user_id=line.user_id,
                    ip=getattr(line, "user_ip", ""),
                    user_agent=getattr(line, "user_agent", ""),
                    stream_id=line.stream_id,
                )
                recorded += 1
            except Exception:
                pass

        # Check for suspicious patterns
        suspicious = svc.get_suspicious_patterns()
        if suspicious:
            logger.warning(f"cron:fingerprint — {len(suspicious)} suspicious patterns detected")
        else:
            logger.info(f"cron:fingerprint — recorded {recorded} fingerprints, no suspicious patterns")

    except ImportError:
        logger.warning("cron:fingerprint — fingerprint module not available")
    except Exception as exc:
        logger.error(f"cron:fingerprint error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CRON: WATCH — scan watch folders and auto-import
# ===========================================================================

def cron_watch(args: List[str]) -> None:
    """Scan watch folders and auto-import new files."""
    db = get_db()
    try:
        from src.modules.watch.service import WatchFolderService

        svc = WatchFolderService(db)
        dirs = svc.get_watch_dirs()
        if not dirs:
            logger.info("cron:watch — no watch directories configured")
            return

        total_found = 0
        total_imported = 0
        for watch_dir in dirs:
            if not os.path.isdir(watch_dir):
                logger.warning(f"cron:watch — directory not found: {watch_dir}")
                continue

            files = svc.scan_directory(watch_dir)
            total_found += len(files)

            # Auto-import new files
            for f in files:
                try:
                    imported = svc.auto_import_file(f["path"])
                    if imported:
                        total_imported += 1
                except Exception as exc:
                    logger.error(f"cron:watch — import error for {f['path']}: {exc}")

        logger.info(f"cron:watch — scanned {len(dirs)} dirs, found {total_found} files, imported {total_imported}")

    except ImportError:
        logger.warning("cron:watch — watch module not available")
    except Exception as exc:
        logger.error(f"cron:watch error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CRON: ARCHIVE — archive maintenance
# ===========================================================================

def cron_archive(args: List[str]) -> None:
    """Archive maintenance: clean expired archive files."""
    db = get_db()
    try:
        from src.domain.models import Setting

        archive_path_row = db.query(Setting).filter(Setting.key == "archive_path").first()
        archive_path = archive_path_row.value if archive_path_row and archive_path_row.value else "/var/streamrev/archive"

        retention_row = db.query(Setting).filter(Setting.key == "archive_retention_days").first()
        retention_days = int(retention_row.value) if retention_row and retention_row.value else 7

        if not os.path.isdir(archive_path):
            logger.info(f"cron:archive — archive path does not exist: {archive_path}")
            return

        cutoff = _utcnow() - timedelta(days=retention_days)
        removed = 0
        freed_bytes = 0

        for root, dirs, files in os.walk(archive_path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                    if mtime < cutoff:
                        size = os.path.getsize(fp)
                        os.remove(fp)
                        removed += 1
                        freed_bytes += size
                except OSError as exc:
                    logger.error(f"cron:archive — error removing {fp}: {exc}")

        # Clean empty directories
        for root, dirs, files in os.walk(archive_path, topdown=False):
            for d in dirs:
                dp = os.path.join(root, d)
                try:
                    if not os.listdir(dp):
                        os.rmdir(dp)
                except OSError:
                    pass

        freed_mb = freed_bytes / (1024 * 1024)
        logger.info(f"cron:archive — removed {removed} expired files, freed {freed_mb:.1f} MB (retention={retention_days}d)")

    except Exception as exc:
        logger.error(f"cron:archive error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  CRON: REGISTRATIONS — clean old pending registrations
# ===========================================================================

def cron_registrations(args: List[str]) -> None:
    """Clean old pending registrations older than 30 days."""
    db = get_db()
    try:
        from src.domain.models import Registration

        cutoff = _utcnow() - timedelta(days=30)
        deleted = db.query(Registration).filter(
            Registration.status == "pending",
            Registration.created_at < cutoff,
        ).delete(synchronize_session="fetch")
        db.commit()

        if deleted > 0:
            logger.info(f"cron:registrations — cleaned {deleted} pending registrations older than 30 days")
        else:
            logger.info("cron:registrations — no expired registrations")

    except Exception as exc:
        db.rollback()
        logger.error(f"cron:registrations error: {exc}")
    finally:
        db.close()


# ===========================================================================
#  XC_VM-STYLE CRONS — explicit compatibility implementations
# ===========================================================================

def cron_streams(args: List[str]) -> None:
    """Streams maintenance: process queue + prune stale connections."""
    cron_queue(args)
    cron_connections(args)
    logger.info("cron:streams — queue + connection maintenance completed")


def cron_users(args: List[str]) -> None:
    """Expire/disable users whose expiration date has passed."""
    db = get_db()
    try:
        from src.domain.models import User

        now = _utcnow()
        updated = (
            db.query(User)
            .filter(User.enabled.is_(True), User.exp_date.isnot(None), User.exp_date <= now)
            .update({User.enabled: False}, synchronize_session="fetch")
        )
        db.commit()
        logger.info(f"cron:users — disabled {updated} expired user(s)")
    except Exception as exc:
        db.rollback()
        logger.error(f"cron:users error: {exc}")
    finally:
        db.close()


def cron_epg(args: List[str]) -> None:
    """EPG cleanup and relink pass."""
    db = get_db()
    try:
        from src.domain.epg.service import EpgService

        svc = EpgService(db)
        removed = svc.clear_old(days=7)
        linked = svc.link_channels(db)
        logger.info(f"cron:epg — removed {removed} old programmes; linked {linked} rows")
    except Exception as exc:
        logger.error(f"cron:epg error: {exc}")
    finally:
        db.close()


def cron_cache(args: List[str]) -> None:
    """Cache maintenance."""
    # RedisCache in this codebase is async; cron console is sync.
    # Keep this command as a safe compatibility no-op until async cron runner is introduced.
    logger.info("cron:cache — compatibility no-op (async Redis maintenance not available in sync CLI yet)")


def cron_servers(args: List[str]) -> None:
    """Server health check summary."""
    db = get_db()
    try:
        from src.domain.server.service import ServerService

        svc = ServerService(db)
        rows = svc.get_all()
        total = len(rows)
        online = sum(1 for s in rows if getattr(s, "status", 0) == 1)
        logger.info(f"cron:servers — online={online}/{total}")
    except Exception as exc:
        logger.error(f"cron:servers error: {exc}")
    finally:
        db.close()


def cron_backups(args: List[str]) -> None:
    """Backup maintenance: remove stale backup files older than 14 days."""
    db = get_db()
    try:
        from src.core.config import settings

        keep_days = 14
        cutoff = _utcnow() - timedelta(days=keep_days)
        removed = 0
        for root, _dirs, files in os.walk(settings.BACKUP_DIR):
            for name in files:
                fp = os.path.join(root, name)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                    if mtime < cutoff:
                        os.remove(fp)
                        removed += 1
                except OSError:
                    continue
        logger.info(f"cron:backups — removed {removed} stale file(s) older than {keep_days} days")
    finally:
        db.close()


# ===========================================================================
#  COMPAT COMMANDS — installer/readme compatibility
# ===========================================================================

def cmd_migrate(args: List[str]) -> None:
    """Run database migrations (create missing tables from metadata)."""
    from src.core.database import Base, engine
    from src.domain import models as _models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print("Database migration completed (metadata create_all).")


def cmd_create_admin(args: List[str]) -> None:
    """Create or update default admin user."""
    db = get_db()
    try:
        from src.domain.user.service import UserService

        svc = UserService(db)
        username = args[0] if args else "admin"
        password = args[1] if len(args) > 1 else "admin"
        admin = svc.get_by_username(username)
        if admin:
            print(f"Admin '{username}' already exists.")
            return
        svc.create({
            "username": username,
            "password": password,
            "is_admin": True,
            "enabled": True,
            "max_connections": 1,
        })
        print(f"Admin created: {username}")
    finally:
        db.close()


def cmd_stats(args: List[str]) -> None:
    """Show basic host statistics."""
    import psutil

    vm = psutil.virtual_memory()
    du = psutil.disk_usage("/")
    print("System stats:")
    print(f"  CPU cores: {psutil.cpu_count()}")
    print(f"  CPU load: {psutil.cpu_percent(interval=0.5)}%")
    print(f"  RAM used: {vm.used / (1024**3):.2f} GiB / {vm.total / (1024**3):.2f} GiB ({vm.percent}%)")
    print(f"  Disk used: {du.used / (1024**3):.2f} GiB / {du.total / (1024**3):.2f} GiB ({du.percent}%)")


def cmd_reset_admin(args: List[str]) -> None:
    """Reset admin password. Usage: cmd:reset-admin [new_password]"""
    db = get_db()
    try:
        from src.domain.user.service import UserService

        svc = UserService(db)
        admin = svc.get_by_username("admin")
        if not admin:
            print("Admin user not found; creating default admin.")
            svc.create({
                "username": "admin",
                "password": args[0] if args else "admin",
                "is_admin": True,
                "enabled": True,
                "max_connections": 1,
            })
            print("Admin created.")
            return
        new_password = args[0] if args else "admin"
        svc.update(admin.id, {"password": new_password})
        print("Admin password reset successfully.")
    finally:
        db.close()


def cmd_import_epg(args: List[str]) -> None:
    """Import EPG from XMLTV URL. Usage: cmd:import-epg <url>"""
    if not args:
        print("Usage: cmd:import-epg <xmltv_url>")
        return
    db = get_db()
    try:
        from src.domain.epg.service import EpgService

        svc = EpgService(db)
        imported = svc.fetch_and_import(args[0])
        linked = svc.link_channels(db)
        print(f"Imported {imported} programme(s), linked {linked} channel row(s).")
    finally:
        db.close()


def cmd_startup(args: List[str]) -> None:
    """Initialize runtime dirs and baseline app state."""
    from src.bootstrap import ensure_runtime_dirs

    ensure_runtime_dirs()
    cmd_migrate([])
    cmd_create_admin([])
    print("Startup initialization complete.")


def cmd_monitor(args: List[str]) -> None:
    """Show quick runtime monitor information."""
    print("== Host Stats ==")
    cmd_stats([])
    print("\n== Active Connections ==")
    cmd_connections([])


def cmd_watchdog(args: List[str]) -> None:
    """Run lightweight watchdog maintenance checks."""
    print("Running queue and connection maintenance...")
    cron_queue([])
    cron_connections([])
    print("Watchdog pass completed.")


def cmd_parity_check(args: List[str]) -> None:
    """
    Validate P0 XC_VM parity contract (route and schema table presence).
    Usage: cmd:parity-check
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    failures: List[str] = []

    reseller_text = (root / "src/public/controllers/reseller/reseller_routes.py").read_text(encoding="utf-8")
    player_text = (root / "src/public/controllers/player/player_routes.py").read_text(encoding="utf-8")
    schema_text = (root / "schema.sql").read_text(encoding="utf-8")
    matrix_path = root / "parity/p0_matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    reseller_required = matrix["checks"]["route_level"]["reseller"]
    player_required = matrix["checks"]["route_level"]["player"]
    table_required = matrix["checks"]["db_table_level"]

    for path in reseller_required:
        if f'"/{path}"' not in reseller_text:
            failures.append(f"missing reseller route: /reseller/{path}")
    for path in player_required:
        if f'"/{path}"' not in player_text:
            failures.append(f"missing player route: /player/{path}")
    schema_l = schema_text.lower()
    for table in table_required:
        if f"create table {table} (" not in schema_l and f"create table `{table}` (" not in schema_l:
            failures.append(f"missing schema table: {table}")

    if failures:
        print("XC_VM P0 parity check: FAILED")
        for item in failures:
            print(f" - {item}")
        raise SystemExit(1)

    print("XC_VM P0 parity check: OK")
    logger.info("cmd:parity-check — all P0 route/schema checks passed")


# ===========================================================================
#  COMMANDS REGISTRY
# ===========================================================================

COMMANDS: Dict[str, Any] = {
    # --- Admin CLI commands ---
    "cmd:connections": cmd_connections,
    "cmd:kill": cmd_kill,
    "cmd:queue": cmd_queue,
    "cmd:audit": cmd_audit,
    "cmd:profiles": cmd_profiles,
    "cmd:rtmp": cmd_rtmp,
    "cmd:sessions": cmd_sessions,
    "cmd:hmac": cmd_hmac,
    "cmd:proxies": cmd_proxies,
    "cmd:db": cmd_db,
    "cmd:cache:info": cmd_cache_info,
    "cmd:security": cmd_security,
    "cmd:tmdb": cmd_tmdb,
    "cmd:theft": cmd_theft,
    "cmd:fingerprint": cmd_fingerprint,
    "cmd:watch": cmd_watch,
    "cmd:archive": cmd_archive,
    "cmd:migrate": cmd_migrate,
    "cmd:create-admin": cmd_create_admin,
    "cmd:stats": cmd_stats,
    "cmd:reset-admin": cmd_reset_admin,
    "cmd:import-epg": cmd_import_epg,
    # XC_VM-style service aliases
    "startup": cmd_startup,
    "monitor": cmd_monitor,
    "watchdog": cmd_watchdog,
    "cmd:parity-check": cmd_parity_check,
    # --- Cron jobs ---
    "cron:queue": cron_queue,
    "cron:connections": cron_connections,
    "cron:recordings": cron_recordings,
    "cron:audit": cron_audit,
    "cron:theft": cron_theft,
    "cron:tmdb": cron_tmdb,
    "cron:fingerprint": cron_fingerprint,
    "cron:watch": cron_watch,
    "cron:archive": cron_archive,
    "cron:registrations": cron_registrations,
    # XC_VM-style cron aliases
    "cron:streams": cron_streams,
    "cron:users": cron_users,
    "cron:epg": cron_epg,
    "cron:cache": cron_cache,
    "cron:servers": cron_servers,
    "cron:backups": cron_backups,
}


# ===========================================================================
#  MAIN ENTRY POINT
# ===========================================================================

def _print_help() -> None:
    """Print available commands."""
    print("StreamRev CLI Console")
    print("=" * 50)
    print()
    print("Usage: python -m src.cli.console <command> [args...]")
    print()

    cmds = sorted(k for k in COMMANDS if k.startswith("cmd:"))
    crons = sorted(k for k in COMMANDS if k.startswith("cron:"))

    print("Admin Commands:")
    for c in cmds:
        doc = COMMANDS[c].__doc__
        desc = doc.strip().split("\n")[0] if doc else ""
        print(f"  {c:<22} {desc}")

    print()
    print("Cron Jobs:")
    for c in crons:
        doc = COMMANDS[c].__doc__
        desc = doc.strip().split("\n")[0] if doc else ""
        print(f"  {c:<22} {desc}")

    print()


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        _print_help()
        sys.exit(0)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command in ("--help", "-h", "help"):
        _print_help()
        sys.exit(0)

    handler = COMMANDS.get(command)
    if handler is None:
        print(f"Unknown command: {command}")
        print(f"Run with --help to see available commands.")
        sys.exit(1)

    try:
        handler(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as exc:
        logger.error(f"Command '{command}' failed: {exc}")
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
