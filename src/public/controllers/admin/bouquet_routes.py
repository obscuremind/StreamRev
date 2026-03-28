from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any, List, Optional, Union

from src.core.database import get_db
from src.domain.bouquet.service import BouquetService
from src.domain.models import User
from .dependencies import get_current_admin

router = APIRouter(prefix="/bouquets", tags=["Admin Bouquets"])


class BouquetCreate(BaseModel):
    bouquet_name: str
    bouquet_channels: Union[str, List[int]] = "[]"
    bouquet_movies: Union[str, List[int]] = "[]"
    bouquet_radios: Union[str, List[int]] = "[]"
    bouquet_series: Union[str, List[int]] = "[]"
    bouquet_order: int = 0


class BouquetUpdate(BaseModel):
    bouquet_name: Optional[str] = None
    bouquet_channels: Optional[Union[str, List[int]]] = None
    bouquet_movies: Optional[Union[str, List[int]]] = None
    bouquet_radios: Optional[Union[str, List[int]]] = None
    bouquet_series: Optional[Union[str, List[int]]] = None
    bouquet_order: Optional[int] = None


def _normalize_bouquet_payload(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    for key in (
        "bouquet_channels",
        "bouquet_movies",
        "bouquet_radios",
        "bouquet_series",
    ):
        if key not in out or out[key] is None:
            continue
        val = out[key]
        if isinstance(val, list):
            continue
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    out[key] = [int(x) for x in parsed]
                else:
                    out[key] = val
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
    return out


@router.get("")
def list_bouquets(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return [_bouquet_to_dict(b) for b in BouquetService(db).get_all()]


@router.get("/{bouquet_id}")
def get_bouquet(
    bouquet_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    b = BouquetService(db).get_by_id(bouquet_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bouquet not found")
    return _bouquet_to_dict(b)


@router.post("")
def create_bouquet(
    data: BouquetCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    payload = _normalize_bouquet_payload(data.model_dump(exclude_none=True))
    return _bouquet_to_dict(BouquetService(db).create(payload))


@router.put("/{bouquet_id}")
def update_bouquet(
    bouquet_id: int,
    data: BouquetUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    payload = _normalize_bouquet_payload(data.model_dump(exclude_none=True))
    b = BouquetService(db).update(bouquet_id, payload)
    if not b:
        raise HTTPException(status_code=404, detail="Bouquet not found")
    return _bouquet_to_dict(b)


@router.delete("/{bouquet_id}")
def delete_bouquet(
    bouquet_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not BouquetService(db).delete(bouquet_id):
        raise HTTPException(status_code=404, detail="Bouquet not found")
    return {"status": "deleted"}


def _bouquet_to_dict(b) -> dict[str, Any]:
    svc = BouquetService
    return {
        "id": b.id,
        "bouquet_name": b.bouquet_name,
        "bouquet_channels": svc.get_channel_ids(b),
        "bouquet_movies": svc.get_movie_ids(b),
        "bouquet_radios": _parse_id_list(b.bouquet_radios),
        "bouquet_series": svc.get_series_ids(b),
        "bouquet_order": b.bouquet_order,
    }


def _parse_id_list(raw: str) -> list[int]:
    try:
        data = json.loads(raw or "[]")
        return [int(x) for x in data] if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError, ValueError):
        return []



class ReorderRequest(BaseModel):
    order: List[int]


class StreamIdsRequest(BaseModel):
    stream_ids: List[int]


class BatchDeleteRequest(BaseModel):
    ids: List[int]


@router.post("/reorder")
def reorder_bouquets(
    data: ReorderRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = BouquetService(db)
    for idx, bouquet_id in enumerate(data.order):
        b = svc.get_by_id(bouquet_id)
        if b:
            b.bouquet_order = idx
    db.commit()
    return {"status": "reordered"}


@router.post("/{bouquet_id}/reorder-channels")
def reorder_channels(
    bouquet_id: int,
    data: ReorderRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = BouquetService(db)
    b = svc.get_by_id(bouquet_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bouquet not found")
    svc.update(bouquet_id, {"bouquet_channels": data.order})
    return {"status": "reordered", "bouquet_id": bouquet_id}


@router.post("/{bouquet_id}/add-streams")
def add_streams_to_bouquet(
    bouquet_id: int,
    data: StreamIdsRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = BouquetService(db)
    b = svc.get_by_id(bouquet_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bouquet not found")
    current = svc.get_channel_ids(b)
    for sid in data.stream_ids:
        if sid not in current:
            current.append(sid)
    svc.update(bouquet_id, {"bouquet_channels": current})
    return {"status": "added", "bouquet_id": bouquet_id, "channels": current}


@router.post("/{bouquet_id}/remove-streams")
def remove_streams_from_bouquet(
    bouquet_id: int,
    data: StreamIdsRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = BouquetService(db)
    b = svc.get_by_id(bouquet_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bouquet not found")
    current = svc.get_channel_ids(b)
    current = [sid for sid in current if sid not in data.stream_ids]
    svc.update(bouquet_id, {"bouquet_channels": current})
    return {"status": "removed", "bouquet_id": bouquet_id, "channels": current}


@router.get("/{bouquet_id}/channels")
def get_bouquet_channels(
    bouquet_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = BouquetService(db)
    b = svc.get_by_id(bouquet_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bouquet not found")
    return {
        "bouquet_id": bouquet_id,
        "channels": svc.get_channel_ids(b),
        "movies": svc.get_movie_ids(b),
        "series": svc.get_series_ids(b),
    }


@router.post("/batch-delete")
def batch_delete_bouquets(
    data: BatchDeleteRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = BouquetService(db)
    count = 0
    for bid in data.ids:
        if svc.delete(bid):
            count += 1
    return {"status": "deleted", "count": count}
