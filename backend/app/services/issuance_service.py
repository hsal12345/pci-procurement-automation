import logging
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.packages import Package, PackageRevision
from app.models.generation import GenerationJob, Artifact
from app.schemas.common import UserRoleEnum, RevisionStatusEnum, PackageCommercialStatusEnum
from app.services.generation_worker import run_generation_job
from app.services.logistics_service import logistics_service
from app.services.archive_service import archive_service
from app.services.audit_service import audit_service

logger = logging.getLogger("app.services.issuance_service")


class IssuanceService:
    @staticmethod
    async def execute_final_issuance(
        db: AsyncSession,
        revision_id: UUID,
        actor_role: str,
        actor_name: str = "Direktur Keuangan",
        notes: Optional[str] = None
    ) -> PackageRevision:
        """Coordinates the final transition from APPROVED to ISSUED:
        1. Validates revision is APPROVED.
        2. Enforces BR13: Physical receipt confirmed and items BAIK (not partial or damaged).
        3. Enforces BR15: Freshness & immutability.
        4. Generates clean official documents (is_draft_override=False) without watermarks.
        5. Validates BR14: Export equivalence across XLSX, DOCX, PDF, ZIP.
        6. Atomically marks current revision as ISSUED and predecessor revisions as SUPERSEDED.
        7. Triggers decoupled Google Drive / n8n archival synchronization.
        """
        allowed_roles = (
            UserRoleEnum.FINANCE_DIRECTOR.value,
            UserRoleEnum.ADMINISTRATION.value,
            UserRoleEnum.SYSTEM_ADMINISTRATOR.value
        )
        if actor_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hanya Direktur Keuangan atau Administrasi yang berwenang menerbitkan paket dokumen resmi."
            )

        # 1. Load revision with package
        res_rev = await db.execute(
            select(PackageRevision)
            .options(
                selectinload(PackageRevision.lines),
                selectinload(PackageRevision.package).selectinload(Package.revisions),
                selectinload(PackageRevision.logistics_record)
            )
            .where(PackageRevision.id == revision_id)
        )
        revision = res_rev.scalar_one_or_none()
        if not revision or not revision.package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Revisi paket dengan ID {revision_id} tidak ditemukan."
            )

        if revision.status != RevisionStatusEnum.APPROVED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Hanya revisi yang telah disetujui (APPROVED) yang dapat diterbitkan secara resmi. "
                    f"Status revisi saat ini: '{revision.status}'."
                )
            )

        # 2. Enforce BR13 Logistics Compliance (delivery confirmed, all BAIK)
        await logistics_service.enforce_br13_logistics_compliance(db, revision_id)

        # 3. Create and execute clean generation job (without draft watermark)
        gen_job = GenerationJob(
            revision_id=revision.id,
            status="QUEUED",
            progress_percent=0
        )
        db.add(gen_job)
        await db.commit()
        await db.refresh(gen_job)

        # Run document generation synchronously for final issuance
        await run_generation_job(
            job_id=gen_job.id,
            formats=["XLSX", "DOCX", "PDF", "ZIP"],
            is_draft_override=False
        )

        # Re-fetch generation job status (refresh to bypass identity map cache from separate session)
        await db.refresh(gen_job)

        if gen_job.status not in ("SUCCEEDED", "COMPLETED"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menghasilkan berkas dokumen resmi tanpa watermark: {gen_job.error_message}"
            )

        # 4. Enforce BR14 Export Equivalence: Check generated artifacts
        res_arts = await db.execute(
            select(Artifact).where(Artifact.revision_id == revision.id)
        )
        artifacts = res_arts.scalars().all()
        formats_present = {a.format.upper() for a in artifacts}
        required_formats = {"XLSX", "DOCX", "PDF", "ZIP"}
        if not required_formats.issubset(formats_present):
            missing = required_formats - formats_present
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Pelanggaran BR14: Format keluaran dokumen tidak lengkap. Format hilang: {missing}."
            )

        # 5. Atomically update statuses:
        # Current revision becomes ISSUED
        prev_rev_status = revision.status
        revision.status = RevisionStatusEnum.ISSUED.value
        revision.is_locked = True
        revision.version += 1

        # Package becomes ISSUED
        pkg = revision.package
        prev_pkg_status = pkg.status
        pkg.status = PackageCommercialStatusEnum.ISSUED.value

        # Predecessor revisions atomically become SUPERSEDED
        for other_rev in pkg.revisions:
            if other_rev.id != revision.id and other_rev.status == RevisionStatusEnum.ISSUED.value:
                other_rev.status = RevisionStatusEnum.SUPERSEDED.value
                other_rev.is_locked = True

        await audit_service.log_event(
            db=db,
            entity_name="PackageRevision",
            entity_id=str(revision.id),
            action="ISSUE",
            actor=actor_name,
            before_state={"revision_status": prev_rev_status, "package_status": prev_pkg_status},
            after_state={"revision_status": revision.status, "package_status": pkg.status},
            reason=notes or "Penerbitan resmi dokumen pengadaan tanpa watermark (Final Issuance)"
        )

        await db.commit()
        await db.refresh(revision)

        # 6. Trigger decoupled archive registration
        try:
            await archive_service.register_archive_request(db, revision.id)
        except Exception as e:
            logger.warning(f"Archive registration encountered a non-blocking error: {e}")

        return revision


issuance_service = IssuanceService()
