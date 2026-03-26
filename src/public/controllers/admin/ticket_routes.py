"""Simple ticket/support system for admin panel."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.domain.models import User
from src.domain.server.settings_service import SettingsService

from .dependencies import get_current_admin

router = APIRouter(prefix="/tickets", tags=["Admin Tickets"])


class TicketCreate(BaseModel):
    subject: str
    message: str
    priority: str = "normal"


class TicketReply(BaseModel):
    message: str


@router.get("")
def list_tickets(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("tickets_data", "[]")
    tickets = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    return {"tickets": tickets}


@router.post("")
def create_ticket(data: TicketCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("tickets_data", "[]")
    tickets = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    ticket = {
        "id": len(tickets) + 1,
        "subject": data.subject,
        "message": data.message,
        "priority": data.priority,
        "status": "open",
        "created_by": admin.username,
        "created_at": datetime.utcnow().isoformat(),
        "replies": [],
    }
    tickets.append(ticket)
    svc.set("tickets_data", tickets, "json")
    return ticket


@router.get("/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("tickets_data", "[]")
    tickets = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    for t in tickets:
        if t.get("id") == ticket_id:
            return t
    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/{ticket_id}/reply")
def reply_ticket(
    ticket_id: int, data: TicketReply, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    svc = SettingsService(db)
    raw = svc.get("tickets_data", "[]")
    tickets = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    for t in tickets:
        if t.get("id") == ticket_id:
            t["replies"].append(
                {"message": data.message, "by": admin.username, "at": datetime.utcnow().isoformat()}
            )
            svc.set("tickets_data", tickets, "json")
            return t
    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/{ticket_id}/close")
def close_ticket(ticket_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("tickets_data", "[]")
    tickets = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    for t in tickets:
        if t.get("id") == ticket_id:
            t["status"] = "closed"
            svc.set("tickets_data", tickets, "json")
            return t
    raise HTTPException(status_code=404, detail="Ticket not found")
