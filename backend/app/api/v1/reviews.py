from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user_role
from app.schemas.reviews import (
    SubmitReviewRequest,
    WithdrawReviewRequest,
    ReturnReviewRequest,
    ApproveReviewRequest,
    IssueRequest,
    ReopenPackageRequest,
    CancelPackageRequest,
    WorkflowActionResponse,
)
from app.schemas.packages import PackageRevisionResponse
from app.core.workflow.state_machine import workflow_state_machine
from app.services.issuance_service import issuance_service

router = APIRouter(tags=["Workflow & Approvals"])


@router.post(
    "/packages/{id}/revisions/{revision_id}/submit",
    response_model=WorkflowActionResponse
)
@router.post(
    "/revisions/{revision_id}/submit",
    response_model=WorkflowActionResponse
)
async def submit_revision_for_review(
    revision_id: UUID,
    payload: SubmitReviewRequest,
    id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Submits a draft revision for Finance Director review.
    Prerequisites: role ADMINISTRATION, zero blocking findings, lines > 0, optimistic lock token.
    """
    rev = await workflow_state_machine.submit(
        db=db,
        revision_id=revision_id,
        actor_role=role,
        expected_version=payload.expected_version,
        actor_name=f"User ({role})",
        notes=payload.notes
    )
    pkg_id = id or rev.package_id
    return WorkflowActionResponse(
        package_id=pkg_id,
        revision_id=rev.id,
        previous_status="DRAFT",
        new_status=rev.status,
        package_status=rev.package.status if rev.package else "ACTIVE",
        version=rev.version,
        message="Revisi berhasil diajukan untuk peninjauan Direktur Keuangan.",
        timestamp=datetime.utcnow()
    )


@router.post(
    "/packages/{id}/revisions/{revision_id}/withdraw",
    response_model=WorkflowActionResponse
)
@router.post(
    "/revisions/{revision_id}/withdraw",
    response_model=WorkflowActionResponse
)
async def withdraw_revision_from_review(
    revision_id: UUID,
    payload: WithdrawReviewRequest,
    id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Allows Administration to withdraw an UNDER_REVIEW revision back to DRAFT."""
    rev = await workflow_state_machine.withdraw(
        db=db,
        revision_id=revision_id,
        actor_role=role,
        expected_version=payload.expected_version,
        reason=payload.reason,
        actor_name=f"User ({role})"
    )
    pkg_id = id or rev.package_id
    return WorkflowActionResponse(
        package_id=pkg_id,
        revision_id=rev.id,
        previous_status="UNDER_REVIEW",
        new_status=rev.status,
        package_status=rev.package.status if rev.package else "ACTIVE",
        version=rev.version,
        message="Pengajuan revisi berhasil ditarik kembali ke status DRAFT.",
        timestamp=datetime.utcnow()
    )


@router.post(
    "/packages/{id}/revisions/{revision_id}/return",
    response_model=WorkflowActionResponse
)
@router.post(
    "/revisions/{revision_id}/return",
    response_model=WorkflowActionResponse
)
async def return_revision_with_comments(
    revision_id: UUID,
    payload: ReturnReviewRequest,
    id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Allows Finance Director to return an UNDER_REVIEW revision with mandatory correction comments."""
    rev = await workflow_state_machine.return_revision(
        db=db,
        revision_id=revision_id,
        actor_role=role,
        expected_version=payload.expected_version,
        comment=payload.comment,
        actor_name=f"User ({role})"
    )
    pkg_id = id or rev.package_id
    return WorkflowActionResponse(
        package_id=pkg_id,
        revision_id=rev.id,
        previous_status="UNDER_REVIEW",
        new_status=rev.status,
        package_status=rev.package.status if rev.package else "ACTIVE",
        version=rev.version,
        message="Revisi berhasil dikembalikan ke Administrasi dengan catatan koreksi.",
        timestamp=datetime.utcnow()
    )


@router.post(
    "/packages/{id}/revisions/{revision_id}/approve",
    response_model=WorkflowActionResponse
)
@router.post(
    "/revisions/{revision_id}/approve",
    response_model=WorkflowActionResponse
)
async def approve_revision(
    revision_id: UUID,
    payload: ApproveReviewRequest,
    id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Allows Finance Director to approve an UNDER_REVIEW revision, permanently locking it."""
    rev = await workflow_state_machine.approve(
        db=db,
        revision_id=revision_id,
        actor_role=role,
        expected_version=payload.expected_version,
        manifest_hash=payload.manifest_hash,
        note=payload.note,
        actor_name=f"User ({role})"
    )
    pkg_id = id or rev.package_id
    return WorkflowActionResponse(
        package_id=pkg_id,
        revision_id=rev.id,
        previous_status="UNDER_REVIEW",
        new_status=rev.status,
        package_status=rev.package.status if rev.package else "ACTIVE",
        version=rev.version,
        message="Revisi berhasil disetujui (APPROVED) oleh Direktur Keuangan.",
        timestamp=datetime.utcnow()
    )


@router.post(
    "/packages/{id}/revisions/{revision_id}/issue",
    response_model=WorkflowActionResponse
)
@router.post(
    "/revisions/{revision_id}/issue",
    response_model=WorkflowActionResponse
)
async def issue_approved_package(
    revision_id: UUID,
    payload: Optional[IssueRequest] = None,
    id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Executes final issuance pipeline: validates BR13 & BR15, renders clean documents without watermarks,
    validates BR14 export equivalence, transitions package and revision to ISSUED, and registers Drive archival.
    """
    notes = payload.notes if payload else None
    rev = await issuance_service.execute_final_issuance(
        db=db,
        revision_id=revision_id,
        actor_role=role,
        actor_name=f"User ({role})",
        notes=notes
    )
    pkg_id = id or rev.package_id
    return WorkflowActionResponse(
        package_id=pkg_id,
        revision_id=rev.id,
        previous_status="APPROVED",
        new_status=rev.status,
        package_status="ISSUED",
        version=rev.version,
        message="Paket dokumen resmi berhasil diterbitkan tanpa watermark (ISSUED).",
        timestamp=datetime.utcnow()
    )


@router.post(
    "/packages/{id}/reopen",
    response_model=PackageRevisionResponse,
    status_code=status.HTTP_201_CREATED
)
async def reopen_issued_package(
    id: UUID,
    payload: ReopenPackageRequest,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Reopens an APPROVED or ISSUED package by creating a new incremented revision (Revision N+1) in DRAFT status.
    The prior revision remains ISSUED until the new revision reaches ISSUED.
    """
    new_rev = await workflow_state_machine.reopen(
        db=db,
        package_id=id,
        actor_role=role,
        reason=payload.reason,
        actor_name=f"User ({role})"
    )
    return new_rev


@router.post(
    "/packages/{id}/cancel",
    response_model=WorkflowActionResponse
)
async def cancel_procurement_package(
    id: UUID,
    payload: CancelPackageRequest,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Cancels a procurement package with state-contingent authorization:
    - If current revision is DRAFT or RETURNED: ADMINISTRATION or FINANCE_DIRECTOR.
    - If current revision is APPROVED or ISSUED: FINANCE_DIRECTOR ONLY.
    """
    pkg = await workflow_state_machine.cancel(
        db=db,
        package_id=id,
        actor_role=role,
        reason=payload.reason,
        actor_name=f"User ({role})",
        expected_version=payload.expected_version
    )
    return WorkflowActionResponse(
        package_id=pkg.id,
        revision_id=pkg.current_revision_id or pkg.id,
        previous_status="ACTIVE",
        new_status="CANCELLED",
        package_status="CANCELLED",
        version=1,
        message=f"Paket pengadaan berhasil dibatalkan: {payload.reason}",
        timestamp=datetime.utcnow()
    )
