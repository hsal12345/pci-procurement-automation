from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import Field, field_validator, model_validator
from app.schemas.common import BaseSchema


class LogisticsLineUpdate(BaseSchema):
    line_number: int
    condition: Optional[str] = Field(None, description="Kondisi barang: BAIK atau RUSAK")
    received_quantity: Optional[Decimal] = Field(None, ge=Decimal("0"), description="Jumlah fisik yang diterima")


class LogisticsFactsUpdate(BaseSchema):
    dispatch_date: Optional[date] = Field(None, description="Tanggal pengiriman dari vendor (Surat Jalan)")
    receipt_date: Optional[date] = Field(None, description="Tanggal penerimaan fisik di sekolah")
    actual_delivery_date: Optional[date] = Field(None, description="Alias untuk receipt_date")
    delivery_reference: Optional[str] = Field(None, description="Nomor referensi Surat Jalan vendor")
    courier_name: Optional[str] = Field(None, description="Nama pengemudi / kurir pengantar")
    vehicle_plate: Optional[str] = Field(None, description="Nomor polisi kendaraan pengantar")
    inspection_status: Optional[str] = Field(None, description="Status pemeriksaan: PENDING, PASSED, FAILED")
    inspection_notes: Optional[str] = Field(None, description="Catatan hasil pemeriksaan fisik")
    line_updates: Optional[List[LogisticsLineUpdate]] = None

    @field_validator("dispatch_date", "receipt_date", "actual_delivery_date", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v

    @model_validator(mode="after")
    def sync_dates(self):
        if self.receipt_date is None and self.actual_delivery_date is not None:
            self.receipt_date = self.actual_delivery_date
        elif self.actual_delivery_date is None and self.receipt_date is not None:
            self.actual_delivery_date = self.receipt_date
        return self


class LogisticsEvidenceResponse(BaseSchema):
    id: UUID
    revision_id: UUID
    original_filename: str
    file_size: int
    mime_type: str
    sha256_hash: str
    evidence_type: str
    description: Optional[str] = None
    uploaded_by: str
    created_at: datetime


class LogisticsRecordResponse(BaseSchema):
    id: UUID
    revision_id: UUID
    dispatch_date: Optional[date] = None
    receipt_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    delivery_reference: Optional[str] = None
    courier_name: Optional[str] = None
    vehicle_plate: Optional[str] = None
    inspection_status: str = "PENDING"
    inspection_notes: Optional[str] = None
    inspected_by: Optional[str] = None
    inspected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    attachments: List[LogisticsEvidenceResponse] = []
    delivery_status: Optional[str] = "DELIVERED"
    is_delivery_confirmed: Optional[bool] = True

    @model_validator(mode="after")
    def sync_dates(self):
        if self.receipt_date is None and self.actual_delivery_date is not None:
            self.receipt_date = self.actual_delivery_date
        elif self.actual_delivery_date is None and self.receipt_date is not None:
            self.actual_delivery_date = self.receipt_date
        return self

