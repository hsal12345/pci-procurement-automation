import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Optional, Tuple, TypeVar
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config import settings
from app.models.ai import AIUsageLog

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

        is_exceeded = tot_cost >= settings.AI_MONTHLY_BUDGET_USD
        return p_tokens, c_tokens, t_tokens, tot_cost, is_exceeded

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
        # Calculate cost
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
        execute_fn: Callable[[], Any]
    ) -> Tuple[Optional[Any], str, Optional[str]]:
        """Executes an AI task under strict budget, rate limit, and timeout guardrails.
        Returns: (result_data, status_code, diagnostic_message)
        Possible status_codes: COMPLETED, BUDGET_EXCEEDED, AI_UNAVAILABLE, DISABLED
        """
        if not settings.AI_ENABLED:
            return None, "DISABLED", "Layanan AI dinonaktifkan dalam konfigurasi sistem."

        # Check monthly budget cap
        _, _, _, current_cost, is_exceeded = await cls.get_current_month_usage(db)
        if is_exceeded:
            msg = (
                f"Batas anggaran AI bulanan (${settings.AI_MONTHLY_BUDGET_USD:.2f} USD) telah tercapai. "
                f"Biaya kumulatif bulan ini: ${current_cost:.4f} USD. Sistem beralih ke verifikasi manual."
            )
            await cls.log_usage(
                db=db,
                provider=settings.AI_PROVIDER,
                model=settings.AI_MODEL,
                task_type=task_type,
                prompt_tokens=0,
                completion_tokens=0,
                status="BUDGET_EXCEEDED",
                latency_ms=0,
                error_message=msg
            )
            return None, "BUDGET_EXCEEDED", msg

        try:
            result, p_tokens, c_tokens, latency_ms = await execute_fn()

            await cls.log_usage(
                db=db,
                provider=settings.AI_PROVIDER,
                model=settings.AI_MODEL,
                task_type=task_type,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                status="SUCCESS",
                latency_ms=latency_ms
            )
            return result, "COMPLETED", None

        except httpx.TimeoutException as exc:
            msg = f"Layanan AI mengalami batas waktu respon ({settings.AI_REQUEST_TIMEOUT_SECONDS} detik). Beralih ke verifikasi manual."
            logger.warning(f"AI timeout in task {task_type}: {exc}")
            await cls.log_usage(
                db=db,
                provider=settings.AI_PROVIDER,
                model=settings.AI_MODEL,
                task_type=task_type,
                prompt_tokens=0,
                completion_tokens=0,
                status="TIMEOUT",
                latency_ms=settings.AI_REQUEST_TIMEOUT_SECONDS * 1000,
                error_message=str(exc)
            )
            return None, "AI_UNAVAILABLE", msg

        except (httpx.ConnectError, httpx.HTTPStatusError, Exception) as exc:
            msg = f"Layanan AI tidak dapat dihubungi atau mengalami kegagalan: {str(exc)}. Beralih ke verifikasi manual."
            logger.warning(f"AI failure in task {task_type}: {exc}")
            await cls.log_usage(
                db=db,
                provider=settings.AI_PROVIDER,
                model=settings.AI_MODEL,
                task_type=task_type,
                prompt_tokens=0,
                completion_tokens=0,
                status="FAILED",
                latency_ms=0,
                error_message=str(exc)
            )
            return None, "AI_UNAVAILABLE", msg
