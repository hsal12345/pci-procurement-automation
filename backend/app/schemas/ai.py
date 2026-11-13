from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CandidateMappingProposal(BaseModel):
    """Structured proposal for spreadsheet header row index and column positions."""
    sheet_name: Optional[str] = Field(None, description="Target worksheet name analyzed.")
    column_mapping: Dict[str, int] = Field(
        ...,
        description="Dictionary mapping canonical line attributes (line_no, description, specification, quantity, unit, hps_price, offer_price, final_price) to 1-indexed column indices."
    )
    header_row_index: int = Field(..., description="1-indexed row number where table column headers are located.")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0.")
    reasoning: str = Field(..., description="Detailed rationale explaining why this header and column mapping was inferred.")
    is_ambiguous: bool = Field(False, description="Flagged true if confidence_score < 0.80, requiring mandatory manual review.")


class AIMappingSuggestRequest(BaseModel):
    """Optional request parameters when requesting AI column mapping suggestion."""
    sheet_name: Optional[str] = Field(None, description="Specific worksheet name to analyze; defaults to active/first sheet.")


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


class DocumentSemanticScoreItem(BaseModel):
    """Percentage semantic evaluation for a single SPJ procurement document (D01-D13)."""
    doc_code: str = Field(..., description="Canonical document code (D01..D13).")
    doc_name: str = Field(..., description="Document title.")
    score_percentage: float = Field(..., ge=0.0, le=100.0, description="Consistency percentage (0-100).")
    passed: bool = Field(True, description="True if score_percentage >= passing_grade.")
    issues_count: int = Field(0, description="Number of semantic/textual issues affecting this document.")
    notes: str = Field("", description="Brief Indonesian assessment note for this document.")


class SemanticAuditRequest(BaseModel):
    """Optional request parameters for AI semantic audit."""
    passing_grade: float = Field(
        95.0,
        ge=0.0,
        le=100.0,
        description="Minimum percentage passing grade required across documents (default 95%)."
    )


class UpdatePassingGradeRequest(BaseModel):
    """Request payload to adjust the passing grade threshold on the latest audit report."""
    passing_grade: float = Field(..., ge=0.0, le=100.0, description="Adjusted passing grade percentage (0-100).")


class SemanticAuditResponse(BaseModel):
    """Result of cross-document semantic discrepancy audit on a package revision."""
    revision_id: UUID
    run_id: Optional[UUID] = None
    status: str  # COMPLETED, BUDGET_EXCEEDED, AI_UNAVAILABLE, MANUAL_REVIEW_RECORDED
    findings_count: int = 0
    findings: List[SemanticDiscrepancyItem] = []
    overall_score: float = Field(100.0, ge=0.0, le=100.0, description="Overall semantic consistency score percentage across all documents.")
    passing_grade: float = Field(95.0, ge=0.0, le=100.0, description="Active passing grade threshold percentage.")
    passed: bool = Field(True, description="True if overall_score >= passing_grade.")
    document_scores: List[DocumentSemanticScoreItem] = Field(default_factory=list, description="Per-document percentage judgment across D01-D13.")
    summary: str


class AIUsageResponse(BaseModel):
    """Metrics for AI token usage, cumulative costs, and remaining budget for current calendar month."""
    current_month: str
    year_month: Optional[str] = None
    runtime_mode: Optional[str] = "local"
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
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_latency_ms: int = 0


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


# =========================================================================
# New Schemas for AI & Audit Usage Runtime Selection & Supporting Features
# =========================================================================

class AIRuntimeConfigResponse(BaseModel):
    runtime_mode: str = Field(..., description="'api' or 'local'")
    provider: str = Field(..., description="gemini, openrouter, openai, deepseek, ollama, mock, custom")
    base_url: str
    model: str
    has_api_key: bool
    api_key_masked: str
    timeout_seconds: int
    monthly_budget_usd: float
    auto_fallback_to_local: bool
    ai_enabled: bool
    available_models: Dict[str, List[str]] = Field(default_factory=dict)


class AIRuntimeConfigUpdateRequest(BaseModel):
    runtime_mode: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    timeout_seconds: Optional[int] = None
    monthly_budget_usd: Optional[float] = None
    auto_fallback_to_local: Optional[bool] = None
    ai_enabled: Optional[bool] = None


class AITestConnectionRequest(BaseModel):
    runtime_mode: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    timeout_seconds: Optional[int] = None


class AITestConnectionResponse(BaseModel):
    status: str  # ONLINE, OFFLINE, DEGRADED, ERROR
    latency_ms: int
    runtime_mode: str
    provider: str
    model: str
    endpoint: str
    message: str
    is_fallback: bool = False


class AIUsageLogItem(BaseModel):
    id: str
    created_at: str
    provider: str
    model: str
    task_type: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    status: str
    latency_ms: int
    error_message: Optional[str] = None


class AIPlaygroundTestRequest(BaseModel):
    test_type: str = Field("DISCREPANCY", description="'DISCREPANCY' or 'MAPPING'")
    text_a: Optional[str] = Field("Pembersih Porselen Botol 1 Liter", description="Item text A (e.g. from HPS)")
    text_b: Optional[str] = Field("Porstex Pembersih Keramik 1000ml", description="Item text B (e.g. from Pesanan/Faktur)")
    sample_headers: Optional[List[str]] = Field(None, description="Sample table headers for mapping test")


class AIPlaygroundTestResponse(BaseModel):
    test_type: str
    runtime_mode: str
    provider: str
    model: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    output: Any
    summary: str


# =========================================================================
# System Knowledge Chat Schemas (PRD FR05 & Navigation Assistant)
# =========================================================================

class SystemKnowledgeRouteItem(BaseModel):
    title: str = Field(..., description="Judul menu atau halaman navigasi")
    path: str = Field(..., description="Path URL internal (misal: /packages, /imports)")
    description: Optional[str] = Field(None, description="Keterangan singkat fungsi halaman")


class SystemKnowledgeChatMessage(BaseModel):
    role: str = Field(..., description="'user' atau 'assistant'")
    content: str = Field(..., description="Isi teks pesan")


class SystemKnowledgeChatRequest(BaseModel):
    message: str = Field(..., description="Pertanyaan pengguna terkait sistem atau navigasi")
    history: Optional[List[SystemKnowledgeChatMessage]] = Field(
        default_factory=list,
        description="Riwayat percakapan sebelumnya untuk konteks multi-turn"
    )


class SystemKnowledgeChatResult(BaseModel):
    """Structured LLM output for system knowledge and navigation chat."""
    reply: str = Field(
        ...,
        description="Jawaban lengkap dan panduan navigasi terstruktur dalam format Markdown berbahasa Indonesia."
    )
    suggested_routes: List[SystemKnowledgeRouteItem] = Field(
        default_factory=list,
        description="Daftar tautan rute halaman sistem yang relevan untuk dikunjungi pengguna."
    )
    suggested_questions: List[str] = Field(
        default_factory=list,
        description="2-4 pertanyaan lanjutan yang relevan untuk memperdalam pemahaman pengguna."
    )


class SystemKnowledgeChatResponse(BaseModel):
    """API Response payload delivered to the frontend chat UI."""
    reply: str
    suggested_routes: List[SystemKnowledgeRouteItem] = []
    suggested_questions: List[str] = []
    runtime_mode: str
    provider: str
    model: str
    tokens_used: int = 0
    latency_ms: int = 0


class SystemKnowledgeInfoResponse(BaseModel):
    """Metadata and raw text content of the system knowledge base markdown file."""
    title: str
    filename: str
    last_updated: str
    content: str
    size_bytes: int
    sections: List[str] = []


# =========================================================================
# AI Auto-Fix Recommendation & Apply Schemas (5. Pemeriksaan Sistem)
# =========================================================================

class AIFixReasoningStep(BaseModel):
    """Single step in the AI reasoning chain while diagnosing revision issues."""
    step_number: int
    title: str
    detail: str
    status: str = "COMPLETED"


class AIFixChangeItem(BaseModel):
    """Proposed atomic fix to a field, document event, document number, line item, or snapshot."""
    fix_id: str
    category: str  # IDENTITY, OFFICIALS, TAX_POLICY, DATES, DOC_NUMBERS, ITEMS_TEXT, ITEMS_PRICING, TOTALS, LOGISTICS
    rule_code: str  # BR01..BR15, AI_SEMANTIC
    target_tab: str  # identity, items, dates, logistics
    field_path: str
    field_label: str
    current_value_display: str
    proposed_value_display: str
    proposed_value_json: Any
    reasoning: str
    severity_resolved: str = "BLOCK"


class AIFixRecommendationResponse(BaseModel):
    """Structured AI auto-fix proposal with reasoning steps and reviewable changes."""
    revision_id: UUID
    status: str  # COMPLETED, NO_ISSUES, BUDGET_EXCEEDED, DISABLED, FAILED
    provider: str = "mock"
    model: str = "mock-rule-engine"
    reasoning_steps: List[AIFixReasoningStep] = Field(default_factory=list)
    changes: List[AIFixChangeItem] = Field(default_factory=list)
    summary: str
    findings_before_count: int = 0
    estimated_resolved_count: int = 0


class AIFixApplyRequest(BaseModel):
    """User-reviewed and approved list of AI fix changes to apply to the revision."""
    expected_version: int
    changes: List[AIFixChangeItem] = Field(default_factory=list)


class AIFixApplyResponse(BaseModel):
    """Confirmation and fresh validation summary after applying AI fixes."""
    revision_id: UUID
    new_version: int
    applied_count: int
    validation_passed: bool
    remaining_errors: int
    remaining_warnings: int
    message: str

