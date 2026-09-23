import logging
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.archive_service import archive_service
from app.models.archive import ArchiveRecord

logger = logging.getLogger(__name__)


class LocalDriveSyncWorker:
    """Fallback synchronization worker for offline or local environments running without n8n.
    Simulates Google Drive folder creation and local mirror backup.
    """

    @staticmethod
    async def sync_archive_record(db: AsyncSession, archive_id: UUID) -> ArchiveRecord:
        """Processes a single pending archive record."""
        try:
            logger.info(f"Processing local drive sync for archive ID: {archive_id}")
            # Generate simulated Google Drive folder ID
            simulated_folder_id = f"gdrive_fld_{str(archive_id)[:8]}"
            return await archive_service.process_callback(
                db=db,
                archive_id=archive_id,
                status_val="SYNCED",
                drive_folder_id=simulated_folder_id
            )
        except Exception as e:
            logger.error(f"Local drive sync failed for archive {archive_id}: {e}")
            return await archive_service.process_callback(
                db=db,
                archive_id=archive_id,
                status_val="FAILED",
                error_message=str(e)
            )

    @staticmethod
    async def run_sync_sweep(db: AsyncSession) -> int:
        """Processes all currently pending archive records."""
        pending = await archive_service.get_pending_archives(db)
        count = 0
        for rec in pending:
            await LocalDriveSyncWorker.sync_archive_record(db, rec.id)
            count += 1
        return count


drive_sync_worker = LocalDriveSyncWorker()
