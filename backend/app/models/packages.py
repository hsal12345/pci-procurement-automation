from datetime import date
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, GUID


class Package(BaseModel):
    __tablename__ = "packages"

    package_number = Column(String(64), unique=True, index=True, nullable=False)
    school_id = Column(GUID, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False)
    fiscal_year = Column(Integer, nullable=False, index=True)
    quarter = Column(Integer, nullable=False)  # 1..4
    funding_source_id = Column(GUID, ForeignKey("funding_sources.id", ondelete="SET NULL"), nullable=True)
    budget_id = Column(GUID, ForeignKey("budget_classifications.id", ondelete="SET NULL"), nullable=True)
    current_revision_id = Column(GUID, nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)
    # Commercial status: ACTIVE, ISSUED, CANCELLED

    school = relationship("School", back_populates="packages")
    revisions = relationship("PackageRevision", back_populates="package", cascade="all, delete-orphan", foreign_keys="PackageRevision.package_id")
    archives = relationship("ArchiveRecord", back_populates="package", cascade="all, delete-orphan")


class PackageRevision(BaseModel):
    __tablename__ = "package_revisions"

    package_id = Column(GUID, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number = Column(Integer, nullable=False, default=1)
    version = Column(Integer, nullable=False, default=1)  # Optimistic concurrency version lock
    status = Column(String(32), default="DRAFT", nullable=False, index=True)
    # Lifecycle: DRAFT, UNDER_REVIEW, RETURNED, APPROVED, ISSUED, SUPERSEDED, OUTSIDE_PILOT_DISPUTE, CANCELLED
    ai_review_status = Column(String(32), default="NOT_RUN", nullable=False, index=True)
    # AI Review Status: NOT_RUN, COMPLETED, MANUAL_REVIEW_RECORDED, FAILED, SKIPPED

    # Immutable master snapshots
    school_snapshot = Column(JSON, nullable=False, default=dict)
    company_snapshot = Column(JSON, nullable=False, default=dict)
    tax_policy_snapshot = Column(JSON, nullable=False, default=list)
    officials_snapshot = Column(JSON, nullable=False, default=list)

    # Financial totals recomputed deterministically
    subtotal = Column(Numeric(20, 4), nullable=False, default=0)
    tax_total = Column(Numeric(20, 4), nullable=False, default=0)
    grand_total = Column(Numeric(20, 4), nullable=False, default=0)
    terbilang_grand_total = Column(Text, nullable=True)

    is_locked = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    package = relationship("Package", back_populates="revisions", foreign_keys=[package_id])
    lines = relationship("RevisionLine", back_populates="revision", cascade="all, delete-orphan", order_by="RevisionLine.line_number")
    events = relationship("DocumentEvent", back_populates="revision", cascade="all, delete-orphan")
    numbers = relationship("DocumentNumber", back_populates="revision", cascade="all, delete-orphan")
    validation_runs = relationship("ValidationRun", back_populates="revision", cascade="all, delete-orphan")
    generation_jobs = relationship("GenerationJob", back_populates="revision", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="revision", cascade="all, delete-orphan")
    logistics_record = relationship("LogisticsRecord", back_populates="revision", uselist=False, cascade="all, delete-orphan")
    evidences = relationship("LogisticsEvidence", back_populates="revision", cascade="all, delete-orphan")
    archives = relationship("ArchiveRecord", back_populates="revision", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("package_id", "revision_number", name="uq_package_revision"),
    )


class RevisionLine(BaseModel):
    __tablename__ = "revision_lines"

    revision_id = Column(GUID, ForeignKey("package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    item_id = Column(GUID, ForeignKey("items.id", ondelete="SET NULL"), nullable=True)
    original_description = Column(Text, nullable=False)
    confirmed_description = Column(Text, nullable=False)
    specification = Column(Text, nullable=True)
    quantity = Column(Numeric(18, 4), nullable=False, default=1)
    received_quantity = Column(Numeric(18, 4), nullable=True)
    unit = Column(String(32), nullable=False)

    # Three distinct unit price stages
    hps_unit_price = Column(Numeric(20, 4), nullable=False, default=0)    # D01
    offer_unit_price = Column(Numeric(20, 4), nullable=False, default=0)  # D03
    final_unit_price = Column(Numeric(20, 4), nullable=False, default=0)  # D04-D06, D10-D13

    discount = Column(Numeric(20, 4), nullable=False, default=0)
    line_total = Column(Numeric(20, 4), nullable=False, default=0)  # quantity * final_unit_price - discount
    condition = Column(String(32), default="BAIK", nullable=False)  # BAIK, RUSAK
    notes = Column(Text, nullable=True)

    revision = relationship("PackageRevision", back_populates="lines")

    __table_args__ = (
        UniqueConstraint("revision_id", "line_number", name="uq_revision_line_num"),
    )


class DocumentEvent(BaseModel):
    __tablename__ = "document_events"

    revision_id = Column(GUID, ForeignKey("package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_code = Column(String(32), nullable=False)  # HPS, SPP, PENAWARAN, NEGOSIASI, PESANAN, SURAT_JALAN, BAPB, BAST, BAST_REKANAN, BAPP, FAKTUR, KWITANSI
    event_date = Column(Date, nullable=False)
    day_name_id = Column(String(32), nullable=True)  # e.g. "Selasa", "Rabu"
    location = Column(String(100), default="Jakarta", nullable=False)
    notes = Column(Text, nullable=True)

    revision = relationship("PackageRevision", back_populates="events")

    __table_args__ = (
        UniqueConstraint("revision_id", "event_code", name="uq_revision_event_code"),
    )


class DocumentNumber(BaseModel):
    __tablename__ = "document_numbers"

    revision_id = Column(GUID, ForeignKey("package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_code = Column(String(32), nullable=False)  # D01..D13
    doc_number = Column(String(128), nullable=False)
    issuer = Column(String(32), nullable=False)  # COMPANY, SCHOOL
    counter_val = Column(Integer, nullable=True)
    issue_date = Column(Date, nullable=True)
    is_reserved = Column(Boolean, default=True, nullable=False)

    revision = relationship("PackageRevision", back_populates="numbers")

    __table_args__ = (
        UniqueConstraint("revision_id", "doc_code", name="uq_revision_doc_number"),
    )
