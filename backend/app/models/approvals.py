from datetime import datetime
from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, GUID, TZDateTime


class Approval(BaseModel):
    __tablename__ = "approvals"

    revision_id = Column(GUID, ForeignKey("package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    approver_name = Column(String(255), nullable=False)
    approver_role = Column(String(64), default="FINANCE_DIRECTOR", nullable=False)
    decision = Column(String(32), nullable=False)  # APPROVED, RETURNED
    decision_reason = Column(Text, nullable=True)
    reviewed_manifest_hash = Column(String(64), nullable=True)
    signed_at = Column(TZDateTime, default=datetime.utcnow, nullable=False)

    revision = relationship("PackageRevision", back_populates="approvals")

