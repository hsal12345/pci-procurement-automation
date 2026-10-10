from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_actor_name, get_current_user_role
from app.config import settings
from app.database import get_db
from app.models.imports import ImportRecord
from app.models.packages import PackageRevision
from app.schemas.ai import (
    CandidateMappingProposal,
    SemanticAuditResponse,
    AIUsageResponse,
    ManualReviewRecordRequest,
    ManualReviewRecordResponse
)
from app.schemas.common import UserRoleEnum
from app.services.ai.mapping_assistant import AIMappingAssistant
from app.services.ai.discrepancy_auditor import SemanticDiscrepancyAuditor
from app.services.ai.budget_guard import AIBudgetGuard
from app.services.audit_service import audit_service

router = APIRouter(prefix="/ai", tags=["AI Assistance & Semantic Verification"])


def require_admin_or_finance(role: str = Depends(get_current_user_role)) -> str:
    allowed = {
        UserRoleEnum.ADMINISTRATION.value,
        UserRoleEnum.FINANCE_DIRECTOR.value,
        UserRoleEnum.SYSTEM_ADMINISTRATOR.value
    }
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: Hanya staf Administrasi atau Direktur Keuangan yang berwenang menggunakan fitur AI."
        )
    return role


@router.post("/imports/{id}/suggest-mapping", response_model=CandidateMappingProposal)
async def ai_suggest_mapping(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    actor_role: str = Depends(require_admin_or_finance)
):
    """Requests an intelligent candidate column mapping proposal from the advisory AI
    for non-standard uploaded spreadsheets (PRD Section FR02 and FR05).
    """
    res = await db.execute(select(ImportRecord).where(ImportRecord.id == id))
    rec = res.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Data impor dengan ID {id} tidak ditemukan.")

    # Locate uploaded workbook in storage directory
    upload_dir = settings.get_upload_dir()
    matching_files = list(upload_dir.glob(f"*_{rec.original_filename}"))
    if not matching_files:
        # Fallback to direct filename check
        fallback_file = upload_dir / rec.original_filename
        if fallback_file.exists():
            workbook_path = fallback_file
        else:
            raise HTTPException(
                status_code=404,
                detail="Berkas fisik spreadsheet tidak ditemukan di penyimpanan server."
            )
    else:
        workbook_path = matching_files[0]

    proposal, status_code, err_msg = await AIMappingAssistant.suggest_mapping_for_workbook(
        workbook_path=workbook_path,
        db=db
    )

    if not proposal:
        if status_code == "BUDGET_EXCEEDED":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=err_msg or "Batas anggaran AI bulanan tercapai. Silakan lakukan pemetaan kolom manual."
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=err_msg or "Layanan bantuan pemetaan AI sedang tidak tersedia. Gunakan pemetaan manual."
        )

    return proposal


@router.post("/revisions/{id}/audit", response_model=SemanticAuditResponse)
async def ai_audit_revision(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    actor_role: str = Depends(require_admin_or_finance),
    actor_name: str = Depends(get_current_actor_name)
):
    """Performs cross-document semantic discrepancy auditing across revision items,
    identifying brand substitutions, unit mismatches, or spec contradictions (PRD FR05, AT16).
    """
    audit_resp = await SemanticDiscrepancyAuditor.audit_revision(
        db=db,
        revision_id=id,
        actor_name=actor_name
    )
    return audit_resp


@router.post("/revisions/{id}/record-manual-review", response_model=ManualReviewRecordResponse)
async def record_manual_review(
    id: UUID,
    payload: ManualReviewRecordRequest,
    db: AsyncSession = Depends(get_db),
    actor_role: str = Depends(require_admin_or_finance)
):
    """Records that staff manually verified textual consistency across procurement documents,
    fulfilling the fallback requirement when AI is unavailable or budget is reached (PRD FR05 and AT16).
    """
    res = await db.execute(select(PackageRevision).where(PackageRevision.id == id))
    rev = res.scalar_one_or_none()
    if not rev:
        raise HTTPException(status_code=404, detail=f"Revisi dengan ID {id} tidak ditemukan.")

    rev.ai_review_status = "MANUAL_REVIEW_RECORDED"

    actor_name = payload.reviewer_name or payload.verifier_name or "Petugas Administrasi"
    review_reason = payload.reason or payload.verification_notes or payload.notes or "Verifikasi manual kepatuhan dokumen SPJ"

    await audit_service.log_event(
        db=db,
        entity_name="PackageRevision",
        entity_id=str(id),
        action="RECORD_MANUAL_REVIEW",
        actor=actor_name,
        before_state={"ai_review_status": "NOT_RUN"},
        after_state={"ai_review_status": "MANUAL_REVIEW_RECORDED"},
        reason=review_reason
    )

    await db.commit()

    now_iso = datetime.utcnow().isoformat()
    return ManualReviewRecordResponse(
        revision_id=id,
        ai_review_status="MANUAL_REVIEW_RECORDED",
        recorded_at=now_iso,
        recorded_by=actor_name,
        message="Verifikasi manual telah dicatat. Paket sekarang diizinkan untuk diajukan ke tahap Under Review."
    )


@router.get("/usage", response_model=AIUsageResponse)
async def get_ai_usage_dashboard(
    db: AsyncSession = Depends(get_db),
    actor_role: str = Depends(require_admin_or_finance)
):
    """Retrieves current month token usage, cumulative costs, remaining budget,
    and service availability for administrative monitoring (PRD Section 11).
    """
    p_tokens, c_tokens, tot_tokens, tot_cost, is_exceeded = await AIBudgetGuard.get_current_month_usage(db)
    remaining_budget = max(0.0, settings.AI_MONTHLY_BUDGET_USD - tot_cost)

    now = datetime.utcnow()
    month_str = now.strftime("%Y-%m")

    if not settings.AI_ENABLED:
        svc_status = "DISABLED"
    elif is_exceeded:
        svc_status = "BUDGET_EXCEEDED"
    else:
        svc_status = "ACTIVE"

    return AIUsageResponse(
        current_month=month_str,
        year_month=month_str,
        provider=settings.AI_PROVIDER,
        model=settings.AI_MODEL,
        prompt_tokens=p_tokens,
        total_prompt_tokens=p_tokens,
        completion_tokens=c_tokens,
        total_completion_tokens=c_tokens,
        total_tokens=tot_tokens,
        total_cost_usd=round(tot_cost, 6),
        monthly_budget_usd=settings.AI_MONTHLY_BUDGET_USD,
        budget_cap_usd=settings.AI_MONTHLY_BUDGET_USD,
        remaining_budget_usd=round(remaining_budget, 6),
        budget_remaining_usd=round(remaining_budget, 6),
        is_budget_exceeded=is_exceeded,
        service_status=svc_status
    )

