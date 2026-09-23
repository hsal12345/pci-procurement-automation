from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, GUID


class ArchiveRecord(BaseModel):
    __tablename__ = "archive_records"

    package_id = Column(GUID, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_id = Column(GUID, ForeignKey("package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_provider = Column(String(32), default="GOOGLE_DRIVE", nullable=False)
    folder_path = Column(String(512), nullable=False)  # Year / Quarter / SD / School / Package ID / Revision
    drive_folder_id = Column(String(128), nullable=True)
    status = Column(String(32), default="PENDING", nullable=False, index=True)  # PENDING, SYNCING, SYNCED, FAILED
    attempt_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)

    package = relationship("Package", back_populates="archives")
    revision = relationship("PackageRevision", back_populates="archives")
