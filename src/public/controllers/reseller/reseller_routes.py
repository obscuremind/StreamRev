"""XC_VM-compatible reseller web-scope routes.

These routes mirror key `/reseller/*` pages from XC_VM and map them onto
StreamRev reseller API/domain services.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Query, Cookie
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.domain.models import Reseller

from .reseller_api import (
    ResellerLoginRequest,
    ResellerProfileUpdate,
    ResellerTicketCreate,
    ResellerTicketReply,
    reseller_create_ticket,
    reseller_created_channels,
    reseller_episodes,
    reseller_epg,
    reseller_get_profile,
    reseller_get_ticket,
    reseller_info,
    reseller_line_activity,
    reseller_lines,
    reseller_list_enigmas,
    reseller_list_mags,
    reseller_list_tickets,
    reseller_live_connections,
    reseller_login,
    reseller_movies,
    reseller_radios,
    reseller_reply_ticket,
    reseller_streams,
    reseller_update_profile,
    reseller_users,
)

router = APIRouter(prefix="/reseller", tags=["Reseller Web"])


def _token_from_header_or_query(
    authorization: Optional[str],
    token: Optional[str],
) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    if token:
        return token
    raise HTTPException(status_code=401, detail="Missing reseller token")


def _reseller_from_token(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
    reseller_token: Optional[str] = Cookie(default=None),
) -> Reseller:
    from src.core.auth import decode_access_token

    jwt_token = _token_from_header_or_query(authorization, token or reseller_token)
    payload = decode_access_token(jwt_token)
    if not payload or payload.get("role") != "reseller":
        raise HTTPException(status_code=401, detail="Invalid token")
    reseller = db.query(Reseller).filter(Reseller.id == int(payload["sub"])).first()
    if not reseller or reseller.status != 1:
        raise HTTPException(status_code=403, detail="Reseller access denied")
    return reseller


@router.get("/login")
def reseller_login_page():
    return {
        "scope": "reseller",
        "message": "POST /reseller/login with username/password to authenticate.",
    }


@router.get("/index")
def reseller_index():
    """XC_VM alias for reseller login page."""
    return reseller_login_page()


@router.post("/login")
def reseller_login_submit(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    return reseller_login(ResellerLoginRequest(username=username, password=password), db)


@router.get("/logout")
def reseller_logout():
    return {"status": "ok", "message": "Logged out. Invalidate token on client side."}


@router.get("/session")
def reseller_session(reseller: Reseller = Depends(_reseller_from_token)):
    return reseller_info(reseller)


@router.get("/dashboard")
def reseller_dashboard(
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    users = reseller_users(page=1, per_page=1, db=db, reseller=reseller)
    lines = reseller_lines(page=1, per_page=1, db=db, reseller=reseller)
    live = reseller_live_connections(db=db, reseller=reseller)
    return {
        "reseller": reseller_info(reseller),
        "stats": {
            "users_total": users["total"],
            "lines_total": lines["total"],
            "live_connections": live["total"],
            "credits": reseller.credits,
        },
    }


@router.get("/api")
def reseller_api_alias(
    action: str = Query("info"),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    """XC_VM reseller/api compatibility multiplexer."""
    action = action.lower().strip()
    if action in {"info", "session"}:
        return reseller_info(reseller)
    if action == "dashboard":
        return reseller_dashboard(db=db, reseller=reseller)
    if action == "tickets":
        return reseller_list_tickets(db=db, reseller=reseller)
    if action == "users":
        return reseller_users(page=1, per_page=100, db=db, reseller=reseller)
    raise HTTPException(status_code=400, detail=f"Unsupported action '{action}'")


@router.post("/api")
def reseller_api_alias_post(
    action: str = Form(...),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_api_alias(action=action, db=db, reseller=reseller)


@router.get("/table")
def reseller_table_alias(
    table: str = Query("users"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    """XC_VM reseller/table compatibility endpoint."""
    key = table.lower().strip()
    if key == "users":
        return reseller_users(page=page, per_page=per_page, db=db, reseller=reseller)
    if key == "lines":
        return reseller_lines(page=page, per_page=per_page, db=db, reseller=reseller)
    if key == "streams":
        return reseller_streams(page=page, per_page=per_page, db=db, reseller=reseller)
    if key == "movies":
        return reseller_movies(page=page, per_page=per_page, db=db, reseller=reseller)
    raise HTTPException(status_code=400, detail=f"Unsupported table '{table}'")


@router.post("/table")
def reseller_table_alias_post(
    table: str = Form("users"),
    page: int = Form(1),
    per_page: int = Form(50),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_table_alias(table=table, page=page, per_page=per_page, db=db, reseller=reseller)


@router.post("/post")
def reseller_post_alias(
    action: str = Form(...),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    """XC_VM compatibility endpoint for generic reseller POST actions."""
    action = action.lower().strip()
    if action == "logout":
        return reseller_logout()
    if action == "session":
        return reseller_info(reseller)
    if action == "profile":
        return reseller_get_profile(reseller)
    if action == "update_profile":
        payload = ResellerProfileUpdate()
        return reseller_update_profile(data=payload, db=db, reseller=reseller)
    if action == "create_ticket":
        ticket = ResellerTicketCreate(subject="Ticket", message="Created from post action", priority="normal")
        return reseller_create_ticket(data=ticket, db=db, reseller=reseller)
    if action == "reply_ticket":
        tickets = reseller_list_tickets(db=db, reseller=reseller).get("tickets", [])
        if not tickets:
            raise HTTPException(status_code=400, detail="No tickets available to reply")
        ticket_id = tickets[0]["id"]
        return reseller_reply_ticket(
            ticket_id=ticket_id,
            data=ResellerTicketReply(message="Auto reply from /reseller/post"),
            db=db,
            reseller=reseller,
        )
    raise HTTPException(status_code=400, detail=f"Unsupported post action '{action}'")


@router.get("/resize")
def reseller_resize(reseller: Reseller = Depends(_reseller_from_token)):
    """XC_VM compatibility endpoint used by legacy reseller UI."""
    return {"status": "ok", "reseller_id": reseller.id}


@router.get("/edit_profile")
def reseller_edit_profile(reseller: Reseller = Depends(_reseller_from_token)):
    return reseller_get_profile(reseller)


@router.get("/users")
def reseller_users_page(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_users(page=page, per_page=per_page, db=db, reseller=reseller)


@router.get("/user")
def reseller_user_page(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    """XC_VM alias: /reseller/user."""
    return reseller_users(page=page, per_page=per_page, db=db, reseller=reseller)


@router.get("/streams")
def reseller_streams_page(
    category_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_streams(category_id=category_id, page=page, per_page=per_page, db=db, reseller=reseller)


@router.get("/movies")
def reseller_movies_page(
    category_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_movies(category_id=category_id, page=page, per_page=per_page, db=db, reseller=reseller)


@router.get("/radios")
def reseller_radios_page(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_radios(page=page, per_page=per_page, db=db, reseller=reseller)


@router.get("/episodes")
def reseller_episodes_page(
    series_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_episodes(series_id=series_id, page=page, per_page=per_page, db=db, reseller=reseller)


@router.get("/created_channels")
def reseller_created_channels_page(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_created_channels(page=page, per_page=per_page, db=db, reseller=reseller)


@router.get("/epg_view")
def reseller_epg_view(
    epg_id: Optional[str] = None,
    channel_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_epg(
        epg_id=epg_id,
        channel_id=channel_id,
        page=page,
        per_page=per_page,
        db=db,
        reseller=reseller,
    )


@router.get("/lines")
def reseller_lines_page(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_lines(page=page, per_page=per_page, db=db, reseller=reseller)


@router.get("/line")
def reseller_line_page(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    """XC_VM alias: /reseller/line."""
    return reseller_lines(page=page, per_page=per_page, db=db, reseller=reseller)


@router.get("/line_activity")
def reseller_line_activity_page(
    line_id: int = Query(...),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_line_activity(line_id=line_id, limit=limit, db=db, reseller=reseller)


@router.get("/live_connections")
def reseller_live_connections_page(
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_live_connections(db=db, reseller=reseller)


@router.get("/mags")
def reseller_mags_page(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_list_mags(page=page, per_page=per_page, search=search, db=db, reseller=reseller)


@router.get("/mag")
def reseller_mag_page(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    """XC_VM alias: /reseller/mag."""
    return reseller_list_mags(page=page, per_page=per_page, search=search, db=db, reseller=reseller)


@router.get("/enigmas")
def reseller_enigmas_page(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_list_enigmas(page=page, per_page=per_page, search=search, db=db, reseller=reseller)


@router.get("/enigma")
def reseller_enigma_page(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    """XC_VM alias: /reseller/enigma."""
    return reseller_list_enigmas(page=page, per_page=per_page, search=search, db=db, reseller=reseller)


@router.get("/tickets")
def reseller_tickets_page(
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    return reseller_list_tickets(db=db, reseller=reseller)


@router.get("/ticket")
def reseller_ticket_page(
    ticket_id: int = Query(...),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    """XC_VM alias: /reseller/ticket."""
    return reseller_get_ticket(ticket_id=ticket_id, db=db, reseller=reseller)


@router.get("/ticket_view")
def reseller_ticket_view_page(
    ticket_id: int = Query(...),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    """XC_VM alias: /reseller/ticket_view."""
    return reseller_get_ticket(ticket_id=ticket_id, db=db, reseller=reseller)


@router.get("/user_logs")
def reseller_user_logs_page(
    user_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(_reseller_from_token),
):
    """XC_VM-compatible user logs endpoint using activity records."""
    from src.domain.models import UserActivity

    q = db.query(UserActivity)
    uid_set = {u["id"] for u in reseller_users(page=1, per_page=100000, db=db, reseller=reseller)["items"]}
    if user_id is not None:
        if user_id not in uid_set:
            raise HTTPException(status_code=404, detail="User not found")
        q = q.filter(UserActivity.user_id == user_id)
    else:
        if not uid_set:
            return {"items": []}
        q = q.filter(UserActivity.user_id.in_(uid_set))
    rows = q.order_by(UserActivity.date_start.desc()).limit(limit).all()
    return {
        "items": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "stream_id": r.stream_id,
                "server_id": r.server_id,
                "user_ip": r.user_ip,
                "user_agent": r.user_agent,
                "date_start": str(r.date_start) if r.date_start else None,
                "date_stop": str(r.date_stop) if r.date_stop else None,
            }
            for r in rows
        ]
    }
