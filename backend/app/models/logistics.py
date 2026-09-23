from datetime import datetime
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, GUID


class LogisticsRecord(BaseModel):
    __tablename__ = "logistics_records"

    revision_id = Column(GUID, ForeignKey("package_revisions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    dispatch_date = Column(Date, nullable=True)
    receipt_date = Column(Date, nullable=True)
    delivery_reference = Column(String(128), nullable=True)  # Surat Jalan reference
    courier_name = Column(String(128), nullable=True)
    vehicle_plate = Column(String(32), nullable=True)
    inspection_status = Column(String(32), default="PENDING", nullable=False)  # PENDING, PASSED, FAILED
    inspection_notes = Column(Text, nullable=True)
    inspected_by = Column(String(128), nullable=True)
    inspected_at = Column(DateTime(timezone=True), nullable=True)

    revision = relationship("PackageRevision", back_populates="logistics_record")


class LogisticsEvidence(BaseModel):
    __tablename__ = "logistics_evidence"

    revision_id = Column(GUID, ForeignKey("package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(64), nullable=False)  # image/jpeg, image/png, application/pdf
    sha256_hash = Column(String(64), nullable=False)
    evidence_type = Column(String(64), default="DELIVERY_PHOTO", nullable=False)  # DELIVERY_PHOTO, RECEIPT, INSPECTION_NOTE
    description = Column(Text, nullable=True)
    uploaded_by = Column(String(100), default="LOGISTICS", nullable=False)

    revision = relationship("PackageRevision", back_populates="evidences")
