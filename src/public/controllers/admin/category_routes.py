from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any, Optional

from src.core.database import get_db
from src.domain.category.service import CategoryService
from src.domain.models import User
from .dependencies import get_current_admin

router = APIRouter(prefix="/categories", tags=["Admin Categories"])


class CategoryCreate(BaseModel):
    category_name: str
    category_type: str = "live"
    parent_id: Optional[int] = None
    order: int = 0


class CategoryUpdate(BaseModel):
    category_name: Optional[str] = None
    category_type: Optional[str] = None
    parent_id: Optional[int] = None
    order: Optional[int] = None


@router.get("")
def list_categories(
    page: int = Query(1, ge=1),
    per_page: int = Query(200, ge=1, le=500),
    category_type: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = CategoryService(db)
    items = svc.get_all(category_type=category_type)
    total = len(items)
    start = (page - 1) * per_page
    page_items = items[start : start + per_page]
    return {
        "items": [_category_to_dict(c) for c in page_items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/live")
def list_live_categories(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return [_category_to_dict(c) for c in CategoryService(db).get_live_categories()]


@router.get("/movie")
def list_movie_categories(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return [_category_to_dict(c) for c in CategoryService(db).get_movie_categories()]


@router.get("/series")
def list_series_categories(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return [_category_to_dict(c) for c in CategoryService(db).get_series_categories()]


@router.get("/radio")
def list_radio_categories(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return [_category_to_dict(c) for c in CategoryService(db).get_radio_categories()]


@router.get("/{category_id}")
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    cat = CategoryService(db).get_by_id(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return _category_to_dict(cat)


@router.post("")
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return _category_to_dict(
        CategoryService(db).create(data.model_dump(exclude_none=True))
    )


@router.put("/{category_id}")
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    cat = CategoryService(db).update(category_id, data.model_dump(exclude_none=True))
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return _category_to_dict(cat)


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not CategoryService(db).delete(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    return {"status": "deleted"}


def _category_to_dict(c) -> dict[str, Any]:
    return {
        "id": c.id,
        "category_name": c.category_name,
        "category_type": c.category_type,
        "parent_id": c.parent_id,
        "order": c.order,
    }
