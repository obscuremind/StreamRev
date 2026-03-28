"""Stream type admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.domain.models import StreamType, User
from .dependencies import get_current_admin

router = APIRouter(prefix="/stream-types", tags=["Admin Stream Types"])


class StreamTypeCreate(BaseModel):
    type_name: str
    type_key: str
    type_output: str = ""
    live: bool = True


class StreamTypeUpdate(BaseModel):
    type_name: Optional[str] = None
    type_key: Optional[str] = None
    type_output: Optional[str] = None
    live: Optional[bool] = None


@router.get("")
def list_stream_types(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    items = db.query(StreamType).order_by(StreamType.type_id.asc()).all()
    return {
        "stream_types": [
            {
                "type_id": st.type_id,
                "type_name": st.type_name,
                "type_key": st.type_key,
                "type_output": st.type_output,
                "live": st.live,
            }
            for st in items
        ]
    }


@router.post("/create")
def create_stream_type(
    data: StreamTypeCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    st = StreamType(**data.model_dump())
    db.add(st)
    db.commit()
    db.refresh(st)
    return {
        "type_id": st.type_id,
        "type_name": st.type_name,
        "type_key": st.type_key,
        "type_output": st.type_output,
        "live": st.live,
    }


@router.put("/{type_id}")
def update_stream_type(
    type_id: int,
    data: StreamTypeUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    st = db.query(StreamType).filter(StreamType.type_id == type_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Stream type not found")
    for key, value in data.model_dump(exclude_none=True).items():
        if hasattr(st, key):
            setattr(st, key, value)
    db.commit()
    db.refresh(st)
    return {
        "type_id": st.type_id,
        "type_name": st.type_name,
        "type_key": st.type_key,
        "type_output": st.type_output,
        "live": st.live,
    }


@router.delete("/{type_id}")
def delete_stream_type(
    type_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    st = db.query(StreamType).filter(StreamType.type_id == type_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Stream type not found")
    db.delete(st)
    db.commit()
    return {"status": "deleted"}
