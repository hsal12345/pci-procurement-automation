import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.config import settings
from app.models.ai import AIUsageLog
from app.services.ai.runtime_manager import runtime_manager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AIBudgetGuard:
    """Guards outgoing AI operations against monthly budget caps, tracks token
    consumption and estimated costs in the database, and provides graceful offline fallback
    when providers time out or become unreachable (PRD Section 11 and FR05).
    """

    @classmethod
    async def get_current_month_usage(cls, db: AsyncSession) -> Tuple[int, int, int, float, bool]:
        """Calculates current month token counts and estimated costs.
        Returns: (prompt_tokens, completion_tokens, total_tokens, total_cost_usd, is_budget_exceeded)
        """
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)

        stmt = select(
            func.coalesce(func.sum(AIUsageLog.prompt_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.completion_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.estimated_cost_usd), Decimal("0.0")),
        ).where(AIUsageLog.created_at >= start_of_month)

        result = await db.execute(stmt)
        row = result.one()
        p_tokens = int(row[0])
        c_tokens = int(row[1])
        t_tokens = int(row[2])
        tot_cost = float(row[3])

        cfg = runtime_manager.get_config()
        budget_limit = cfg.monthly_budget_usd if cfg.runtime_mode == "api" else 999999.0
        is_exceeded = (tot_cost >= budget_limit) if cfg.runtime_mode == "api" else False
        return p_tokens, c_tokens, t_tokens, tot_cost, is_exceeded

    @classmethod
    async def get_usage_metrics(cls, db: AsyncSession) -> Dict[str, Any]:
        """Retrieves comprehensive metrics: tokens, cost, requests count, success rate, avg latency."""
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)

        p_tokens, c_tokens, tot_tokens, tot_cost, is_exceeded = await cls.get_current_month_usage(db)

        # Count total requests and success count this month
        stats_stmt = select(
            func.count(AIUsageLog.id),
            func.count(AIUsageLog.id).filter(AIUsageLog.status == "SUCCESS"),
            func.count(AIUsageLog.id).filter(AIUsageLog.status.in_(["FAILED", "TIMEOUT", "BUDGET_EXCEEDED"])),
            func.coalesce(func.avg(AIUsageLog.latency_ms), 0)
        ).where(AIUsageLog.created_at >= start_of_month)

        stats_res = await db.execute(stats_stmt)
        stats_row = stats_res.one()

        tot_requests = int(stats_row[0] or 0)
        success_count = int(stats_row[1] or 0)
        failure_count = int(stats_row[2] or 0)
        avg_latency = int(float(stats_row[3] or 0))

        return {
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "total_tokens": tot_tokens,
            "total_cost_usd": round(tot_cost, 6),
            "is_budget_exceeded": is_exceeded,
            "total_requests": tot_requests,
            "success_count": success_count,
            "failure_count": failure_count,
            "average_latency_ms": avg_latency
        }

    @classmethod
    async def get_recent_logs(
        cls,
        db: AsyncSession,
        limit: int = 50,
        status: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> List[AIUsageLog]:
        """Retrieves recent AI usage and telemetry records."""
        stmt = select(AIUsageLog).order_by(desc(AIUsageLog.created_at))
        if status and status.upper() != "ALL":
            stmt = stmt.where(AIUsageLog.status == status.upper())
        if task_type and task_type.upper() != "ALL":
            stmt = stmt.where(AIUsageLog.task_type == task_type.upper())
        stmt = stmt.limit(min(limit, 200))

        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def log_usage(
        cls,
        db: AsyncSession,
        provider: str,
        model: str,
        task_type: str,
        prompt_tokens: int,
        completion_tokens: int,
        status: str,
        latency_ms: int,
        error_message: Optional[str] = None
    ) -> AIUsageLog:
        """Records an execution event and token cost in ai_usage_logs."""
        cfg = runtime_manager.get_config()
        # If local mode or mock, cost is zero
        if cfg.runtime_mode == "local" or provider.lower() in ["mock", "ollama"]:
            est_cost = Decimal("0.0")
        else:
            prompt_cost = (prompt_tokens / 1000.0) * settings.AI_COST_PER_1K_PROMPT_USD
            completion_cost = (completion_tokens / 1000.0) * settings.AI_COST_PER_1K_COMPLETION_USD
            est_cost = Decimal(str(round(prompt_cost + completion_cost, 6)))

        usage_log = AIUsageLog(
            provider=provider,
            model=model,
            task_type=task_type,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=est_cost,
            status=status,
            error_message=error_message,
            latency_ms=latency_ms
        )
        db.add(usage_log)
        await db.commit()
        await db.refresh(usage_log)
        return usage_log

    @classmethod
    async def execute_guarded(
        cls,
        db: AsyncSession,
        task_type: str,
        execute_fn: Callable[[], Any],
        fallback_fn: Optional[Callable[[], Any]] = None
    ) -> Tuple[Optional[Any], str, Optional[str]]:
        """Executes an AI task under strict budget, rate limit, and timeout guardrails.
        Returns: (result_data, status_code, diagnostic_message)
        Possible status_codes: COMPLETED, BUDGET_EXCEEDED, AI_UNAVAILABLE, DISABLED, FALLBACK
        """
        cfg = runtime_manager.get_config()

        if not cfg.ai_enabled:
            return None, "DISABLED", "Layanan AI dinonaktifkan dalam konfigurasi sistem."

        # Check monthly budget cap if in API mode
        if cfg.runtime_mode == "api":
            _, _, _, current_cost, is_exceeded = await cls.get_current_month_usage(db)
            if is_exceeded:
                msg = (
                    f"Batas anggaran AI bulanan (${cfg.monthly_budget_usd:.2f} USD) telah tercapai. "
                    f"Biaya kumulatif bulan ini: ${current_cost:.4f} USD."
                )
                if cfg.auto_fallback_to_local and fallback_fn:
                    logger.warning(f"Budget exceeded, triggering auto-fallback to local engine for {task_type}")
                    await cls.log_usage(
                        db=db,
                        provider=cfg.provider,
                        model=cfg.model,
                        task_type=task_type,
                        prompt_tokens=0,
                        completion_tokens=0,
                        status="BUDGET_EXCEEDED",
                        latency_ms=0,
                        error_message=msg
                    )
                    fb_res, p_tok, c_tok, lat_ms = await fallback_fn()
                    await cls.log_usage(
                        db=db,
                        provider="mock",
                        model="mock-rule-engine",
                        task_type=task_type,
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        status="FALLBACK",
                        latency_ms=lat_ms,
                        error_message="Fallback otomatis ke mesin aturan lokal karena batas anggaran cloud tercapai."
                    )
                    return fb_res, "COMPLETED", msg + " (Beralih ke mesin aturan lokal)"
                else:
                    await cls.log_usage(
                        db=db,
                        provider=cfg.provider,
                        model=cfg.model,
                        task_type=task_type,
                        prompt_tokens=0,
                        completion_tokens=0,
                        status="BUDGET_EXCEEDED",
                        latency_ms=0,
                        error_message=msg + " Sistem beralih ke verifikasi manual."
                    )
                    return None, "BUDGET_EXCEEDED", msg + " Silakan gunakan verifikasi manual."

        try:
            result, p_tokens, c_tokens, latency_ms = await execute_fn()

            await cls.log_usage(
                db=db,
                provider=cfg.provider,
                model=cfg.model,
                task_type=task_type,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                status="SUCCESS",
                latency_ms=latency_ms
            )
            return result, "COMPLETED", None

        except httpx.TimeoutException as exc:
            msg = f"Layanan AI mengalami batas waktu respon ({cfg.timeout_seconds} detik)."
            logger.warning(f"AI timeout in task {task_type}: {exc}")
            await cls.log_usage(
                db=db,
                provider=cfg.provider,
                model=cfg.model,
                task_type=task_type,
                prompt_tokens=0,
                completion_tokens=0,
                status="TIMEOUT",
                latency_ms=cfg.timeout_seconds * 1000,
                error_message=str(exc)
            )

            if cfg.auto_fallback_to_local and fallback_fn:
                logger.info(f"Triggering auto-fallback to local engine for timeout in {task_type}")
                fb_res, p_tok, c_tok, lat_ms = await fallback_fn()
                await cls.log_usage(
                    db=db,
                    provider="mock",
                    model="mock-rule-engine",
                    task_type=task_type,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    status="FALLBACK",
                    latency_ms=lat_ms,
                    error_message="Fallback otomatis ke mesin aturan lokal akibat timeout pada provider cloud."
                )
                return fb_res, "COMPLETED", msg + " (Beralih ke mesin aturan lokal)"

            return None, "AI_UNAVAILABLE", msg + " Beralih ke verifikasi manual."

        except (httpx.ConnectError, httpx.HTTPStatusError, Exception) as exc:
            detail = ""
            if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                try:
                    detail = f" (Respon server: {exc.response.text})"
                except Exception:
                    pass
            msg = f"Layanan AI tidak dapat dihubungi atau mengalami kegagalan: {str(exc)}{detail}."
            logger.warning(f"AI failure in task {task_type}: {exc}{detail}")
            await cls.log_usage(
                db=db,
                provider=cfg.provider,
                model=cfg.model,
                task_type=task_type,
                prompt_tokens=0,
                completion_tokens=0,
                status="FAILED",
                latency_ms=0,
                error_message=f"{str(exc)}{detail}"
            )

            if cfg.auto_fallback_to_local and fallback_fn:
                logger.info(f"Triggering auto-fallback to local engine for failure in {task_type}")
                fb_res, p_tok, c_tok, lat_ms = await fallback_fn()
                await cls.log_usage(
                    db=db,
                    provider="mock",
                    model="mock-rule-engine",
                    task_type=task_type,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    status="FALLBACK",
                    latency_ms=lat_ms,
                    error_message=f"Fallback otomatis ke mesin aturan lokal akibat kegagalan provider ({str(exc)})."
                )
                return fb_res, "COMPLETED", msg + " (Beralih ke mesin aturan lokal)"

            return None, "AI_UNAVAILABLE", msg + " Beralih ke verifikasi manual."
