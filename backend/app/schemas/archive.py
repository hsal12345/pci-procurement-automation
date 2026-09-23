from datetime import datetime
from typing import Optional
from uuid import UUID
from app.schemas.common import BaseSchema


class ArchiveTriggerRequest(BaseSchema):
    revision_id: UUID


class ArchiveCallbackRequest(BaseSchema):
    archive_id: UUID
    status: str  # SYNCED, FAILED
    drive_folder_id: Optional[str] = None
    error_message: Optional[str] = None


class ArchiveRecordResponse(BaseSchema):
    id: UUID
    package_id: UUID
    revision_id: UUID
    target_provider: str
    folder_path: str
    drive_folder_id: Optional[str] = None
    status: str
    attempt_count: int
    last_error: Optional[str] = None
    last_attempt_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    created_at: datetime
