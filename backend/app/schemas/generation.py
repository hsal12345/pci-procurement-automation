from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    formats: Optional[List[str]] = Field(
        default=None,
        description="List of target formats: ['XLSX', 'DOCX', 'PDF', 'ZIP']. If omitted, generates all."
    )
    is_draft: Optional[bool] = Field(
        default=None,
        description="Optional override for DRAFT status. Defaults to revision approval state."
    )


class GenerationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    revision_id: UUID
    status: str
    progress_percent: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: Optional[UUID] = None
    revision_id: UUID
    doc_code: Optional[str] = None
    format: str
    filename: str
    file_size: int
    sha256_hash: str
    is_draft: bool
    archive_status: str
    created_at: datetime
    download_url: Optional[str] = None
