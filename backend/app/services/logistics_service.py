import hashlib
import shutil
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.packages import PackageRevision, RevisionLine
from app.models.logistics import LogisticsRecord, LogisticsEvidence
from app.schemas.common import UserRoleEnum, RevisionStatusEnum
from app.schemas.logistics import LogisticsFactsUpdate
from app.services.audit_service import audit_service

ALLOWED_EVIDENCE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_EVIDENCE_MIMES = {"image/jpeg", "image/png", "application/pdf"}
MAX_EVIDENCE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

COMPLETION_HANDOVER_DOCS = ["D08", "D09", "D10", "D11", "D12", "D13"]


class LogisticsService:
    @staticmethod
    async def update_logistics_facts(
        db: AsyncSession,
        revision_id: UUID,
        payload: LogisticsFactsUpdate,
        actor_role: str,
        actor_name: str = "Petugas Logistik"
    ) -> LogisticsRecord:
        """Updates delivery dates, courier/vehicle reference, inspection notes,
        and individual line conditions (BAIK/RUSAK) and received quantities.
        Enforces dispute routing if goods are damaged or deliveries are partial.
        """
        allowed_roles = (
            UserRoleEnum.LOGISTICS.value,
            UserRoleEnum.ADMINISTRATION.value,
            UserRoleEnum.SYSTEM_ADMINISTRATOR.value
        )
        if actor_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hanya peran Bagian Logistik atau Administrasi yang berwenang memperbarui data logistik pengiriman."
            )

        # Get revision with lines
        res_rev = await db.execute(
            select(PackageRevision)
            .options(
                selectinload(PackageRevision.lines),
                selectinload(PackageRevision.logistics_record)
            )
            .where(PackageRevision.id == revision_id)
        )
        revision = res_rev.scalar_one_or_none()
        if not revision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Revisi paket dengan ID {revision_id} tidak ditemukan."
            )

        if revision.status in (RevisionStatusEnum.ISSUED.value, RevisionStatusEnum.CANCELLED.value, RevisionStatusEnum.SUPERSEDED.value):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Revisi ini telah berstatus '{revision.status}' dan data logistik tidak dapat dimodifikasi lagi."
            )

        # Retrieve or create LogisticsRecord
        logistics = revision.logistics_record
        is_new = False
        if not logistics:
            logistics = LogisticsRecord(revision_id=revision.id)
            db.add(logistics)
            is_new = True

        before_logistics = {
            "dispatch_date": logistics.dispatch_date.isoformat() if logistics.dispatch_date else None,
            "receipt_date": logistics.receipt_date.isoformat() if logistics.receipt_date else None,
            "delivery_reference": logistics.delivery_reference,
            "inspection_status": logistics.inspection_status
        } if not is_new else {}

        if "dispatch_date" in payload.model_fields_set:
            logistics.dispatch_date = payload.dispatch_date
        elif payload.dispatch_date is not None:
            logistics.dispatch_date = payload.dispatch_date

        if "receipt_date" in payload.model_fields_set or "actual_delivery_date" in payload.model_fields_set:
            logistics.receipt_date = payload.receipt_date
        elif payload.receipt_date is not None:
            logistics.receipt_date = payload.receipt_date

        if "delivery_reference" in payload.model_fields_set or payload.delivery_reference is not None:
            logistics.delivery_reference = payload.delivery_reference
        if "courier_name" in payload.model_fields_set or payload.courier_name is not None:
            logistics.courier_name = payload.courier_name
        if "vehicle_plate" in payload.model_fields_set or payload.vehicle_plate is not None:
            logistics.vehicle_plate = payload.vehicle_plate
        if payload.inspection_status is not None:
            logistics.inspection_status = payload.inspection_status.upper()
            logistics.inspected_by = actor_name
            logistics.inspected_at = datetime.utcnow()
        if "inspection_notes" in payload.model_fields_set or payload.inspection_notes is not None:
            logistics.inspection_notes = payload.inspection_notes

        # Process individual line updates if provided
        has_damaged_or_partial = False
        if payload.line_updates:
            lines_by_num = {l.line_number: l for l in revision.lines}
            for update in payload.line_updates:
                line = lines_by_num.get(update.line_number)
                if line:
                    if update.condition is not None:
                        cond = update.condition.upper()
                        line.condition = cond
                        if cond == "RUSAK":
                            has_damaged_or_partial = True

                    if update.received_quantity is not None:
                        line.received_quantity = update.received_quantity
                        if update.received_quantity < line.quantity:
                            has_damaged_or_partial = True

        # Check existing lines if any condition is RUSAK
        for l in revision.lines:
            if l.condition == "RUSAK" or (l.received_quantity is not None and l.received_quantity < l.quantity):
                has_damaged_or_partial = True

        # Dispute routing per PRD Section 1.2 & Section 8
        if has_damaged_or_partial:
            prev_status = revision.status
            revision.status = RevisionStatusEnum.OUTSIDE_PILOT_DISPUTE.value
            logistics.inspection_status = "FAILED"
            await audit_service.log_event(
                db=db,
                entity_name="PackageRevision",
                entity_id=str(revision.id),
                action="DISPUTE",
                actor=actor_name,
                before_state={"status": prev_status},
                after_state={"status": revision.status, "inspection_status": "FAILED"},
                reason="Pemeriksaan fisik mencatat barang rusak atau kurang kirim. Dialihkan ke OUTSIDE_PILOT_DISPUTE."
            )

        after_logistics = {
            "dispatch_date": logistics.dispatch_date.isoformat() if logistics.dispatch_date else None,
            "receipt_date": logistics.receipt_date.isoformat() if logistics.receipt_date else None,
            "delivery_reference": logistics.delivery_reference,
            "inspection_status": logistics.inspection_status
        }

        await audit_service.log_event(
            db=db,
            entity_name="LogisticsRecord",
            entity_id=str(revision.id),
            action="UPDATE_LOGISTICS",
            actor=actor_name,
            before_state=before_logistics,
            after_state=after_logistics,
            reason="Pembaruan fakta logistik pengiriman dan hasil pemeriksaan fisik"
        )

        await db.commit()
        await db.refresh(logistics)
        return logistics

    @staticmethod
    async def save_evidence_attachment(
        db: AsyncSession,
        revision_id: UUID,
        file: UploadFile,
        evidence_type: str = "DELIVERY_PHOTO",
        description: Optional[str] = None,
        actor_role: str = "LOGISTICS",
        actor_name: str = "Petugas Logistik"
    ) -> LogisticsEvidence:
        """Validates, hashes, stores, and records delivery or inspection photo/document evidence."""
        allowed_roles = (
            UserRoleEnum.LOGISTICS.value,
            UserRoleEnum.ADMINISTRATION.value,
            UserRoleEnum.SYSTEM_ADMINISTRATOR.value
        )
        if actor_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hanya peran Bagian Logistik atau Administrasi yang berwenang mengunggah berkas bukti logistik."
            )

        # Check revision exists
        res_rev = await db.execute(select(PackageRevision).where(PackageRevision.id == revision_id))
        revision = res_rev.scalar_one_or_none()
        if not revision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Revisi paket dengan ID {revision_id} tidak ditemukan."
            )

        filename = file.filename or "attachment"
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EVIDENCE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format berkas bukti '{suffix}' tidak didukung. Hanya JPEG (.jpg, .jpeg), PNG (.png), dan PDF (.pdf) yang diperbolehkan."
            )

        target_dir = settings.get_evidence_dir() / str(revision_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        unique_filename = f"{uuid4().hex[:12]}_{filename}"
        dest_path = target_dir / unique_filename

        hasher = hashlib.sha256()
        total_size = 0

        with open(dest_path, "wb") as buffer:
            while chunk := await file.read(65536):
                total_size += len(chunk)
                if total_size > MAX_EVIDENCE_SIZE_BYTES:
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Ukuran berkas bukti melebihi batas maksimum 10 MB."
                    )
                hasher.update(chunk)
                buffer.write(chunk)

        file_hash = hasher.hexdigest()
        mime_type = file.content_type or ("application/pdf" if suffix == ".pdf" else "image/jpeg")

        evidence = LogisticsEvidence(
            revision_id=revision.id,
            file_path=str(dest_path),
            original_filename=filename,
            file_size=total_size,
            mime_type=mime_type,
            sha256_hash=file_hash,
            evidence_type=evidence_type.upper(),
            description=description,
            uploaded_by=actor_name
        )
        db.add(evidence)

        await audit_service.log_event(
            db=db,
            entity_name="LogisticsEvidence",
            entity_id=str(evidence.id),
            action="UPLOAD_EVIDENCE",
            actor=actor_name,
            after_state={
                "filename": filename,
                "file_size": total_size,
                "sha256_hash": file_hash,
                "evidence_type": evidence_type
            },
            reason=description or "Unggah bukti foto/dokumen fisik pengiriman"
        )

        await db.commit()
        await db.refresh(evidence)
        return evidence

    @staticmethod
    async def list_evidence(db: AsyncSession, revision_id: UUID) -> List[LogisticsEvidence]:
        """Lists all uploaded evidence records for a revision."""
        result = await db.execute(
            select(LogisticsEvidence)
            .where(LogisticsEvidence.revision_id == revision_id)
            .order_by(LogisticsEvidence.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def enforce_br13_logistics_compliance(db: AsyncSession, revision_id: UUID):
        """Enforces BR13 Delivery & Payment Facts:
        Blocks completion and handover documents (D08-D13) from final issuance
        if delivery is unconfirmed, condition is RUSAK, or quantities are partial.
        """
        res_rev = await db.execute(
            select(PackageRevision)
            .options(
                selectinload(PackageRevision.lines),
                selectinload(PackageRevision.logistics_record)
            )
            .where(PackageRevision.id == revision_id)
        )
        revision = res_rev.scalar_one_or_none()
        if not revision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Revisi paket dengan ID {revision_id} tidak ditemukan."
            )

        logistics = revision.logistics_record

        # 1. Check physical receipt
        if not logistics or not logistics.receipt_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Pelanggaran Aturan Bisnis BR13: Tanggal penerimaan fisik barang belum tercatat. "
                    f"Penerbitan dokumen penyelesaian ({', '.join(COMPLETION_HANDOVER_DOCS)}) "
                    f"diblokir hingga pengiriman dikonfirmasi diterima di sekolah."
                )
            )

        # 2. Check damaged goods or partial received quantities
        for idx, line in enumerate(revision.lines, start=1):
            if line.condition == "RUSAK":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Pelanggaran Aturan Bisnis BR13: Barang pada baris {idx} ('{line.confirmed_description}') "
                        f"tercatat dalam kondisi RUSAK. Transaksi dialihkan ke penyelesaian sengketa di luar alur standar "
                        f"(OUTSIDE_PILOT_DISPUTE) hingga vendor melakukan penggantian fisik barang."
                    )
                )

            if line.received_quantity is not None and line.received_quantity < line.quantity:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Pelanggaran Aturan Bisnis BR13: Kuantitas fisik diterima pada baris {idx} "
                        f"({line.received_quantity} {line.unit}) kurang dari kuantitas pesanan ({line.quantity} {line.unit}). "
                        f"Penerbitan dokumen penyelesaian ({', '.join(COMPLETION_HANDOVER_DOCS)}) diblokir hingga barang lengkap."
                    )
                )


logistics_service = LogisticsService()
