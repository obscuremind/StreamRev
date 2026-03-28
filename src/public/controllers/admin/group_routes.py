"""User group admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from src.core.database import get_db
from src.domain.models import User
from src.domain.group.service import UserGroupService
from .dependencies import get_current_admin

router = APIRouter(prefix="/groups", tags=["Admin User Groups"])


class GroupCreate(BaseModel):
    group_name: str
    can_delete: bool = True
    packages: Optional[str] = None


class GroupUpdate(BaseModel):
    group_name: Optional[str] = None
    can_delete: Optional[bool] = None
    packages: Optional[str] = None


class UserIdsRequest(BaseModel):
    user_ids: List[int]


@router.get("")
def list_groups(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"groups": UserGroupService(db).get_all()}


@router.get("/{group_id}")
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = UserGroupService(db).get_by_id(group_id)
    if not result:
        raise HTTPException(status_code=404, detail="Group not found")
    return result


@router.post("/create")
def create_group(
    data: GroupCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return UserGroupService(db).create(data.model_dump(exclude_none=True))


@router.put("/{group_id}")
def update_group(
    group_id: int,
    data: GroupUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = UserGroupService(db).update(group_id, data.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Group not found")
    return result


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not UserGroupService(db).delete(group_id):
        raise HTTPException(status_code=404, detail="Group not found or cannot be deleted")
    return {"status": "deleted"}


@router.get("/{group_id}/users")
def group_users(
    group_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"users": UserGroupService(db).get_users(group_id)}


@router.post("/{group_id}/add-users")
def add_users_to_group(
    group_id: int,
    data: UserIdsRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = UserGroupService(db).add_users(group_id, data.user_ids)
    return {"status": "added", "count": count}


@router.post("/{group_id}/remove-users")
def remove_users_from_group(
    group_id: int,
    data: UserIdsRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = UserGroupService(db).remove_users(group_id, data.user_ids)
    return {"status": "removed", "count": count}
