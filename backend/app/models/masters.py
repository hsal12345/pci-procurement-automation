from datetime import date, datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
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


class Company(BaseModel):
    __tablename__ = "companies"

    legal_name = Column(String(255), nullable=False)
    npwp = Column(String(32), nullable=True)
    address = Column(Text, nullable=False)
    subdistrict = Column(String(100), nullable=True)
    city = Column(String(100), nullable=False, default="Jakarta")
    postal_code = Column(String(16), nullable=True)
    email = Column(String(128), nullable=True)
    phone = Column(String(32), nullable=True)
    bank_name = Column(String(100), nullable=True)
    bank_account_number = Column(String(64), nullable=True)
    bank_account_holder = Column(String(255), nullable=True)
    director_name = Column(String(255), nullable=False)
    director_title = Column(String(100), nullable=False, default="Direktur")
    logo_path = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class School(BaseModel):
    __tablename__ = "schools"

    name = Column(String(255), nullable=False, index=True)
    npsn = Column(String(16), nullable=True, unique=True, index=True)
    level = Column(String(16), nullable=False, default="SD")
    address = Column(Text, nullable=False)
    subdistrict = Column(String(100), nullable=True)
    postal_code = Column(String(16), nullable=True)
    email = Column(String(128), nullable=True)
    phone = Column(String(32), nullable=True)
    letterhead_path = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    appointments = relationship("OfficialAppointment", back_populates="school", cascade="all, delete-orphan")
    packages = relationship("Package", back_populates="school")


class OfficialAppointment(BaseModel):
    __tablename__ = "official_appointments"

    school_id = Column(GUID, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    person_name = Column(String(255), nullable=False)
    nip = Column(String(32), nullable=True)  # Stored as text to preserve leading zeros
    role = Column(String(64), nullable=False)  # KEPALA_SEKOLAH, BENDAHARA, PENGURUS_BARANG, TIM_BOS
    valid_from = Column(Date, nullable=False, default=date(2020, 1, 1))
    valid_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    school = relationship("School", back_populates="appointments")


class Item(BaseModel):
    __tablename__ = "items"

    sku = Column(String(64), unique=True, index=True, nullable=True)
    canonical_description = Column(String(255), nullable=False, index=True)
    default_spec = Column(Text, nullable=True)
    brand = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    default_unit = Column(String(32), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class Unit(BaseModel):
    __tablename__ = "units"

    code = Column(String(32), unique=True, index=True, nullable=False)
    display_label = Column(String(64), nullable=False)
    allowed_fractional = Column(Boolean, default=False, nullable=False)


class BudgetClassification(BaseModel):
    __tablename__ = "budget_classifications"

    fiscal_year = Column(Integer, nullable=False, index=True)
    activity_code = Column(String(64), nullable=True)
    activity_name = Column(String(255), nullable=False)
    sub_activity = Column(String(255), nullable=True)
    account_code = Column(String(64), nullable=True)
    account_name = Column(String(255), nullable=False)
    funding_source_code = Column(String(32), nullable=True)


class FundingSource(BaseModel):
    __tablename__ = "funding_sources"

    code = Column(String(32), unique=True, index=True, nullable=False)  # BOS, BOP
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class TaxPolicyVersion(BaseModel):
    __tablename__ = "tax_policy_versions"

    policy_id = Column(String(64), index=True, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    tax_type = Column(String(32), nullable=False)  # PPN, PPH22, PPH23
    rate = Column(Numeric(12, 8), nullable=False)  # e.g. 0.11000000 for 11%, 0.01500000 for 1.5%
    is_inclusive = Column(Boolean, default=False, nullable=False)
    withholding_rule = Column(String(64), default="NONE", nullable=False)  # NONE, WITHHOLD_FROM_PAYABLE
    rounding_rule = Column(String(32), default="ROUND_HALF_UP", nullable=False)
    effective_from = Column(Date, nullable=False, default=date(2020, 1, 1))
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("policy_id", "version", "tax_type", name="uq_policy_ver_type"),
    )


class PackageProfile(BaseModel):
    __tablename__ = "package_profiles"

    code = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    required_doc_codes = Column(JSON, nullable=False)  # e.g. ["D01", "D02", ..., "D13"]


class NumberingPolicy(BaseModel):
    __tablename__ = "numbering_policies"

    doc_code = Column(String(32), nullable=False, index=True)  # D01..D13
    issuer = Column(String(32), nullable=False)  # COMPANY or SCHOOL
    pattern = Column(String(128), nullable=False)  # e.g. "{seq}/DO/PCI/{year}"
    reset_period = Column(String(32), default="YEARLY", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class NumberCounter(BaseModel):
    """Concurrency-safe transactional sequence counter table.
    Enables SELECT ... FOR UPDATE atomic counter incrementing.
    """
    __tablename__ = "number_counters"

    scope_key = Column(String(64), unique=True, index=True, nullable=False)  # e.g. "COMPANY:FAKTUR:2026"
    counter_val = Column(Integer, default=0, nullable=False)
