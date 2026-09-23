from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, GUID


class ValidationRun(BaseModel):
    __tablename__ = "validation_runs"

    revision_id = Column(GUID, ForeignKey("package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_by = Column(String(100), nullable=True)
    run_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    passed = Column(Boolean, default=False, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    warning_count = Column(Integer, default=0, nullable=False)
    info_count = Column(Integer, default=0, nullable=False)

    revision = relationship("PackageRevision", back_populates="validation_runs")
    findings = relationship("Finding", back_populates="run", cascade="all, delete-orphan")


class Finding(BaseModel):
    __tablename__ = "findings"

    run_id = Column(GUID, ForeignKey("validation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_code = Column(String(16), nullable=False, index=True)  # BR01..BR15
    severity = Column(String(16), nullable=False)  # BLOCK, WARNING, INFO
    doc_code = Column(String(32), nullable=True)  # D01..D13
    sheet_name = Column(String(64), nullable=True)
    cell_range = Column(String(32), nullable=True)
    field_name = Column(String(100), nullable=True)
    original_value = Column(Text, nullable=True)
    proposed_value = Column(Text, nullable=True)
    message = Column(Text, nullable=False)
    disposition = Column(String(32), default="PENDING", nullable=False)  # PENDING, ACKNOWLEDGED, OVERRIDDEN, RESOLVED
    disposition_reason = Column(Text, nullable=True)
    disposition_actor = Column(String(100), nullable=True)

    run = relationship("ValidationRun", back_populates="findings")
