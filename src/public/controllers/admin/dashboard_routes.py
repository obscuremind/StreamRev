from __future__ import annotations

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
