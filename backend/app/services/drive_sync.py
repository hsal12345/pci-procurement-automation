import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.archive import ArchiveRecord
from app.models.generation import Artifact
from app.models.packages import PackageRevision
from app.services.archive_service import archive_service
from app.services.audit_service import audit_service
from app.services.google_drive_service import GoogleDriveService, google_drive_service, sanitize_drive_name

logger = logging.getLogger(__name__)


def _resolve_local_artifact_path(file_path_str: str) -> Path:
    path = Path(file_path_str)
    if path.exists():
        return path
    rel_candidate = settings.BASE_DIR / file_path_str
    if rel_candidate.exists():
        return rel_candidate
    return path


class LocalDriveSyncWorker:
    """Fallback synchronization worker for offline or local environments running without live Drive API."""

    @staticmethod
    async def sync_archive_record(db, archive_id: UUID) -> ArchiveRecord:
        """Processes a single pending archive record."""
        try:
            logger.info(f"Processing local drive sync for archive ID: {archive_id}")
            simulated_folder_id = f"gdrive_fld_{str(archive_id)[:8]}"
            return await archive_service.process_callback(
                db=db,
                archive_id=archive_id,
                status_val="SYNCED",
                drive_folder_id=simulated_folder_id,
                drive_folder_url=f"https://drive.google.com/drive/folders/{simulated_folder_id}",
                progress_percent=100,
                current_step="Sinkronisasi simulasi lokal selesai.",
            )
        except Exception as e:
            logger.error(f"Local drive sync failed for archive {archive_id}: {e}")
            return await archive_service.process_callback(
                db=db,
                archive_id=archive_id,
                status_val="FAILED",
                error_message=str(e),
            )

    @staticmethod
    async def run_sync_sweep(db) -> int:
        """Processes all currently pending archive records."""
        pending = await archive_service.get_pending_archives(db)
        count = 0
        for rec in pending:
            await LocalDriveSyncWorker.sync_archive_record(db, rec.id)
            count += 1
        return count


async def execute_revision_drive_upload(revision_id: UUID, actor_name: str = "Admin") -> None:
    """Background task that uploads all generated artifacts for an APPROVED/ISSUED revision
    to Google Drive under Lv1 (Sekolah) -> Lv2 (Year) -> Lv3 (Triwulan) -> Lv4 (Kode Pengadaan) -> Lv5 (Files),
    overwriting existing files in place and tracking real-time progress.
    """
    logger.info(f"Starting Google Drive upload worker for revision {revision_id} by {actor_name}")
    async with AsyncSessionLocal() as db:
        archive = None
        try:
            rev_res = await db.execute(
                select(PackageRevision)
                .options(selectinload(PackageRevision.package))
                .where(PackageRevision.id == revision_id)
            )
            revision = rev_res.scalar_one_or_none()
            if not revision or not revision.package:
                raise ValueError(f"Revisi paket {revision_id} tidak ditemukan.")

            pkg = revision.package
            school_name = (revision.school_snapshot or {}).get("name", "Sekolah")
            pkg_folder_name = sanitize_drive_name(pkg.package_number, fallback="Paket")

            arch_res = await db.execute(
                select(ArchiveRecord).where(ArchiveRecord.revision_id == revision.id)
            )
            archive = arch_res.scalar_one_or_none()
            if not archive:
                archive = ArchiveRecord(
                    package_id=pkg.id,
                    revision_id=revision.id,
                    target_provider="GOOGLE_DRIVE",
                    folder_path=f"{school_name}/{pkg.fiscal_year}/Triwulan {pkg.quarter}/{pkg_folder_name} (Rev-{revision.revision_number})",
                    status="SYNCING",
                    progress_percent=5,
                    attempt_count=0,
                )
                db.add(archive)
                await db.flush()

            art_res = await db.execute(
                select(Artifact)
                .where(Artifact.revision_id == revision.id)
                .order_by(Artifact.format, Artifact.filename)
            )
            artifacts = list(art_res.scalars().all())
            if not artifacts:
                raise ValueError(
                    "Belum ada berkas dokumen yang dihasilkan untuk revisi ini."
                )

            archive.status = "SYNCING"
            archive.progress_percent = 8
            archive.current_step = "Mengautentikasi Google Drive API..."
            archive.uploaded_files = 0
            archive.total_files = len(artifacts)
            archive.total_bytes = 0
            archive.attempt_count += 1
            archive.last_attempt_at = datetime.utcnow()
            archive.last_error = None
            await db.commit()

            overwritten_count = 0

            if settings.is_drive_live_configured():
                folder_info = await google_drive_service.ensure_hierarchy(
                    school_name=school_name,
                    fiscal_year=pkg.fiscal_year,
                    quarter=pkg.quarter,
                    package_number=pkg.package_number,
                )
                archive.drive_folder_id = folder_info["folder_id"]
                archive.drive_folder_url = folder_info["folder_url"]
                archive.folder_path = (
                    f"{folder_info['display_path']} (Rev-{revision.revision_number})"
                )
                archive.progress_percent = 20
                archive.current_step = (
                    f"Folder siap: {folder_info['display_path']}. Mengunggah berkas..."
                )
                await db.commit()

                total = len(artifacts)
                for idx, art in enumerate(artifacts):
                    art.archive_status = "SYNCING"
                    target_filename = GoogleDriveService.resolve_canonical_filename(
                        art.doc_code, art.format, art.filename
                    )
                    local_path = _resolve_local_artifact_path(art.file_path)

                    upload_res = await google_drive_service.upload_or_overwrite_file(
                        local_path=local_path,
                        folder_id=folder_info["folder_id"],
                        target_filename=target_filename,
                        fmt=art.format,
                        package_number=pkg.package_number,
                        revision_number=revision.revision_number,
                        sha256_hash=art.sha256_hash,
                        file_size=art.file_size,
                    )

                    if upload_res.get("overwritten"):
                        overwritten_count += 1

                    art.drive_file_id = upload_res["id"]
                    art.drive_web_view_link = upload_res["webViewLink"]
                    art.archive_status = "SYNCED"
                    art.drive_synced_at = datetime.utcnow()

                    archive.uploaded_files = idx + 1
                    archive.total_bytes += int(art.file_size or 0)
                    archive.progress_percent = 20 + int(((idx + 1) / total) * 78)
                    verb = "Menimpa" if upload_res.get("overwritten") else "Mengunggah"
                    archive.current_step = (
                        f"{verb} ({idx + 1}/{total}): {upload_res['name']}"
                    )
                    await db.commit()
            else:
                # Mock fallback mode
                sim_folder_id = f"gdrive_fld_{str(archive.id)[:8]}"
                archive.drive_folder_id = sim_folder_id
                archive.drive_folder_url = f"https://drive.google.com/drive/folders/{sim_folder_id}"
                archive.folder_path = (
                    f"{school_name} / {pkg.fiscal_year} / Triwulan {pkg.quarter} / {pkg_folder_name} (Rev-{revision.revision_number})"
                )
                archive.progress_percent = 20
                archive.current_step = "Menyiapkan folder simulasi lokal..."
                await db.commit()

                total = len(artifacts)
                for idx, art in enumerate(artifacts):
                    sim_file_id = f"gdrive_file_{str(art.id)[:8]}"
                    art.drive_file_id = sim_file_id
                    art.drive_web_view_link = f"https://drive.google.com/file/d/{sim_file_id}/view"
                    art.archive_status = "SYNCED"
                    art.drive_synced_at = datetime.utcnow()

                    archive.uploaded_files = idx + 1
                    archive.total_bytes += int(art.file_size or 0)
                    archive.progress_percent = 20 + int(((idx + 1) / total) * 78)
                    archive.current_step = f"Simulasi unggah ({idx + 1}/{total}): {art.filename}"
                    await db.commit()

            # Mark prior synced archives for the same package as SUPERSEDED
            other_res = await db.execute(
                select(ArchiveRecord).where(
                    ArchiveRecord.package_id == pkg.id,
                    ArchiveRecord.revision_id != revision.id,
                    ArchiveRecord.status == "SYNCED",
                )
            )
            for other_arch in other_res.scalars().all():
                other_arch.status = "SUPERSEDED"
                other_arch.current_step = (
                    f"Digantikan oleh unggahan Revisi {revision.revision_number}"
                )

            archive.status = "SYNCED"
            archive.progress_percent = 100
            archive.synced_at = datetime.utcnow()
            archive.last_error = None
            archive.current_step = (
                f"Selesai! {len(artifacts)} berkas tersimpan di Google Drive "
                f"({school_name} / {pkg.fiscal_year} / Triwulan {pkg.quarter} / {pkg_folder_name})."
            )

            await audit_service.log_event(
                db=db,
                entity_name="ArchiveRecord",
                entity_id=str(archive.id),
                action="ARCHIVE_SYNCED",
                actor=actor_name,
                after_state={
                    "revision_id": str(revision.id),
                    "revision_number": revision.revision_number,
                    "folder_path": archive.folder_path,
                    "drive_folder_id": archive.drive_folder_id,
                    "drive_folder_url": archive.drive_folder_url,
                    "uploaded_files": archive.uploaded_files,
                    "overwritten_count": overwritten_count,
                },
                reason=f"Unggah paket ke Google Drive oleh {actor_name}",
            )
            await db.commit()
            logger.info(
                f"Google Drive upload succeeded for revision {revision_id}: "
                f"{archive.uploaded_files} files (overwritten={overwritten_count})"
            )

        except Exception as exc:
            logger.exception(f"Google Drive upload failed for revision {revision_id}: {exc}")
            await db.rollback()

            err_arch_res = await db.execute(
                select(ArchiveRecord).where(ArchiveRecord.revision_id == revision_id)
            )
            err_archive = err_arch_res.scalar_one_or_none()
            if err_archive:
                err_archive.status = "FAILED"
                err_archive.last_error = str(exc)
                err_archive.current_step = "Gagal mengunggah ke Google Drive."

                # Mark any artifacts left in SYNCING state as FAILED
                syncing_arts_res = await db.execute(
                    select(Artifact).where(
                        Artifact.revision_id == revision_id,
                        Artifact.archive_status == "SYNCING",
                    )
                )
                for s_art in syncing_arts_res.scalars().all():
                    s_art.archive_status = "FAILED"

                await audit_service.log_event(
                    db=db,
                    entity_name="ArchiveRecord",
                    entity_id=str(err_archive.id),
                    action="ARCHIVE_FAILED",
                    actor=actor_name,
                    after_state={"status": "FAILED", "error": str(exc)},
                    reason="Kegagalan saat mengunggah berkas ke Google Drive",
                )
                await db.commit()


drive_sync_worker = LocalDriveSyncWorker()
