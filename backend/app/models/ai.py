from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, Numeric, String, Text
from app.models.base import BaseModel, GUID


class AIUsageLog(BaseModel):
    """Tracks token consumption, estimated costs, latency, and status
    for all outbound AI requests under the monthly budget cap guard.
    """
    __tablename__ = "ai_usage_logs"

    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False)
    task_type = Column(String(50), nullable=False, index=True)  # MAPPING_ASSISTANT, DISCREPANCY_AUDITOR, AUTO_FIX
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    estimated_cost_usd = Column(Numeric(10, 6), default=0.0, nullable=False)
    status = Column(String(32), default="SUCCESS", nullable=False, index=True)  # SUCCESS, BUDGET_EXCEEDED, TIMEOUT, FAILED, FALLBACK
    error_message = Column(Text, nullable=True)
    latency_ms = Column(Integer, default=0, nullable=False)


class AISemanticAuditReport(BaseModel):
    """Persists percentage-based semantic audit evaluation across all 13 documents (D01-D13)
    along with the user-adjustable passing grade threshold (default 95%).
    """
    __tablename__ = "ai_semantic_audit_reports"

    revision_id = Column(GUID, ForeignKey("package_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(GUID, nullable=True)
    passing_grade = Column(Numeric(5, 2), default=95.0, nullable=False)
    overall_score = Column(Numeric(5, 2), default=100.0, nullable=False)
    passed = Column(Boolean, default=True, nullable=False)
    findings_count = Column(Integer, default=0, nullable=False)
    document_scores = Column(JSON, nullable=False, default=list)
    findings = Column(JSON, nullable=False, default=list)
    summary = Column(Text, nullable=False, default="")
    evaluated_by = Column(String(100), nullable=True)
