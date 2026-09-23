from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import Field
from app.schemas.common import BaseSchema, PackageStatusEnum


class RevisionLineBase(BaseSchema):
    line_number: int
    item_id: Optional[UUID] = None
    original_description: str
    confirmed_description: str
    specification: Optional[str] = None
    quantity: Decimal = Field(default=Decimal("1"), ge=Decimal("0.0001"))
    received_quantity: Optional[Decimal] = None
    unit: str

    # Three distinct unit price stages
    hps_unit_price: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    offer_unit_price: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    final_unit_price: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))

    discount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    line_total: Decimal = Field(default=Decimal("0"))
    condition: str = "BAIK"
    notes: Optional[str] = None


class RevisionLineCreate(RevisionLineBase):
    pass


class RevisionLineResponse(RevisionLineBase):
    id: UUID
    revision_id: UUID
    created_at: datetime
    updated_at: datetime


class DocumentEventBase(BaseSchema):
    event_code: str
    event_date: date
    day_name_id: Optional[str] = None
    location: str = "Jakarta"
    notes: Optional[str] = None


class DocumentEventCreate(DocumentEventBase):
    pass


class DocumentEventResponse(DocumentEventBase):
    id: UUID
    revision_id: UUID
    created_at: datetime
    updated_at: datetime


class DocumentNumberBase(BaseSchema):
    doc_code: str
    doc_number: str
    issuer: str
    counter_val: Optional[int] = None
    issue_date: Optional[date] = None
    is_reserved: bool = True


class DocumentNumberCreate(DocumentNumberBase):
    pass


class DocumentNumberResponse(DocumentNumberBase):
    id: UUID
    revision_id: UUID
    created_at: datetime
    updated_at: datetime


class PackageRevisionResponse(BaseSchema):
    id: UUID
    package_id: UUID
    revision_number: int
    version: int
    status: str = "DRAFT"
    school_snapshot: Optional[Dict[str, Any]] = None
    company_snapshot: Optional[Dict[str, Any]] = None
    tax_policy_snapshot: Optional[List[Dict[str, Any]]] = []
    officials_snapshot: Optional[List[Dict[str, Any]]] = []
    subtotal: Decimal
    tax_total: Decimal
    grand_total: Decimal
    terbilang_grand_total: Optional[str] = None
    is_locked: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    lines: List[RevisionLineResponse] = []
    events: List[DocumentEventResponse] = []
    numbers: List[DocumentNumberResponse] = []


class PackageCreate(BaseSchema):
    school_id: UUID
    fiscal_year: int
    quarter: int = Field(ge=1, le=4)
    funding_source_id: Optional[UUID] = None
    budget_id: Optional[UUID] = None
    package_number: Optional[str] = None


class PackageResponse(BaseSchema):
    id: UUID
    package_number: str
    package_code: Optional[str] = None
    school_id: UUID
    fiscal_year: int
    quarter: int
    funding_source_id: Optional[UUID] = None
    budget_id: Optional[UUID] = None
    fund_source: Optional[str] = "BOS_REGULER"
    current_revision_id: Optional[UUID] = None
    status: PackageStatusEnum
    created_at: datetime
    updated_at: datetime

    revisions: List[PackageRevisionResponse] = []
    current_revision: Optional[PackageRevisionResponse] = None


class PackageRevisionUpdate(BaseSchema):
    expected_version: int  # Concurrency lock check
    lines: Optional[List[RevisionLineCreate]] = None
    events: Optional[List[DocumentEventCreate]] = None
    numbers: Optional[List[DocumentNumberCreate]] = None
    school_snapshot: Optional[Dict[str, Any]] = None
    company_snapshot: Optional[Dict[str, Any]] = None
    tax_policy_snapshot: Optional[List[Dict[str, Any]]] = None
    officials_snapshot: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


class TaxBreakdownItem(BaseSchema):
    tax_type: str
    amount: float
    rate: float


class RevisionCalculateRequest(BaseSchema):
    lines: List[RevisionLineCreate]


class RevisionCalculateResponse(BaseSchema):
    subtotal: float
    tax_total: float
    grand_total: float
    terbilang: str
    tax_breakdown: List[TaxBreakdownItem] = []

