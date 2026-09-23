from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from app.schemas.common import BaseSchema


class AuditEventResponse(BaseSchema):
    id: UUID
    entity_name: str
    entity_id: str
    action: str
    actor: str
    timestamp: datetime
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    reason: Optional[str] = None
