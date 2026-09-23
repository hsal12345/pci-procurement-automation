from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from app.schemas.common import BaseSchema


class ImportUploadResponse(BaseSchema):
    import_id: UUID
    filename: str
    file_hash: str
    status: str
    message: str


class DiscrepancyItem(BaseSchema):
    sheet_name: str
    cell_coordinate: Optional[str] = None
    rule_category: str  # EXTERNAL_LINK, ENTITY_MISMATCH, DATE_INVERSION, INCOMPLETE_ROWS, STALE_NUMBER
    severity: str  # BLOCK, WARNING
    field: str
    found_value: Any
    expected_or_note: str


class ImportPreviewResponse(BaseSchema):
    import_id: UUID
    filename: str
    status: str
    school_candidate: Dict[str, Any]
    transaction_metadata: Dict[str, Any]
    candidate_lines: List[Dict[str, Any]]
    events_candidate: List[Dict[str, Any]]
    detected_discrepancies: List[DiscrepancyItem]
    can_proceed_to_confirm: bool


class ImportConfirmRequest(BaseSchema):
    school_id: Optional[UUID] = None
    confirmed_lines: Optional[List[Dict[str, Any]]] = None
    confirmed_events: Optional[List[Dict[str, Any]]] = None
    funding_source_code: str = "BOS"
    notes: Optional[str] = None
