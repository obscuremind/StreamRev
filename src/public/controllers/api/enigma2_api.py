"""
Enigma2-style XML API for satellite / Linux receivers (OpenWebif-compatible patterns).

Responses are UTF-8 XML with ``e2bouquetlist``, ``e2servicelist``, and ``e2eventlist`` roots.
"""

from __future__ import annotations

import base64
import html
import json
from typing import Any, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from src.core.auth.password import verify_password
from src.core.database import get_db
from src.domain.epg.service import EpgService
from src.domain.models import Bouquet, EpgData, Series, Stream, User
from src.domain.stream.service import StreamService
from src.domain.user.service import UserService
from src.domain.vod.service import SeriesService

router = APIRouter(tags=["Enigma2 API"])


def _esc(text: Optional[str]) -> str:
    return html.escape(text or "", quote=True)


def _b64_utf8(text: Optional[str]) -> str:
    return base64.b64encode((text or "").encode("utf-8")).decode("ascii")


def _parse_bouquet_channel_ids(bouquet: Bouquet) -> List[int]:
    try:
        raw = json.loads(bouquet.bouquet_channels or "[]")
        if not isinstance(raw, list):
            return []
        out: List[int] = []
        for x in raw:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        return out
    except (json.JSONDecodeError, TypeError):
        return []


def _authenticate(username: str, password: str, db: Session) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=403, detail="Invalid credentials")
    if not verify_password(password, user.password):
        raise HTTPException(status_code=403, detail="Invalid credentials")
    if not user.enabled:
        raise HTTPException(status_code=403, detail="Account disabled")
    svc = UserService(db)
    if svc.is_expired(user):
        raise HTTPException(status_code=403, detail="Account expired")
    return user


def _bouquets_for_user(db: Session, user: User) -> List[Bouquet]:
    q = db.query(Bouquet).order_by(Bouquet.bouquet_order.asc(), Bouquet.id.asc())
    all_b = q.all()
    raw = (user.bouquet or "").strip()
    if not raw:
        return all_b
    wanted: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            wanted.add(int(part))
        except ValueError:
            continue
    if not wanted:
        return all_b
    return [b for b in all_b if b.id in wanted]


def _bouquet_serviceref(bouquet: Bouquet) -> str:
    return (
        f'1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquet_{bouquet.id}.tv" ORDER BY bouquet'
    )


def _channel_serviceref(request: Request, username: str, password: str, stream: Stream) -> str:
    base = str(request.base_url).rstrip("/")
    url = f"{base}/live/{username}/{password}/{stream.id}.ts"
    enc = quote(url, safe="")
    return f"1:0:1:{stream.id}:0:0:0:0:0:0:{enc}"


def _xml_bouquet_list(bouquets: List[Bouquet]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<e2bouquetlist>",
    ]
    for b in bouquets:
        lines.append("  <e2bouquet>")
        lines.append(f"    <e2servicereference>{_esc(_bouquet_serviceref(b))}</e2servicereference>")
        lines.append(f"    <e2servicename>{_esc(b.bouquet_name)}</e2servicename>")
        lines.append("  </e2bouquet>")
    lines.append("</e2bouquetlist>")
    return "\n".join(lines)


def _xml_service_list_bouquets(bouquets: List[Bouquet]) -> str:
    """Service reference list when no action is specified (bouquet entries as services)."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<e2servicelist>",
    ]
    for b in bouquets:
        lines.append("  <e2service>")
        lines.append(f"    <e2servicereference>{_esc(_bouquet_serviceref(b))}</e2servicereference>")
        lines.append(f"    <e2servicename>{_esc(b.bouquet_name)}</e2servicename>")
        lines.append("  </e2service>")
    lines.append("</e2servicelist>")
    return "\n".join(lines)


def _xml_channel_list(
    request: Request,
    username: str,
    password: str,
    streams: List[Stream],
) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<e2servicelist>",
    ]
    for s in streams:
        lines.append("  <e2service>")
        lines.append(
            f"    <e2servicereference>{_esc(_channel_serviceref(request, username, password, s))}</e2servicereference>"
        )
        lines.append(f"    <e2servicename>{_esc(s.stream_display_name)}</e2servicename>")
        lines.append("  </e2service>")
    lines.append("</e2servicelist>")
    return "\n".join(lines)


def _xml_seasons_list(series: Series, season_numbers: List[int]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<e2seasonlist>",
    ]
    for sn in season_numbers:
        lines.append("  <e2season>")
        lines.append(f"    <e2seasonnumber>{int(sn)}</e2seasonnumber>")
        lines.append(f"    <e2seasontitle>{_b64_utf8(f'Season {sn}')}</e2seasontitle>")
        lines.append("  </e2season>")
    lines.append("</e2seasonlist>")
    return "\n".join(lines)


def _xml_series_streams(
    request: Request,
    username: str,
    password: str,
    series: Series,
    episodes: List[Any],
) -> str:
    base = str(request.base_url).rstrip("/")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<e2streamlist>",
    ]
    for ep in episodes:
        ext = ep.container_extension or "mp4"
        url = f"{base}/series/{username}/{password}/{ep.id}.{ext}"
        title_b64 = _b64_utf8(ep.stream_display_name or "")
        lines.append("  <e2stream>")
        lines.append(f"    <e2title>{title_b64}</e2title>")
        lines.append(f"    <e2episode>{int(ep.episode_number)}</e2episode>")
        lines.append(f"    <e2season>{int(ep.season_number or 1)}</e2season>")
        lines.append("    <e2location><![CDATA[" + url + "]]></e2location>")
        lines.append("  </e2stream>")
    lines.append("</e2streamlist>")
    return "\n".join(lines)


def _xml_series_catalog(rows: List[Series]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<e2servicelist>",
    ]
    for s in rows:
        title_b64 = _b64_utf8(s.title or "")
        lines.append("  <e2service>")
        lines.append(f"    <e2servicereference>{_esc(str(s.id))}</e2servicereference>")
        lines.append(f"    <e2servicename>{title_b64}</e2servicename>")
        lines.append("  </e2service>")
    lines.append("</e2servicelist>")
    return "\n".join(lines)


def _xml_epg(programs: List[EpgData], stream: Stream) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<e2eventlist>",
    ]
    for p in programs:
        dur = 0
        if p.start and p.end:
            dur = int((p.end - p.start).total_seconds())
        start_ts = int(p.start.timestamp()) if p.start else 0
        lines.append("  <e2event>")
        lines.append(f"    <e2eventid>{p.id}</e2eventid>")
        lines.append(f"    <e2eventservicename>{_esc(stream.stream_display_name)}</e2eventservicename>")
        lines.append(f"    <e2eventtitle>{_esc(p.title)}</e2eventtitle>")
        lines.append(f"    <e2eventstart>{start_ts}</e2eventstart>")
        lines.append(f"    <e2eventduration>{dur}</e2eventduration>")
        lines.append(
            f"    <e2eventdescriptionextended>{_esc(p.description or '')}</e2eventdescriptionextended>"
        )
        lines.append("  </e2event>")
    lines.append("</e2eventlist>")
    return "\n".join(lines)


def _load_bouquet_streams(
    db: Session,
    bouquet: Bouquet,
) -> List[Stream]:
    ids = _parse_bouquet_channel_ids(bouquet)
    if not ids:
        return []
    rows = (
        db.query(Stream)
        .filter(Stream.id.in_(ids), Stream.enabled.is_(True), Stream.stream_type == 1)
        .all()
    )
    order = {sid: i for i, sid in enumerate(ids)}
    rows.sort(key=lambda s: (order.get(s.id, 9999), s.id))
    return rows


def _handle_enigma2(
    request: Request,
    db: Session,
    username: str,
    password: str,
    action: Optional[str],
    bouquet_id: Optional[int],
    stream_id: Optional[int],
    series_id: Optional[int],
    season: Optional[int],
    cat_id: Optional[int],
) -> Response:
    user = _authenticate(username, password, db)
    bouquets = _bouquets_for_user(db, user)
    stream_svc = StreamService(db)
    epg_svc = EpgService(db)
    series_svc = SeriesService(db)

    act = (action or "").strip().lower() if action else ""

    if act == "get_bouquets":
        body = _xml_bouquet_list(bouquets)
        return Response(content=body, media_type="application/xml")

    if act == "get_channels":
        if bouquet_id is None:
            raise HTTPException(status_code=400, detail="bouquet_id required")
        allowed_ids = {b.id for b in bouquets}
        bouquet = db.query(Bouquet).filter(Bouquet.id == bouquet_id).first()
        if not bouquet or bouquet.id not in allowed_ids:
            raise HTTPException(status_code=404, detail="Bouquet not found")
        streams = _load_bouquet_streams(db, bouquet)
        body = _xml_channel_list(request, username, password, streams)
        return Response(content=body, media_type="application/xml")

    if act == "get_epg":
        if stream_id is None:
            raise HTTPException(status_code=400, detail="stream_id required")
        stream = stream_svc.get_by_id(stream_id)
        if not stream or not stream.enabled:
            raise HTTPException(status_code=404, detail="Stream not found")
        if not stream.epg_channel_id:
            body = _xml_epg([], stream)
            return Response(content=body, media_type="application/xml")
        programs = epg_svc.get_all_programs(stream.epg_channel_id)
        body = _xml_epg(programs[:200], stream)
        return Response(content=body, media_type="application/xml")

    if act == "get_seasons":
        if series_id is None:
            raise HTTPException(status_code=400, detail="series_id required")
        series = series_svc.get_by_id(series_id)
        if not series:
            raise HTTPException(status_code=404, detail="Series not found")
        episodes = series_svc.get_episodes(series_id)
        season_set = sorted({int(ep.season_number or 1) for ep in episodes})
        body = _xml_seasons_list(series, season_set)
        return Response(content=body, media_type="application/xml")

    if act == "get_series_streams":
        if series_id is None or season is None:
            raise HTTPException(status_code=400, detail="series_id and season required")
        series = series_svc.get_by_id(series_id)
        if not series:
            raise HTTPException(status_code=404, detail="Series not found")
        episodes = [
            ep
            for ep in series_svc.get_episodes(series_id)
            if int(ep.season_number or 1) == int(season)
        ]
        episodes.sort(key=lambda e: (e.episode_number or 0, e.id))
        body = _xml_series_streams(request, username, password, series, episodes)
        return Response(content=body, media_type="application/xml")

    if act == "get_series":
        if cat_id is None:
            raise HTTPException(status_code=400, detail="cat_id required")
        result = series_svc.get_all(category_id=cat_id, per_page=10_000)
        body = _xml_series_catalog(result["items"])
        return Response(content=body, media_type="application/xml")

    body = _xml_service_list_bouquets(bouquets)
    return Response(content=body, media_type="application/xml")


@router.get("/enigma2.php")
def enigma2_php(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Query(...),
    password: str = Query(...),
    action: Optional[str] = Query(None),
    bouquet_id: Optional[int] = Query(None),
    stream_id: Optional[int] = Query(None),
    series_id: Optional[int] = Query(None),
    season: Optional[int] = Query(None),
    cat_id: Optional[int] = Query(None),
):
    return _handle_enigma2(
        request,
        db,
        username,
        password,
        action,
        bouquet_id,
        stream_id,
        series_id,
        season,
        cat_id,
    )


@router.get("/enigma2/{username}/{password}/get_bouquets")
def enigma2_get_bouquets_path(
    request: Request,
    username: str,
    password: str,
    db: Session = Depends(get_db),
):
    return _handle_enigma2(
        request, db, username, password, "get_bouquets", None, None, None, None, None
    )


@router.get("/enigma2/{username}/{password}/channels/{bouquet_id}")
def enigma2_channels_path(
    request: Request,
    username: str,
    password: str,
    bouquet_id: int,
    db: Session = Depends(get_db),
):
    return _handle_enigma2(
        request,
        db,
        username,
        password,
        "get_channels",
        bouquet_id,
        None,
        None,
        None,
        None,
    )
