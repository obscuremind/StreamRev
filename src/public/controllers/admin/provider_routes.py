from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.domain.models import User
from src.domain.stream.provider_service import ProviderService

from .dependencies import get_current_admin

router = APIRouter(prefix="/providers", tags=["Admin Providers"])


@router.get("")
def list_providers(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return ProviderService(db).get_providers()


@router.get("/{domain}/streams")
def provider_streams(domain: str, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    streams = ProviderService(db).get_streams_by_provider(domain)
    return [{"id": s.id, "name": s.stream_display_name, "enabled": s.enabled} for s in streams]
