export interface SemanticDiscrepancyItem {
  sheet_code: string;
  item_number: number;
  item_description_a: string;
  item_description_b: string;
  discrepancy_type: "BRAND_SUBSTITUTION" | "SPEC_CONTRADICTION" | "UNIT_MISMATCH" | "SUSPECT_ANOMALY";
  severity: "WARNING" | "INFO";
  explanation: string;
  recommended_action: string;
}

export interface SemanticAuditResponse {
  revision_id: string;
  status: "COMPLETED" | "FAILED" | "BUDGET_EXCEEDED" | "DISABLED";
  findings_count: number;
  findings: SemanticDiscrepancyItem[];
  summary: string;
}

export interface CandidateMappingProposal {
  sheet_name: string;
  header_row_index: number;
  column_mapping: Record<string, number>;
  confidence_score: number;
  reasoning?: string;
  is_ambiguous: boolean;
}

export interface AIUsageResponse {
  current_month?: string;
  year_month?: string;
  provider: string;
  model?: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_prompt_tokens?: number;
  total_completion_tokens?: number;
  total_tokens: number;
  total_cost_usd: number;
  monthly_budget_usd?: number;
  budget_cap_usd?: number;
  remaining_budget_usd?: number;
  budget_remaining_usd?: number;
  is_budget_exceeded: boolean;
  service_status?: string;
}

