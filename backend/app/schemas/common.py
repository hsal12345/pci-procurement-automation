from enum import Enum
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SeverityEnum(str, Enum):
    BLOCK = "BLOCK"
    WARNING = "WARNING"
    INFO = "INFO"


class DispositionEnum(str, Enum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    OVERRIDDEN = "OVERRIDDEN"
    RESOLVED = "RESOLVED"


class PackageCommercialStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    ISSUED = "ISSUED"
    CANCELLED = "CANCELLED"


class RevisionStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    RETURNED = "RETURNED"
    APPROVED = "APPROVED"
    ISSUED = "ISSUED"
    SUPERSEDED = "SUPERSEDED"
    OUTSIDE_PILOT_DISPUTE = "OUTSIDE_PILOT_DISPUTE"
    CANCELLED = "CANCELLED"


class PackageStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    RETURNED = "RETURNED"
    APPROVED = "APPROVED"
    ISSUED = "ISSUED"
    SUPERSEDED = "SUPERSEDED"
    CANCELLED = "CANCELLED"
    ACTIVE = "ACTIVE"


class UserRoleEnum(str, Enum):
    ADMINISTRATION = "ADMINISTRATION"
    LOGISTICS = "LOGISTICS"
    FINANCE_DIRECTOR = "FINANCE_DIRECTOR"
    SYSTEM_ADMINISTRATOR = "SYSTEM_ADMINISTRATOR"


class DocumentRoleEnum(str, Enum):
    KEPALA_SEKOLAH = "KEPALA_SEKOLAH"
    BENDAHARA = "BENDAHARA"
    PENGURUS_BARANG = "PENGURUS_BARANG"
    TIM_BOS = "TIM_BOS"
    DIREKTUR = "DIREKTUR"
