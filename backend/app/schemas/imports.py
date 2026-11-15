from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import Field
from app.schemas.common import BaseSchema


class ImportUploadResponse(BaseSchema):
    import_id: UUID
    filename: str
    file_hash: str
    file_size: int = 0
    status: str
    source_format: str = "XLSX"
    sheet_names: List[str] = []
    active_sheet: Optional[str] = None
    extraction_stats: Dict[str, Any] = Field(default_factory=dict)
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
    file_hash: Optional[str] = None
    status: str
    source_format: str = "XLSX"
    sheet_names: List[str] = []
    active_sheet: str = "HPS"
    raw_preview_rows: List[List[Any]] = []
    header_row_index: Optional[int] = None
    detected_mapping: Dict[str, int] = {}
    ai_proposal: Optional[Dict[str, Any]] = None
    ai_status: Optional[str] = None
    ai_error: Optional[str] = None
    upload_context: Dict[str, Any] = {}
    document_context: Dict[str, Any] = Field(default_factory=dict)
    extraction_stats: Dict[str, Any] = Field(default_factory=dict)
    progress: Optional[Dict[str, Any]] = None
    school_candidate: Dict[str, Any]
    transaction_metadata: Dict[str, Any]
    candidate_lines: List[Dict[str, Any]]
    events_candidate: List[Dict[str, Any]]
    detected_discrepancies: List[DiscrepancyItem]
    can_proceed_to_confirm: bool


class ImportReparseRequest(BaseSchema):
    sheet_name: Optional[str] = None
    header_row_index: Optional[int] = Field(None, ge=1)
    column_mapping: Dict[str, int] = Field(default_factory=dict)
    mapping_source: str = "AI_EDITED"  # AI, AI_EDITED, MANUAL_FALLBACK


class ImportConfirmRequest(BaseSchema):
    school_id: Optional[UUID] = None
    fiscal_year: Optional[int] = None
    quarter: Optional[int] = Field(None, ge=1, le=4)
    sheet_name: Optional[str] = None
    header_row_index: Optional[int] = Field(None, ge=1)
    column_mapping: Optional[Dict[str, int]] = None
    mapping_source: Optional[str] = None
    confirmed_lines: Optional[List[Dict[str, Any]]] = None
    confirmed_events: Optional[List[Dict[str, Any]]] = None
    funding_source_code: str = "BOS_REGULER"
    notes: Optional[str] = None
