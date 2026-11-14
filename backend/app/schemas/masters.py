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
    director_sk_number: Optional[str] = None
    logo_path: Optional[str] = None
    is_active: bool = True


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseSchema):
    legal_name: Optional[str] = None
    npwp: Optional[str] = None
    address: Optional[str] = None
    subdistrict: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_holder: Optional[str] = None
    director_name: Optional[str] = None
    director_title: Optional[str] = None
    director_sk_number: Optional[str] = None
    logo_path: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyOfficialBase(BaseSchema):
    company_id: UUID
    person_name: str
    role: str = "DIREKTUR"
    role_title: str = "Direktur"
    nip: Optional[str] = None
    position_sk_number: Optional[str] = None
    is_active: bool = True


class CompanyOfficialCreate(BaseSchema):
    person_name: str
    role: str = "DIREKTUR"
    role_title: str = "Direktur"
    nip: Optional[str] = None
    position_sk_number: Optional[str] = None
    is_active: bool = True


class CompanyOfficialResponse(CompanyOfficialBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class CompanyResponse(CompanyBase):
    id: UUID
    officials: Optional[List[CompanyOfficialResponse]] = []
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


class SchoolUpdate(BaseSchema):
    name: Optional[str] = None
    npsn: Optional[str] = None
    level: Optional[str] = None
    address: Optional[str] = None
    subdistrict: Optional[str] = None
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    letterhead_path: Optional[str] = None
    is_active: Optional[bool] = None


class SchoolResponse(SchoolBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class OfficialAppointmentBase(BaseSchema):
    school_id: UUID
    person_name: str
    nip: Optional[str] = None  # Stored as text, preserves leading zero
    role: str  # KEPALA_SEKOLAH, BENDAHARA, PENGURUS_BARANG, TIM_BOS
    position_sk_number: Optional[str] = None  # SK Penugasan e.g. 800/014/SK/2025
    valid_from: date
    valid_to: Optional[date] = None
    is_active: bool = True


class OfficialAppointmentCreate(BaseSchema):
    person_name: str
    nip: Optional[str] = None
    role: str
    position_sk_number: Optional[str] = None
    valid_from: date = date(2026, 1, 1)
    valid_to: Optional[date] = None
    is_active: bool = True


class OfficialAppointmentUpdate(BaseSchema):
    person_name: Optional[str] = None
    nip: Optional[str] = None
    role: Optional[str] = None
    position_sk_number: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    is_active: Optional[bool] = None


class OfficialAppointmentResponse(OfficialAppointmentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ItemBase(BaseSchema):
    sku: Optional[str] = None
    kbli: Optional[str] = None
    canonical_description: str
    default_spec: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    default_unit: Optional[str] = None
    reference_price: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    is_active: bool = True


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseSchema):
    sku: Optional[str] = None
    kbli: Optional[str] = None
    canonical_description: Optional[str] = None
    default_spec: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    default_unit: Optional[str] = None
    reference_price: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    is_active: Optional[bool] = None


class ItemPriceUpdate(BaseSchema):
    reference_price: Decimal = Field(ge=Decimal("0"))


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


class UnitUpdate(BaseSchema):
    code: Optional[str] = None
    display_label: Optional[str] = None
    allowed_fractional: Optional[bool] = None


class UnitResponse(UnitBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class BudgetClassificationBase(BaseSchema):
    fiscal_year: int = 2026
    activity_code: Optional[str] = None
    activity_name: str
    sub_activity: Optional[str] = None
    account_code: Optional[str] = None
    account_name: str
    funding_source_code: Optional[str] = "BOS"
    funding_scheme: str = "BOS_REGULER"
    is_active: bool = True


class BudgetClassificationCreate(BudgetClassificationBase):
    pass


class BudgetClassificationUpdate(BaseSchema):
    fiscal_year: Optional[int] = None
    activity_code: Optional[str] = None
    activity_name: Optional[str] = None
    sub_activity: Optional[str] = None
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    funding_source_code: Optional[str] = None
    funding_scheme: Optional[str] = None
    is_active: Optional[bool] = None


class BudgetClassificationResponse(BudgetClassificationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class FundingSourceBase(BaseSchema):
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True


class FundingSourceCreate(FundingSourceBase):
    pass


class FundingSourceUpdate(BaseSchema):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FundingSourceResponse(FundingSourceBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class PackageProfileResponse(BaseSchema):
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    required_doc_codes: List[str] = []
    created_at: datetime
    updated_at: datetime


class PackageProfileUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    required_doc_codes: Optional[List[str]] = None


class TemplateRegistryResponse(BaseSchema):
    id: UUID
    doc_code: str
    doc_name: str
    funding_scheme: str = "ALL"
    is_mandatory: bool = True
    version: int = 1
    filename: str
    file_path: Optional[str] = None
    sha256_hash: Optional[str] = None
    required_tokens: List[str] = []
    detected_tokens: List[str] = []
    is_active: bool = True
    uploaded_by: str = "SYSTEM"
    created_at: datetime
    updated_at: datetime


class TemplateConfigUpdate(BaseSchema):
    doc_name: Optional[str] = None
    funding_scheme: Optional[str] = None
    is_mandatory: Optional[bool] = None
    is_active: Optional[bool] = None


class TemplateValidationResult(BaseSchema):
    doc_code: str
    filename: str
    is_valid: bool
    detected_tokens: List[str] = []
    missing_required_tokens: List[str] = []
    unrecognized_tokens: List[str] = []
    syntax_errors: List[str] = []
    message: str


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
