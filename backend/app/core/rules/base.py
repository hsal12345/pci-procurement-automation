from dataclasses import dataclass
from typing import Optional, Any
from app.schemas.common import SeverityEnum


@dataclass
class RuleFinding:
    rule_code: str  # BR01..BR15
    severity: SeverityEnum  # BLOCK, WARNING, INFO
    message: str
    doc_code: Optional[str] = None
    sheet_name: Optional[str] = None
    cell_range: Optional[str] = None
    field_name: Optional[str] = None
    original_value: Optional[str] = None
    proposed_value: Optional[str] = None
