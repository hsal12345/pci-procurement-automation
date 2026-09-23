from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.packages import Package, PackageRevision, RevisionLine, DocumentEvent, DocumentNumber
from app.models.approvals import Approval
from app.models.validation import ValidationRun
from app.models.generation import Artifact
from app.schemas.common import UserRoleEnum, RevisionStatusEnum, PackageCommercialStatusEnum
from app.services.audit_service import audit_service


class WorkflowStateMachine:
    """Formal business state machine coordinating revision lifecycle transitions,
    state-contingent RBAC, optimistic concurrency control, and audit trail tracking.
    """

    @classmethod
    async def get_revision_with_details(cls, db: AsyncSession, revision_id: UUID) -> PackageRevision:
        res = await db.execute(
            select(PackageRevision)
            .options(
                selectinload(PackageRevision.lines),
                selectinload(PackageRevision.events),
                selectinload(PackageRevision.numbers),
                selectinload(PackageRevision.package),
                selectinload(PackageRevision.validation_runs),
            )
            .where(PackageRevision.id == revision_id)
        )
        revision = res.scalar_one_or_none()
        if not revision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Revisi paket dengan ID {revision_id} tidak ditemukan."
            )
        return revision

    @classmethod
    def check_optimistic_lock(cls, revision: PackageRevision, expected_version: int):
        if revision.version != expected_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Konflik persaingan pembaruan (OPTIMISTIC_LOCK_CONFLICT): "
                    f"versi token yang Anda kirimkan ({expected_version}) berbeda dengan versi data terkini di server ({revision.version}). "
                    f"Silakan muat ulang data untuk merekonsiliasi perubahan."
                )
            )

    @classmethod
    async def submit(
        cls,
        db: AsyncSession,
        revision_id: UUID,
        actor_role: str,
        expected_version: int,
        actor_name: str = "Administrator",
        notes: Optional[str] = None
    ) -> PackageRevision:
        """Transitions DRAFT/RETURNED -> UNDER_REVIEW.
        Enforces role ADMINISTRATION, zero blocking findings, lines > 0, and optimistic locking.
        """
        if actor_role not in (UserRoleEnum.ADMINISTRATION.value, UserRoleEnum.SYSTEM_ADMINISTRATOR.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hanya peran Bagian Administrasi yang berwenang mengajukan revisi untuk peninjauan."
            )

        revision = await cls.get_revision_with_details(db, revision_id)
        cls.check_optimistic_lock(revision, expected_version)

        valid_source_states = (RevisionStatusEnum.DRAFT.value, RevisionStatusEnum.RETURNED.value)
        if revision.status not in valid_source_states:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tidak dapat mengajukan revisi dengan status '{revision.status}'. Status harus DRAFT atau RETURNED."
            )

        # 1. Prerequisite: Lines must exist
        if not revision.lines or len(revision.lines) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Paket tidak dapat diajukan: daftar rincian barang/jasa kosong. Minimal harus terdapat 1 item."
            )

        # 2. Prerequisite: Check latest validation run for blocking errors
        val_res = await db.execute(
            select(ValidationRun)
            .where(ValidationRun.revision_id == revision.id)
            .order_by(desc(ValidationRun.run_at))
        )
        latest_val = val_res.scalars().first()
        if latest_val and latest_val.error_count > 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Paket tidak dapat diajukan: terdeteksi {latest_val.error_count} temuan pemblokir (BLOCKING) "
                    f"pada pemeriksaan kepatuhan aturan bisnis (BR01-BR15). Selesaikan temuan terlebih dahulu."
                )
            )

        # 3. Prerequisite: Check AI review status or recorded manual review (PRD FR05 and Acceptance Test AT16)
        from app.config import settings
        if settings.AI_ENABLED:
            if revision.ai_review_status == "NOT_RUN":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Paket belum melalui pemeriksaan teks AI atau verifikasi manual tercatat."
                )
            if revision.ai_review_status == "FAILED":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Pemeriksaan AI gagal atau tidak tersedia. Harap lakukan 'Catat Verifikasi Manual' sebelum mengajukan persetujuan."
                )

        # Transition
        prev_status = revision.status
        revision.status = RevisionStatusEnum.UNDER_REVIEW.value
        revision.is_locked = True
        revision.version += 1
        if notes:
            revision.notes = notes

        # Keep package status active
        if revision.package:
            revision.package.status = PackageCommercialStatusEnum.ACTIVE.value

        await audit_service.log_event(
            db=db,
            entity_name="PackageRevision",
            entity_id=str(revision.id),
            action="SUBMIT",
            actor=actor_name,
            before_state={"status": prev_status, "version": expected_version, "is_locked": False},
            after_state={"status": revision.status, "version": revision.version, "is_locked": True},
            reason=notes or "Diajukan untuk peninjauan oleh Administrasi"
        )

        await db.commit()
        await db.refresh(revision)
        return revision

    @classmethod
    async def withdraw(
        cls,
        db: AsyncSession,
        revision_id: UUID,
        actor_role: str,
        expected_version: int,
        reason: str,
        actor_name: str = "Administrator"
    ) -> PackageRevision:
        """Transitions UNDER_REVIEW -> DRAFT.
        Allows Administration to pull back a review request.
        """
        if actor_role not in (UserRoleEnum.ADMINISTRATION.value, UserRoleEnum.SYSTEM_ADMINISTRATOR.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hanya peran Bagian Administrasi yang berwenang menarik kembali pengajuan revisi."
            )

        revision = await cls.get_revision_with_details(db, revision_id)
        cls.check_optimistic_lock(revision, expected_version)

        if revision.status != RevisionStatusEnum.UNDER_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tidak dapat menarik kembali revisi dengan status '{revision.status}'. Hanya revisi UNDER_REVIEW yang dapat ditarik."
            )

        prev_status = revision.status
        revision.status = RevisionStatusEnum.DRAFT.value
        revision.is_locked = False
        revision.version += 1

        await audit_service.log_event(
            db=db,
            entity_name="PackageRevision",
            entity_id=str(revision.id),
            action="WITHDRAW",
            actor=actor_name,
            before_state={"status": prev_status, "version": expected_version, "is_locked": True},
            after_state={"status": revision.status, "version": revision.version, "is_locked": False},
            reason=reason
        )

        await db.commit()
        await db.refresh(revision)
        return revision

    @classmethod
    async def return_revision(
        cls,
        db: AsyncSession,
        revision_id: UUID,
        actor_role: str,
        expected_version: int,
        comment: str,
        actor_name: str = "Direktur Keuangan"
    ) -> PackageRevision:
        """Transitions UNDER_REVIEW -> RETURNED.
        Allows Finance Director to return package with mandatory correction comments.
        """
        if actor_role not in (UserRoleEnum.FINANCE_DIRECTOR.value, UserRoleEnum.SYSTEM_ADMINISTRATOR.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hanya Direktur Keuangan yang berwenang mengembalikan paket dokumen pengadaan."
            )

        if not comment or len(comment.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Catatan koreksi pengembalian wajib diisi secara rinci oleh Direktur Keuangan."
            )

        revision = await cls.get_revision_with_details(db, revision_id)
        cls.check_optimistic_lock(revision, expected_version)

        if revision.status != RevisionStatusEnum.UNDER_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tidak dapat mengembalikan revisi dengan status '{revision.status}'. Status harus UNDER_REVIEW."
            )

        prev_status = revision.status
        revision.status = RevisionStatusEnum.RETURNED.value
        revision.is_locked = False
        revision.version += 1

        # Record approval rejection
        approval = Approval(
            revision_id=revision.id,
            approver_name=actor_name,
            approver_role=actor_role,
            decision="RETURNED",
            decision_reason=comment,
            signed_at=datetime.utcnow()
        )
        db.add(approval)

        await audit_service.log_event(
            db=db,
            entity_name="PackageRevision",
            entity_id=str(revision.id),
            action="RETURN",
            actor=actor_name,
            before_state={"status": prev_status, "version": expected_version, "is_locked": True},
            after_state={"status": revision.status, "version": revision.version, "is_locked": False},
            reason=comment
        )

        await db.commit()
        await db.refresh(revision)
        return revision

    @classmethod
    async def approve(
        cls,
        db: AsyncSession,
        revision_id: UUID,
        actor_role: str,
        expected_version: int,
        manifest_hash: Optional[str] = None,
        note: Optional[str] = None,
        actor_name: str = "Direktur Keuangan"
    ) -> PackageRevision:
        """Transitions UNDER_REVIEW -> APPROVED.
        Enforces role FINANCE_DIRECTOR, binds revision to manifest hash, and locks revision permanently.
        """
        if actor_role not in (UserRoleEnum.FINANCE_DIRECTOR.value, UserRoleEnum.SYSTEM_ADMINISTRATOR.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hanya Direktur Keuangan yang berwenang menyetujui paket pengadaan."
            )

        revision = await cls.get_revision_with_details(db, revision_id)
        cls.check_optimistic_lock(revision, expected_version)

        if revision.status != RevisionStatusEnum.UNDER_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tidak dapat menyetujui revisi dengan status '{revision.status}'. Status harus UNDER_REVIEW."
            )

        # Transition
        prev_status = revision.status
        revision.status = RevisionStatusEnum.APPROVED.value
        revision.is_locked = True
        revision.version += 1

        # Record approval
        approval = Approval(
            revision_id=revision.id,
            approver_name=actor_name,
            approver_role=actor_role,
            decision="APPROVED",
            decision_reason=note or "Disetujui oleh Direktur Keuangan",
            reviewed_manifest_hash=manifest_hash,
            signed_at=datetime.utcnow()
        )
        db.add(approval)

        await audit_service.log_event(
            db=db,
            entity_name="PackageRevision",
            entity_id=str(revision.id),
            action="APPROVE",
            actor=actor_name,
            before_state={"status": prev_status, "version": expected_version, "is_locked": True},
            after_state={
                "status": revision.status,
                "version": revision.version,
                "is_locked": True,
                "reviewed_manifest_hash": manifest_hash
            },
            reason=note or "Disetujui oleh Direktur Keuangan"
        )

        await db.commit()
        await db.refresh(revision)
        return revision

    @classmethod
    async def reopen(
        cls,
        db: AsyncSession,
        package_id: UUID,
        actor_role: str,
        reason: str,
        actor_name: str = "Administrator"
    ) -> PackageRevision:
        """Clones the latest revision into a new revision (DRAFT) with revision_number = N+1.
        Allowed roles: ADMINISTRATION, FINANCE_DIRECTOR.
        The previous issued revision remains ISSUED until the new revision reaches ISSUED.
        """
        if actor_role not in (UserRoleEnum.ADMINISTRATION.value, UserRoleEnum.FINANCE_DIRECTOR.value, UserRoleEnum.SYSTEM_ADMINISTRATOR.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hanya peran Administrasi atau Direktur Keuangan yang berwenang membuka kembali paket."
            )

        if not reason or len(reason.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Alasan pembukaan kembali paket wajib diisi secara rinci."
            )

        # Find package and latest revision
        pkg_res = await db.execute(
            select(Package)
            .options(
                selectinload(Package.revisions).selectinload(PackageRevision.lines),
                selectinload(Package.revisions).selectinload(PackageRevision.events),
                selectinload(Package.revisions).selectinload(PackageRevision.numbers),
            )
            .where(Package.id == package_id)
        )
        pkg = pkg_res.scalar_one_or_none()
        if not pkg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paket pengadaan dengan ID {package_id} tidak ditemukan."
            )

        if not pkg.revisions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paket tidak memiliki riwayat revisi yang dapat dibuka kembali."
            )

        # Sort revisions by revision_number
        sorted_revs = sorted(pkg.revisions, key=lambda r: r.revision_number)
        latest_rev = sorted_revs[-1]

        if latest_rev.status not in (RevisionStatusEnum.APPROVED.value, RevisionStatusEnum.ISSUED.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hanya paket yang telah disetujui (APPROVED) atau diterbitkan (ISSUED) yang dapat dibuka kembali sebagai revisi baru. Status saat ini: {latest_rev.status}."
            )

        new_rev_number = latest_rev.revision_number + 1

        # Create new PackageRevision in DRAFT status
        new_revision = PackageRevision(
            package_id=pkg.id,
            revision_number=new_rev_number,
            version=1,
            status=RevisionStatusEnum.DRAFT.value,
            ai_review_status=latest_rev.ai_review_status or "COMPLETED",
            school_snapshot=dict(latest_rev.school_snapshot or {}),
            company_snapshot=dict(latest_rev.company_snapshot or {}),
            tax_policy_snapshot=list(latest_rev.tax_policy_snapshot or []),
            officials_snapshot=list(latest_rev.officials_snapshot or []),
            subtotal=latest_rev.subtotal,
            tax_total=latest_rev.tax_total,
            grand_total=latest_rev.grand_total,
            terbilang_grand_total=latest_rev.terbilang_grand_total,
            is_locked=False,
            notes=f"Revisi {new_rev_number} dibuka kembali: {reason}"
        )
        db.add(new_revision)
        await db.flush()

        # Clone lines
        for line in latest_rev.lines:
            new_line = RevisionLine(
                revision_id=new_revision.id,
                line_number=line.line_number,
                item_id=line.item_id,
                original_description=line.original_description,
                confirmed_description=line.confirmed_description,
                specification=line.specification,
                quantity=line.quantity,
                received_quantity=line.received_quantity,
                unit=line.unit,
                hps_unit_price=line.hps_unit_price,
                offer_unit_price=line.offer_unit_price,
                final_unit_price=line.final_unit_price,
                discount=line.discount,
                line_total=line.line_total,
                condition=line.condition,
                notes=line.notes
            )
            db.add(new_line)

        # Clone events
        for ev in latest_rev.events:
            new_ev = DocumentEvent(
                revision_id=new_revision.id,
                event_code=ev.event_code,
                event_date=ev.event_date,
                day_name_id=ev.day_name_id,
                location=ev.location,
                notes=ev.notes
            )
            db.add(new_ev)

        # Clone document numbers
        for num in latest_rev.numbers:
            new_num = DocumentNumber(
                revision_id=new_revision.id,
                doc_code=num.doc_code,
                doc_number=num.doc_number,
                issuer=num.issuer,
                counter_val=num.counter_val,
                issue_date=num.issue_date,
                is_reserved=True
            )
            db.add(new_num)

        # Update package current revision pointer and keep package ACTIVE
        pkg.current_revision_id = new_revision.id
        pkg.status = PackageCommercialStatusEnum.ACTIVE.value

        await audit_service.log_event(
            db=db,
            entity_name="Package",
            entity_id=str(pkg.id),
            action="REOPEN",
            actor=actor_name,
            before_state={"current_revision_id": str(latest_rev.id), "revision_number": latest_rev.revision_number},
            after_state={"current_revision_id": str(new_revision.id), "revision_number": new_rev_number},
            reason=reason
        )

        await db.commit()

        # Eager load relationships for API response serialization
        new_rev_res = await db.execute(
            select(PackageRevision)
            .options(
                selectinload(PackageRevision.lines),
                selectinload(PackageRevision.events),
                selectinload(PackageRevision.numbers),
            )
            .where(PackageRevision.id == new_revision.id)
        )
        return new_rev_res.scalar_one()

    @classmethod
    async def cancel(
        cls,
        db: AsyncSession,
        package_id: UUID,
        actor_role: str,
        reason: str,
        actor_name: str = "Petugas",
        expected_version: Optional[int] = None
    ) -> Package:
        """State-contingent cancellation RBAC:
        - If current revision is DRAFT or RETURNED: ADMINISTRATION or FINANCE_DIRECTOR allowed.
        - If current revision is APPROVED or ISSUED: ONLY FINANCE_DIRECTOR allowed.
        Marks document numbers as non-reusable.
        """
        if not reason or len(reason.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Alasan pembatalan paket pengadaan wajib diisi secara rinci."
            )

        pkg_res = await db.execute(
            select(Package)
            .options(
                selectinload(Package.revisions).selectinload(PackageRevision.numbers)
            )
            .where(Package.id == package_id)
        )
        pkg = pkg_res.scalar_one_or_none()
        if not pkg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paket pengadaan dengan ID {package_id} tidak ditemukan."
            )

        current_rev = None
        if pkg.current_revision_id:
            for r in pkg.revisions:
                if r.id == pkg.current_revision_id:
                    current_rev = r
                    break

        if not current_rev and pkg.revisions:
            current_rev = pkg.revisions[-1]

        # Check optimistic lock if provided
        if current_rev and expected_version is not None:
            cls.check_optimistic_lock(current_rev, expected_version)

        current_status = current_rev.status if current_rev else pkg.status

        # State-contingent RBAC:
        if current_status in (RevisionStatusEnum.APPROVED.value, RevisionStatusEnum.ISSUED.value):
            if actor_role not in (UserRoleEnum.FINANCE_DIRECTOR.value, UserRoleEnum.SYSTEM_ADMINISTRATOR.value):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Hanya Direktur Keuangan yang berwenang membatalkan paket yang telah disetujui atau diterbitkan."
                )

        prev_pkg_status = pkg.status
        pkg.status = PackageCommercialStatusEnum.CANCELLED.value

        if current_rev:
            prev_rev_status = current_rev.status
            current_rev.status = RevisionStatusEnum.CANCELLED.value
            current_rev.is_locked = True
            current_rev.version += 1

            # Invalidate reserved numbers
            for doc_num in current_rev.numbers:
                doc_num.is_reserved = False

        await audit_service.log_event(
            db=db,
            entity_name="Package",
            entity_id=str(pkg.id),
            action="CANCEL",
            actor=actor_name,
            before_state={"package_status": prev_pkg_status, "revision_status": current_status},
            after_state={"package_status": pkg.status, "revision_status": RevisionStatusEnum.CANCELLED.value},
            reason=reason
        )

        await db.commit()
        await db.refresh(pkg)
        return pkg


workflow_state_machine = WorkflowStateMachine()
