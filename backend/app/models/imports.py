from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    JSON,
)
from app.models.base import BaseModel, TZDateTime


class ImportRecord(BaseModel):
    __tablename__ = "imports"

    original_filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    file_size = Column(Integer, nullable=False, default=0)
    uploaded_at = Column(TZDateTime, default=datetime.utcnow, nullable=False)
    uploader = Column(String(100), nullable=False, default="admin")
    status = Column(String(32), default="PARSED", nullable=False)  # UPLOADED, PARSED, CONFIRMED, FAILED
    candidate_payload = Column(JSON, nullable=True)
    sheet_metadata = Column(JSON, nullable=True)
    detected_discrepancies = Column(JSON, nullable=True)

