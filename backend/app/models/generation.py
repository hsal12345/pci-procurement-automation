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


class GenerationJob(BaseModel):
    __tablename__ = "generation_jobs"

    revision_id = Column(GUID, ForeignKey("package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), default="QUEUED", nullable=False, index=True)  # QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED
    progress_percent = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    revision = relationship("PackageRevision", back_populates="generation_jobs")
    artifacts = relationship("Artifact", back_populates="job", cascade="all, delete-orphan")


class Artifact(BaseModel):
    __tablename__ = "artifacts"

    job_id = Column(GUID, ForeignKey("generation_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    revision_id = Column(GUID, ForeignKey("package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_code = Column(String(32), nullable=True)  # D01..D13, ALL, ZIP
    format = Column(String(16), nullable=False)  # XLSX, DOCX, PDF, ZIP
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    sha256_hash = Column(String(64), nullable=False)
    is_draft = Column(Boolean, default=True, nullable=False)
    archive_status = Column(String(32), default="PENDING", nullable=False)  # PENDING, SYNCING, SYNCED, FAILED

    job = relationship("GenerationJob", back_populates="artifacts")
