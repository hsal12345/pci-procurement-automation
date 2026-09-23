from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.packages import Package, PackageRevision
from app.models.archive import ArchiveRecord
from app.services.audit_service import audit_service


class ArchiveService:
    @staticmethod
    async def register_archive_request(
        db: AsyncSession,
        revision_id: UUID
    ) -> ArchiveRecord:
        """Registers or resets an archive synchronization request for an issued package revision.
        Constructs standardized folder path: Year / Quarter / SD / School / Package ID / Revision.
        """
        res_rev = await db.execute(
            select(PackageRevision)
            .options(selectinload(PackageRevision.package))
            .where(PackageRevision.id == revision_id)
        )
        revision = res_rev.scalar_one_or_none()
        if not revision or not revision.package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Revisi paket dengan ID {revision_id} tidak ditemukan."
            )

        pkg = revision.package
        school_name = (revision.school_snapshot or {}).get("name", "SDN")
        folder_path = (
            f"{pkg.fiscal_year}/Q{pkg.quarter}/SD/{school_name}/"
            f"{pkg.package_number.replace('/', '_')}/Rev-{revision.revision_number}"
        )

        # Check existing record
        res_arch = await db.execute(
            select(ArchiveRecord).where(ArchiveRecord.revision_id == revision.id)
        )
        archive = res_arch.scalar_one_or_none()
        if not archive:
            archive = ArchiveRecord(
                package_id=pkg.id,
                revision_id=revision.id,
                target_provider="GOOGLE_DRIVE",
                folder_path=folder_path,
                status="PENDING",
                attempt_count=0
            )
            db.add(archive)
        else:
            archive.folder_path = folder_path
            archive.status = "PENDING"
            archive.last_error = None

        await audit_service.log_event(
            db=db,
            entity_name="ArchiveRecord",
            entity_id=str(revision.id),
            action="ARCHIVE_TRIGGER",
            actor="System",
            after_state={"folder_path": folder_path, "status": "PENDING"},
            reason="Registrasi sinkronisasi arsip ke Google Drive / n8n"
        )

        await db.commit()
        await db.refresh(archive)
        return archive

    @staticmethod
    async def get_pending_archives(db: AsyncSession) -> List[ArchiveRecord]:
        """Retrieves pending or failed archive requests eligible for upload."""
        res = await db.execute(
            select(ArchiveRecord)
            .where(ArchiveRecord.status.in_(["PENDING", "FAILED"]))
            .order_by(ArchiveRecord.created_at.asc())
        )
        return res.scalars().all()

    @staticmethod
    async def process_callback(
        db: AsyncSession,
        archive_id: UUID,
        status_val: str,
        drive_folder_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> ArchiveRecord:
        """Processes n8n or background sync callback reporting upload success or error.
        Guarantees that archive failures NEVER mutate or revoke the legal business ISSUED status.
        """
        res = await db.execute(select(ArchiveRecord).where(ArchiveRecord.id == archive_id))
        archive = res.scalar_one_or_none()
        if not archive:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data permintaan arsip dengan ID {archive_id} tidak ditemukan."
            )

        archive.attempt_count += 1
        archive.last_attempt_at = datetime.utcnow()

        if status_val.upper() == "SYNCED":
            archive.status = "SYNCED"
            archive.drive_folder_id = drive_folder_id
            archive.synced_at = datetime.utcnow()
            archive.last_error = None
        else:
            archive.status = "FAILED"
            archive.last_error = error_message or "Gagal mengunggah berkas ke Google Drive."

        await audit_service.log_event(
            db=db,
            entity_name="ArchiveRecord",
            entity_id=str(archive.id),
            action=f"ARCHIVE_{archive.status}",
            actor="n8n_webhook",
            after_state={
                "status": archive.status,
                "drive_folder_id": archive.drive_folder_id,
                "attempt_count": archive.attempt_count,
                "error": archive.last_error
            },
            reason="Pembaruan status sinkronisasi arsip dari n8n/Google Drive"
        )

        await db.commit()
        await db.refresh(archive)
        return archive


archive_service = ArchiveService()
