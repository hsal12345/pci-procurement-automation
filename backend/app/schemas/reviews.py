from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import Field
from app.schemas.common import BaseSchema


class SubmitReviewRequest(BaseSchema):
    expected_version: int = Field(..., description="Optimistic concurrency lock token")
    notes: Optional[str] = None


class WithdrawReviewRequest(BaseSchema):
    expected_version: int = Field(..., description="Optimistic concurrency lock token")
    reason: str = Field(..., min_length=3, description="Alasan penarikan pengajuan revisi")


class ReturnReviewRequest(BaseSchema):
    expected_version: int = Field(..., description="Optimistic concurrency lock token")
    comment: str = Field(..., min_length=3, description="Catatan koreksi pengembalian dari Direktur Keuangan")


class ApproveReviewRequest(BaseSchema):
    expected_version: int = Field(..., description="Optimistic concurrency lock token")
    manifest_hash: Optional[str] = Field(None, description="SHA-256 hash dari manifest draft yang ditinjau")
    note: Optional[str] = None


class IssueRequest(BaseSchema):
    expected_version: Optional[int] = Field(None, description="Optimistic concurrency lock token")
    notes: Optional[str] = None


class ReopenPackageRequest(BaseSchema):
    reason: str = Field(..., min_length=3, description="Alasan pembukaan kembali paket yang telah diterbitkan")
    expected_version: Optional[int] = Field(None, description="Optimistic concurrency lock token")


class CancelPackageRequest(BaseSchema):
    reason: str = Field(..., min_length=3, description="Alasan pembatalan paket pengadaan")
    expected_version: Optional[int] = Field(None, description="Optimistic concurrency lock token")


class WorkflowActionResponse(BaseSchema):
    package_id: UUID
    revision_id: UUID
    previous_status: str
    new_status: str
    package_status: str
    version: int
    message: str
    timestamp: datetime
