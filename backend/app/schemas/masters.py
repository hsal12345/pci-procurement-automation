from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import Field
from app.schemas.common import BaseSchema


class CompanyBase(BaseSchema):
    legal_name: str
    npwp: Optional[str] = None
    address: str
    subdistrict: Optional[str] = None
    city: str = "Jakarta"
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_holder: Optional[str] = None
    director_name: str
    director_title: str = "Direktur"
    logo_path: Optional[str] = None
    is_active: bool = True


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class SchoolBase(BaseSchema):
    name: str
    npsn: Optional[str] = None  # Stored as text, preserves leading zero
    level: str = "SD"
    address: str
    subdistrict: Optional[str] = None
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    letterhead_path: Optional[str] = None
    is_active: bool = True


class SchoolCreate(SchoolBase):
    pass


class SchoolResponse(SchoolBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class OfficialAppointmentBase(BaseSchema):
    school_id: UUID
    person_name: str
    nip: Optional[str] = None  # Stored as text, preserves leading zero
    role: str  # KEPALA_SEKOLAH, BENDAHARA, PENGURUS_BARANG, TIM_BOS
    valid_from: date
    valid_to: Optional[date] = None
    is_active: bool = True


class OfficialAppointmentCreate(OfficialAppointmentBase):
    pass


class OfficialAppointmentResponse(OfficialAppointmentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ItemBase(BaseSchema):
    sku: Optional[str] = None
    canonical_description: str
    default_spec: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    default_unit: Optional[str] = None
    is_active: bool = True


class ItemCreate(ItemBase):
    pass


class ItemResponse(ItemBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class UnitBase(BaseSchema):
    code: str
    display_label: str
    allowed_fractional: bool = False


class UnitCreate(UnitBase):
    pass


class UnitResponse(UnitBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class TaxPolicyVersionBase(BaseSchema):
    policy_id: str
    version: int = 1
    tax_type: str  # PPN, PPH22, PPH23
    rate: Decimal  # e.g. 0.11000000
    is_inclusive: bool = False
    withholding_rule: str = "NONE"  # NONE, WITHHOLD_FROM_PAYABLE
    rounding_rule: str = "ROUND_HALF_UP"
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool = True


class TaxPolicyVersionCreate(TaxPolicyVersionBase):
    pass


class TaxPolicyVersionResponse(TaxPolicyVersionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class NumberCounterResponse(BaseSchema):
    id: UUID
    scope_key: str
    counter_val: int
    updated_at: datetime
