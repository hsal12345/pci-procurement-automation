from sqlalchemy import Column, String, Integer, Numeric, Text
from app.models.base import BaseModel


class AIUsageLog(BaseModel):
    """Tracks token consumption, estimated costs, latency, and status
    for all outbound AI requests under the monthly budget cap guard.
    """
    __tablename__ = "ai_usage_logs"

    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False)
    task_type = Column(String(50), nullable=False, index=True)  # MAPPING_ASSISTANT, DISCREPANCY_AUDITOR
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    estimated_cost_usd = Column(Numeric(10, 6), default=0.0, nullable=False)
    status = Column(String(32), default="SUCCESS", nullable=False, index=True)  # SUCCESS, BUDGET_EXCEEDED, TIMEOUT, FAILED, FALLBACK
    error_message = Column(Text, nullable=True)
    latency_ms = Column(Integer, default=0, nullable=False)
