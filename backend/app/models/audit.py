from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    JSON,
)
from app.models.base import BaseModel, TZDateTime


class AuditEvent(BaseModel):
    __tablename__ = "audit_events"

    entity_name = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False, index=True)
    action = Column(String(32), nullable=False, index=True)  # CREATE, UPDATE, DELETE, SUBMIT, APPROVE, RETURN, IMPORT, GENERATE
    actor = Column(String(100), nullable=False, default="system")
    timestamp = Column(TZDateTime, default=datetime.utcnow, nullable=False)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    reason = Column(Text, nullable=True)

