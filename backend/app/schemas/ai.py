from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CandidateMappingProposal(BaseModel):
    """Structured proposal for spreadsheet header row index and column positions."""
    column_mapping: Dict[str, int] = Field(
        ...,
        description="Dictionary mapping canonical line attributes (line_no, description, specification, quantity, unit, hps_price, offer_price, final_price) to 1-indexed column indices."
    )
    header_row_index: int = Field(..., description="1-indexed row number where table column headers are located.")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0.")
    reasoning: str = Field(..., description="Detailed rationale explaining why this header and column mapping was inferred.")
    is_ambiguous: bool = Field(False, description="Flagged true if confidence_score < 0.80, requiring mandatory manual review.")


class SemanticDiscrepancyItem(BaseModel):
    """Discrepancy finding between document sheets or line specifications."""
    sheet_a: str = Field(..., description="First sheet or document code where item was observed (e.g. D01/HPS).")
    sheet_b: str = Field(..., description="Second sheet or document code compared (e.g. D05/Surat Pesanan).")
    line_number: Optional[int] = Field(None, description="Affected line item number if identifiable.")
    item_name: str = Field(..., description="Item description under inspection.")
    discrepancy_type: str = Field(..., description="Category: BRAND_SUBSTITUTION, SPECIFICATION_MISMATCH, UNIT_INCOMPATIBILITY, NAMING_VARIATION.")
    severity: str = Field("WARNING", description="Finding severity: WARNING or INFO.")
    message: str = Field(..., description="Human-readable description of the semantic difference.")
    recommended_action: str = Field(..., description="Actionable recommendation for procurement staff.")


class SemanticAuditResponse(BaseModel):
    """Result of cross-document semantic discrepancy audit on a package revision."""
    revision_id: UUID
    run_id: Optional[UUID] = None
    status: str  # COMPLETED, BUDGET_EXCEEDED, AI_UNAVAILABLE, MANUAL_REVIEW_RECORDED
    findings_count: int = 0
    findings: List[SemanticDiscrepancyItem] = []
    summary: str


class AIUsageResponse(BaseModel):
    """Metrics for AI token usage, cumulative costs, and remaining budget for current calendar month."""
    current_month: str
    year_month: Optional[str] = None
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_prompt_tokens: Optional[int] = None
    total_completion_tokens: Optional[int] = None
    total_tokens: int
    total_cost_usd: float
    monthly_budget_usd: float
    budget_cap_usd: Optional[float] = None
    remaining_budget_usd: float
    budget_remaining_usd: Optional[float] = None
    is_budget_exceeded: bool
    service_status: str  # ACTIVE, BUDGET_EXCEEDED, DISABLED


class ManualReviewRecordRequest(BaseModel):
    """Request payload to record that human manual review was performed."""
    reviewer_name: Optional[str] = "Petugas Administrasi"
    verifier_name: Optional[str] = None
    reason: Optional[str] = None
    verification_notes: Optional[str] = None
    notes: Optional[str] = None



class ManualReviewRecordResponse(BaseModel):
    """Confirmation response after recording manual review."""
    revision_id: UUID
    ai_review_status: str
    recorded_at: str
    recorded_by: str
    message: str
