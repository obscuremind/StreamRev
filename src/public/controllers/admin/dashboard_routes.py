from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.core.database import get_db
from src.domain.bouquet.service import BouquetService
from src.domain.epg.service import EpgService
from src.domain.line.service import LineService, ResellerService
from src.domain.models import StreamCategory, User
from src.domain.server.service import ServerService
from src.domain.stream.service import StreamService
from src.domain.user.service import UserService
from src.domain.vod.service import MovieService, SeriesService
from .dependencies import get_current_admin

router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {
        "streams": StreamService(db).get_stats(),
        "users": UserService(db).get_stats(),
        "movies": MovieService(db).get_stats(),
        "series": SeriesService(db).get_stats(),
        "servers": ServerService(db).get_stats(),
        "epg": EpgService(db).get_stats(),
        "lines": {
            "active_connections": LineService(db).get_online_count(),
        },
        "bouquets": {"total": len(BouquetService(db).get_all())},
        "categories": {
            "total": db.query(func.count(StreamCategory.id)).scalar() or 0,
        },
        "resellers": ResellerService(db).get_stats(),
    }



@router.get("/system")
def system_info(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    import platform
    import os
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "pid": os.getpid(),
    }


@router.get("/connections-chart")
def connections_chart(
    hours: int = 24,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    from src.domain.models import UserActivity
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    data = (
        db.query(
            func.strftime("%Y-%m-%d %H:00:00", UserActivity.date_start).label("hour"),
            func.count(UserActivity.id).label("count"),
        )
        .filter(UserActivity.date_start >= cutoff)
        .group_by("hour")
        .order_by("hour")
        .all()
    )
    return {"chart": [{"hour": r.hour, "connections": r.count} for r in data]}


@router.get("/stream-health")
def stream_health(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    from src.domain.models import ServerStream, Stream
    total = db.query(func.count(Stream.id)).scalar() or 0
    active = db.query(func.count(ServerStream.id)).filter(ServerStream.stream_status == 1).scalar() or 0
    error = db.query(func.count(ServerStream.id)).filter(ServerStream.stream_status == 3).scalar() or 0
    enabled = db.query(func.count(Stream.id)).filter(Stream.enabled.is_(True)).scalar() or 0
    return {
        "total": total,
        "enabled": enabled,
        "active": active,
        "error": error,
        "health_pct": round(active / total * 100, 2) if total > 0 else 0,
    }


@router.get("/top-streams")
def top_streams(
    limit: int = 10,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    from src.domain.models import Line, Stream
    results = (
        db.query(
            Line.stream_id,
            func.count(Line.id).label("connections"),
        )
        .group_by(Line.stream_id)
        .order_by(func.count(Line.id).desc())
        .limit(limit)
        .all()
    )
    items = []
    for r in results:
        stream = db.query(Stream).filter(Stream.id == r.stream_id).first()
        items.append({
            "stream_id": r.stream_id,
            "stream_name": stream.stream_display_name if stream else "Unknown",
            "connections": r.connections,
        })
    return {"top_streams": items}


@router.get("/top-users")
def top_users(
    limit: int = 10,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    from src.domain.models import Line
    results = (
        db.query(
            Line.user_id,
            func.count(Line.id).label("connections"),
        )
        .group_by(Line.user_id)
        .order_by(func.count(Line.id).desc())
        .limit(limit)
        .all()
    )
    items = []
    for r in results:
        user = db.query(User).filter(User.id == r.user_id).first()
        items.append({
            "user_id": r.user_id,
            "username": user.username if user else "Unknown",
            "connections": r.connections,
        })
    return {"top_users": items}


@router.get("/recent-activity")
def recent_activity(
    limit: int = 20,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    from src.domain.models import UserActivity
    items = (
        db.query(UserActivity)
        .order_by(UserActivity.date_start.desc())
        .limit(limit)
        .all()
    )
    return {
        "activity": [
            {
                "id": a.id,
                "user_id": a.user_id,
                "stream_id": a.stream_id,
                "server_id": a.server_id,
                "ip": a.user_ip,
                "country": a.geoip_country_code,
                "date_start": a.date_start.isoformat() if a.date_start else None,
            }
            for a in items
        ]
    }


@router.get("/server-load")
def server_load(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    from src.domain.models import Line, Server
    servers = db.query(Server).all()
    result = []
    for s in servers:
        conn_count = db.query(func.count(Line.id)).filter(Line.server_id == s.id).scalar() or 0
        result.append({
            "server_id": s.id,
            "server_name": s.server_name,
            "status": s.status,
            "connections": conn_count,
            "total_clients": s.total_clients,
            "bandwidth_usage": s.total_bandwidth_usage,
        })
    return {"servers": result}


@router.get("/alerts")
def dashboard_alerts(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    from src.domain.models import Server, ServerStream
    alerts = []
    offline_servers = db.query(Server).filter(Server.status == 0).count()
    if offline_servers > 0:
        alerts.append({"level": "warning", "message": f"{offline_servers} server(s) offline"})
    error_streams = db.query(ServerStream).filter(ServerStream.stream_status == 3).count()
    if error_streams > 0:
        alerts.append({"level": "error", "message": f"{error_streams} stream(s) in error state"})
    expired = db.query(User).filter(User.exp_date < datetime.utcnow(), User.enabled.is_(True)).count()
    if expired > 0:
        alerts.append({"level": "info", "message": f"{expired} user(s) expired but still enabled"})
    return {"alerts": alerts}
