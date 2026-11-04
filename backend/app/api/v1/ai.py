from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
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
    ManualReviewRecordResponse,
    AIRuntimeConfigResponse,
    AIRuntimeConfigUpdateRequest,
    AITestConnectionRequest,
    AITestConnectionResponse,
    AIUsageLogItem,
    AIPlaygroundTestRequest,
    AIPlaygroundTestResponse,
    SystemKnowledgeChatRequest,
    SystemKnowledgeChatResponse,
    SystemKnowledgeInfoResponse
)
from app.schemas.common import UserRoleEnum
from app.services.ai.mapping_assistant import AIMappingAssistant
from app.services.ai.discrepancy_auditor import SemanticDiscrepancyAuditor
from app.services.ai.budget_guard import AIBudgetGuard
from app.services.ai.runtime_manager import runtime_manager
from app.services.ai.system_knowledge_service import system_knowledge_service
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


RECOMMENDED_MODELS: Dict[str, List[str]] = {
    "gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ],
    "openrouter": [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "openai/gpt-4o-mini"
    ],
    "openai": [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-3.5-turbo"
    ],
    "ollama": [
        "llama3.2",
        "llama3.1",
        "mistral",
        "qwen2.5",
        "gemma2",
        "phi3"
    ],
    "mock": [
        "mock-rule-engine"
    ],
    "custom": [
        "default-model"
    ]
}


# =========================================================================
# Runtime Configuration Management (API Runtime vs Local Runtime)
# =========================================================================

@router.get("/config", response_model=AIRuntimeConfigResponse)
async def get_ai_runtime_config(
    actor_role: str = Depends(require_admin_or_finance)
):
    """Retrieves current AI runtime configuration (API vs Local runtime),
    active provider, model, masked API key, and preset choices.
    """
    cfg_dict = runtime_manager.get_masked_config_dict()
    return AIRuntimeConfigResponse(
        runtime_mode=cfg_dict["runtime_mode"],
        provider=cfg_dict["provider"],
        base_url=cfg_dict["base_url"],
        model=cfg_dict["model"],
        has_api_key=cfg_dict["has_api_key"],
        api_key_masked=cfg_dict["api_key_masked"],
        timeout_seconds=cfg_dict["timeout_seconds"],
        monthly_budget_usd=cfg_dict["monthly_budget_usd"],
        auto_fallback_to_local=cfg_dict["auto_fallback_to_local"],
        ai_enabled=cfg_dict["ai_enabled"],
        available_models=RECOMMENDED_MODELS
    )


@router.put("/config", response_model=AIRuntimeConfigResponse)
async def update_ai_runtime_config(
    payload: AIRuntimeConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor_role: str = Depends(require_admin_or_finance),
    actor_name: str = Depends(get_current_actor_name)
):
    """Updates AI runtime configuration dynamically (e.g. toggles between API runtime and
    Local runtime, updates endpoint or API key), persists to storage, and writes an audit event.
    """
    old_cfg = runtime_manager.get_config().model_dump()
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}

    new_cfg = runtime_manager.update_config(update_data)

    # Log to audit trail
    await audit_service.log_event(
        db=db,
        entity_name="AIRuntimeConfig",
        entity_id="active_runtime",
        action="UPDATE_RUNTIME_CONFIG",
        actor=actor_name,
        before_state={"runtime_mode": old_cfg["runtime_mode"], "provider": old_cfg["provider"], "model": old_cfg["model"]},
        after_state={"runtime_mode": new_cfg.runtime_mode, "provider": new_cfg.provider, "model": new_cfg.model},
        reason=f"Pembaruan runtime AI menjadi mode {new_cfg.runtime_mode.upper()} ({new_cfg.provider.upper()})"
    )

    cfg_dict = runtime_manager.get_masked_config_dict()
    return AIRuntimeConfigResponse(
        runtime_mode=cfg_dict["runtime_mode"],
        provider=cfg_dict["provider"],
        base_url=cfg_dict["base_url"],
        model=cfg_dict["model"],
        has_api_key=cfg_dict["has_api_key"],
        api_key_masked=cfg_dict["api_key_masked"],
        timeout_seconds=cfg_dict["timeout_seconds"],
        monthly_budget_usd=cfg_dict["monthly_budget_usd"],
        auto_fallback_to_local=cfg_dict["auto_fallback_to_local"],
        ai_enabled=cfg_dict["ai_enabled"],
        available_models=RECOMMENDED_MODELS
    )


@router.post("/test-connection", response_model=AITestConnectionResponse)
async def test_ai_connection(
    payload: Optional[AITestConnectionRequest] = None,
    actor_role: str = Depends(require_admin_or_finance)
):
    """Tests connectivity, responsiveness, and latency for active or candidate AI runtime."""
    test_dict = payload.model_dump(exclude_none=True) if payload else None
    result = await runtime_manager.test_connection(test_dict)
    return AITestConnectionResponse(**result)


# =========================================================================
# Usage Dashboard, Metrics, Telemetry Logs & Budget Management
# =========================================================================

@router.get("/usage", response_model=AIUsageResponse)
async def get_ai_usage_dashboard(
    db: AsyncSession = Depends(get_db),
    actor_role: str = Depends(require_admin_or_finance)
):
    """Retrieves current month token usage, cumulative costs, remaining budget,
    and service availability for administrative monitoring (PRD Section 11).
    """
    metrics = await AIBudgetGuard.get_usage_metrics(db)
    cfg = runtime_manager.get_config()

    budget_limit = cfg.monthly_budget_usd
    tot_cost = metrics["total_cost_usd"]
    remaining_budget = max(0.0, budget_limit - tot_cost)

    now = datetime.utcnow()
    month_str = now.strftime("%Y-%m")

    if not cfg.ai_enabled:
        svc_status = "DISABLED"
    elif metrics["is_budget_exceeded"]:
        svc_status = "BUDGET_EXCEEDED"
    else:
        svc_status = "ACTIVE"

    return AIUsageResponse(
        current_month=month_str,
        year_month=month_str,
        runtime_mode=cfg.runtime_mode,
        provider=cfg.provider,
        model=cfg.model,
        prompt_tokens=metrics["prompt_tokens"],
        total_prompt_tokens=metrics["prompt_tokens"],
        completion_tokens=metrics["completion_tokens"],
        total_completion_tokens=metrics["completion_tokens"],
        total_tokens=metrics["total_tokens"],
        total_cost_usd=round(tot_cost, 6),
        monthly_budget_usd=budget_limit,
        budget_cap_usd=budget_limit,
        remaining_budget_usd=round(remaining_budget, 6),
        budget_remaining_usd=round(remaining_budget, 6),
        is_budget_exceeded=metrics["is_budget_exceeded"],
        service_status=svc_status,
        total_requests=metrics["total_requests"],
        success_count=metrics["success_count"],
        failure_count=metrics["failure_count"],
        average_latency_ms=metrics["average_latency_ms"]
    )


@router.get("/logs", response_model=List[AIUsageLogItem])
async def list_ai_usage_logs(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="ALL, SUCCESS, FAILED, TIMEOUT, BUDGET_EXCEEDED, FALLBACK"),
    task_type: Optional[str] = Query(None, description="ALL, MAPPING_ASSISTANT, DISCREPANCY_AUDITOR, PLAYGROUND"),
    db: AsyncSession = Depends(get_db),
    actor_role: str = Depends(require_admin_or_finance)
):
    """Retrieves recent append-only AI execution and telemetry logs from ai_usage_logs."""
    records = await AIBudgetGuard.get_recent_logs(db, limit=limit, status=status, task_type=task_type)
    items = []
    for r in records:
        items.append(AIUsageLogItem(
            id=str(r.id),
            created_at=r.created_at.isoformat() if r.created_at else "",
            provider=r.provider,
            model=r.model,
            task_type=r.task_type,
            prompt_tokens=r.prompt_tokens,
            completion_tokens=r.completion_tokens,
            total_tokens=r.total_tokens,
            estimated_cost_usd=float(r.estimated_cost_usd or 0.0),
            status=r.status,
            latency_ms=r.latency_ms,
            error_message=r.error_message
        ))
    return items


# =========================================================================
# Interactive Playground / Live Testing Feature
# =========================================================================

@router.post("/playground/test", response_model=AIPlaygroundTestResponse)
async def ai_playground_test(
    payload: AIPlaygroundTestRequest,
    db: AsyncSession = Depends(get_db),
    actor_role: str = Depends(require_admin_or_finance)
):
    """Executes a live test against the active AI runtime (either API or Local runtime)
    so users can verify semantic detection or mapping outputs with live telemetry.
    """
    cfg = runtime_manager.get_config()
    adapter = runtime_manager.get_active_adapter()

    if payload.test_type == "DISCREPANCY":
        # Test semantic discrepancy check
        from app.schemas.ai import SemanticDiscrepancyItem, SemanticAuditResponse
        prompt = (
            f"Bandingkan dua deskripsi barang pengadaan sekolah berikut:\n"
            f"Item A: {payload.text_a or 'Pembersih Porselen'}\n"
            f"Item B: {payload.text_b or 'Porstex Pembersih Porselen 1 Liter'}\n\n"
            f"Tentukan apakah terdapat substitusi merek dagang, perbedaan ukuran/spesifikasi, atau variasi penamaan."
        )

        from pydantic import BaseModel, Field

        class PlaygroundDiscrepancyResult(BaseModel):
            discrepancy_type: str = Field(..., description="BRAND_SUBSTITUTION, SPECIFICATION_MISMATCH, UNIT_INCOMPATIBILITY, NAMING_VARIATION")
            severity: str = Field("WARNING", description="WARNING or INFO")
            explanation: str = Field(..., description="Penjelasan singkat dalam bahasa Indonesia")
            recommended_action: str = Field(..., description="Rekomendasi tindakan administratif")

        perf_metrics = {}
        async def _run():
            out, p_tok, c_tok, lat = await adapter.complete_structured(
                system_prompt="Anda adalah auditor pengadaan sekolah CV Pustaka Cemerlang Indonesia.",
                user_prompt=prompt,
                response_schema=PlaygroundDiscrepancyResult
            )
            perf_metrics["p_tokens"] = p_tok
            perf_metrics["c_tokens"] = c_tok
            perf_metrics["latency_ms"] = lat
            return out, p_tok, c_tok, lat

        res, status_code, err_msg = await AIBudgetGuard.execute_guarded(
            db=db,
            task_type="PLAYGROUND",
            execute_fn=_run
        )

        if not res:
            raise HTTPException(status_code=500, detail=err_msg or "Gagal mengeksekusi uji coba playground.")

        lat_ms = perf_metrics.get("latency_ms", 15 if cfg.provider == "mock" else 250)
        p_tok = perf_metrics.get("p_tokens", 85)
        c_tok = perf_metrics.get("c_tokens", 60)
        cost_val = 0.0 if cfg.runtime_mode == "local" else round(((p_tok / 1000.0) * settings.AI_COST_PER_1K_PROMPT_USD) + ((c_tok / 1000.0) * settings.AI_COST_PER_1K_COMPLETION_USD), 6)

        return AIPlaygroundTestResponse(
            test_type="DISCREPANCY",
            runtime_mode=cfg.runtime_mode,
            provider=cfg.provider,
            model=cfg.model,
            latency_ms=lat_ms,
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            cost_usd=cost_val,
            output=res.model_dump(),
            summary=f"Pemeriksaan semantik berhasil dievaluasi dengan status [{res.discrepancy_type}]."
        )

    else:
        # Test column mapping
        sample_hdrs = payload.sample_headers or ["No", "Nama Buku / Barang", "Spesifikasi", "Banyaknya", "Satuan", "Harga Satuan", "Total"]
        prompt = (
            f"Identifikasi pemetaan kolom untuk baris header berikut:\n"
            f"{sample_hdrs}"
        )

        perf_metrics = {}
        async def _run():
            out, p_tok, c_tok, lat = await adapter.complete_structured(
                system_prompt=AIMappingAssistant.SYSTEM_PROMPT,
                user_prompt=prompt,
                response_schema=CandidateMappingProposal
            )
            perf_metrics["p_tokens"] = p_tok
            perf_metrics["c_tokens"] = c_tok
            perf_metrics["latency_ms"] = lat
            return out, p_tok, c_tok, lat

        res, status_code, err_msg = await AIBudgetGuard.execute_guarded(
            db=db,
            task_type="PLAYGROUND",
            execute_fn=_run
        )

        if not res:
            raise HTTPException(status_code=500, detail=err_msg or "Gagal mengeksekusi pemetaan playground.")

        lat_ms = perf_metrics.get("latency_ms", 15 if cfg.provider == "mock" else 300)
        p_tok = perf_metrics.get("p_tokens", 110)
        c_tok = perf_metrics.get("c_tokens", 75)
        cost_val = 0.0 if cfg.runtime_mode == "local" else round(((p_tok / 1000.0) * settings.AI_COST_PER_1K_PROMPT_USD) + ((c_tok / 1000.0) * settings.AI_COST_PER_1K_COMPLETION_USD), 6)

        return AIPlaygroundTestResponse(
            test_type="MAPPING",
            runtime_mode=cfg.runtime_mode,
            provider=cfg.provider,
            model=cfg.model,
            latency_ms=lat_ms,
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            cost_usd=cost_val,
            output=res.model_dump(),
            summary=f"Pemetaan berhasil: Skor keyakinan {res.confidence_score * 100:.1f}%."
        )


# =========================================================================
# Core Transaction Operations (Mapping & Discrepancy Audit)
# =========================================================================

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

    upload_dir = settings.get_upload_dir()
    matching_files = list(upload_dir.glob(f"*_{rec.original_filename}"))
    if not matching_files:
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


# =========================================================================
# System Knowledge Base & Navigation Assistant Endpoints (PRD FR05)
# =========================================================================

@router.get("/knowledge", response_model=SystemKnowledgeInfoResponse)
async def get_system_knowledge():
    """Retrieves metadata and full markdown text of the system knowledge base
    used by the AI assistant for contextual guidance.
    """
    return system_knowledge_service.get_info()


@router.post("/knowledge/chat", response_model=SystemKnowledgeChatResponse)
async def chat_with_system_knowledge(
    payload: SystemKnowledgeChatRequest,
    db: AsyncSession = Depends(get_db),
    actor_role: str = Depends(require_admin_or_finance)
):
    """Processes a navigation guide or system question against the system knowledge context,
    enforcing strict boundaries and tracking token telemetry.
    """
    response, status_code, err_msg = await system_knowledge_service.chat(db=db, request=payload)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=err_msg or "Gagal memproses pesan pada asisten pengetahuan sistem."
        )
    return response

