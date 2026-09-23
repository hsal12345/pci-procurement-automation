from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.v1.internal import verify_internal_service_key
from app.schemas.archive import (
    ArchiveTriggerRequest,
    ArchiveCallbackRequest,
    ArchiveRecordResponse,
)
from app.services.archive_service import archive_service

router = APIRouter(prefix="/internal/archive", tags=["Internal Archive Sync"])


@router.post(
    "/trigger",
    response_model=ArchiveRecordResponse,
    status_code=status.HTTP_201_CREATED
)
async def trigger_archive_registration(
    payload: ArchiveTriggerRequest,
    db: AsyncSession = Depends(get_db),
    key: str = Depends(verify_internal_service_key)
):
    """Internal endpoint called upon final package issuance to register Google Drive upload."""
    return await archive_service.register_archive_request(db, payload.revision_id)


@router.get(
    "/pending",
    response_model=List[ArchiveRecordResponse]
)
async def list_pending_archives(
    db: AsyncSession = Depends(get_db),
    key: str = Depends(verify_internal_service_key)
):
    """Polled by n8n or background cron to fetch packages requiring Google Drive synchronization."""
    return await archive_service.get_pending_archives(db)


@router.post(
    "/callback",
    response_model=ArchiveRecordResponse
)
async def process_archive_callback(
    payload: ArchiveCallbackRequest,
    db: AsyncSession = Depends(get_db),
    key: str = Depends(verify_internal_service_key)
):
    """Callback invoked by n8n or worker to record upload success (SYNCED) or failure (FAILED)."""
    return await archive_service.process_callback(
        db=db,
        archive_id=payload.archive_id,
        status_val=payload.status,
        drive_folder_id=payload.drive_folder_id,
        error_message=payload.error_message
    )
