from datetime import datetime
from typing import Optional, List
from uuid import UUID
from app.schemas.common import BaseSchema, SeverityEnum, DispositionEnum


class FindingResponse(BaseSchema):
    id: UUID
    run_id: UUID
    rule_code: str  # BR01..BR15
    severity: SeverityEnum
    doc_code: Optional[str] = None
    sheet_name: Optional[str] = None
    cell_range: Optional[str] = None
    field_name: Optional[str] = None
    original_value: Optional[str] = None
    proposed_value: Optional[str] = None
    message: str
    disposition: DispositionEnum
    disposition_reason: Optional[str] = None
    disposition_actor: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ValidationRunResponse(BaseSchema):
    id: UUID
    revision_id: UUID
    triggered_by: Optional[str] = None
    run_at: datetime
    passed: bool
    error_count: int
    warning_count: int
    info_count: int
    created_at: datetime
    updated_at: datetime
    findings: List[FindingResponse] = []


class FindingDispositionRequest(BaseSchema):
    disposition: DispositionEnum  # ACKNOWLEDGED, OVERRIDDEN, RESOLVED
    disposition_reason: str
    disposition_actor: str = "finance_director"
