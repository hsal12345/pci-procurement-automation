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
    drive_folder_url: Optional[str] = None
    error_message: Optional[str] = None


class ArchiveRecordResponse(BaseSchema):
    id: UUID
    package_id: UUID
    revision_id: UUID
    target_provider: str
    folder_path: str
    drive_folder_id: Optional[str] = None
    drive_folder_url: Optional[str] = None
    status: str
    progress_percent: int = 0
    current_step: Optional[str] = None
    uploaded_files: int = 0
    total_files: int = 0
    total_bytes: int = 0
    attempt_count: int
    last_error: Optional[str] = None
    last_attempt_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    created_at: datetime
    revision_number: Optional[int] = None
