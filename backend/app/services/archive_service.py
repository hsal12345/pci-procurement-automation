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
from app.services.google_drive_service import sanitize_drive_name


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
        pkg_folder_name = sanitize_drive_name(pkg.package_number, fallback="Paket")
        folder_path = (
            f"{school_name}/{pkg.fiscal_year}/Triwulan {pkg.quarter}/{pkg_folder_name} "
            f"(Rev-{revision.revision_number})"
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
                progress_percent=0,
                uploaded_files=0,
                total_files=0,
                total_bytes=0,
                attempt_count=0
            )
            db.add(archive)
        else:
            archive.folder_path = folder_path
            archive.status = "PENDING"
            archive.progress_percent = 0
            archive.current_step = None
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
        drive_folder_url: Optional[str] = None,
        error_message: Optional[str] = None,
        uploaded_files: Optional[int] = None,
        total_files: Optional[int] = None,
        total_bytes: Optional[int] = None,
        progress_percent: Optional[int] = None,
        current_step: Optional[str] = None,
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

        if uploaded_files is not None:
            archive.uploaded_files = uploaded_files
        if total_files is not None:
            archive.total_files = total_files
        if total_bytes is not None:
            archive.total_bytes = total_bytes
        if current_step is not None:
            archive.current_step = current_step

        if status_val.upper() == "SYNCED":
            archive.status = "SYNCED"
            archive.drive_folder_id = drive_folder_id
            if drive_folder_url is not None:
                archive.drive_folder_url = drive_folder_url
            archive.progress_percent = progress_percent if progress_percent is not None else 100
            archive.synced_at = datetime.utcnow()
            archive.last_error = None
        else:
            archive.status = "FAILED"
            if progress_percent is not None:
                archive.progress_percent = progress_percent
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
