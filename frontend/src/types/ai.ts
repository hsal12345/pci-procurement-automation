export interface SemanticDiscrepancyItem {
  sheet_code?: string;
  sheet_a?: string;
  sheet_b?: string;
  item_number?: number;
  line_number?: number;
  item_name?: string;
  item_description_a?: string;
  item_description_b?: string;
  discrepancy_type: "BRAND_SUBSTITUTION" | "SPEC_CONTRADICTION" | "SPECIFICATION_MISMATCH" | "UNIT_MISMATCH" | "UNIT_INCOMPATIBILITY" | "SUSPECT_ANOMALY" | "NAMING_VARIATION";
  severity: "WARNING" | "INFO";
  explanation?: string;
  message?: string;
  recommended_action: string;
}

export interface SemanticAuditResponse {
  revision_id: string;
  run_id?: string;
  status: "COMPLETED" | "FAILED" | "BUDGET_EXCEEDED" | "DISABLED" | "FALLBACK";
  findings_count: number;
  findings: SemanticDiscrepancyItem[];
  summary: string;
}

export interface CandidateMappingProposal {
  sheet_name?: string;
  header_row_index: number;
  column_mapping: Record<string, number>;
  confidence_score: number;
  reasoning?: string;
  is_ambiguous: boolean;
}

export interface AIUsageResponse {
  current_month?: string;
  year_month?: string;
  runtime_mode?: "api" | "local" | string;
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
  total_requests?: number;
  success_count?: number;
  failure_count?: number;
  average_latency_ms?: number;
}

export interface AIRuntimeConfig {
  runtime_mode: "api" | "local";
  provider: "gemini" | "openrouter" | "openai" | "ollama" | "mock" | "custom" | string;
  base_url: string;
  model: string;
  has_api_key: boolean;
  api_key_masked: string;
  timeout_seconds: number;
  monthly_budget_usd: number;
  auto_fallback_to_local: boolean;
  ai_enabled: boolean;
  available_models?: Record<string, string[]>;
}

export interface AIRuntimeConfigUpdate {
  runtime_mode?: "api" | "local";
  provider?: string;
  base_url?: string;
  api_key?: string;
  model?: string;
  timeout_seconds?: number;
  monthly_budget_usd?: number;
  auto_fallback_to_local?: boolean;
  ai_enabled?: boolean;
}

export interface AITestConnectionRequest {
  runtime_mode?: string;
  provider?: string;
  base_url?: string;
  api_key?: string;
  model?: string;
  timeout_seconds?: number;
}

export interface AITestConnectionResponse {
  status: "ONLINE" | "OFFLINE" | "DEGRADED" | "ERROR";
  latency_ms: number;
  runtime_mode: string;
  provider: string;
  model: string;
  endpoint: string;
  message: string;
  is_fallback?: boolean;
}

export interface AIUsageLogItem {
  id: string;
  created_at: string;
  provider: string;
  model: string;
  task_type: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  status: "SUCCESS" | "FAILED" | "TIMEOUT" | "BUDGET_EXCEEDED" | "FALLBACK" | string;
  latency_ms: number;
  error_message?: string;
}

export interface AIPlaygroundTestRequest {
  test_type: "DISCREPANCY" | "MAPPING";
  text_a?: string;
  text_b?: string;
  sample_headers?: string[];
}

export interface AIPlaygroundTestResponse {
  test_type: string;
  runtime_mode: string;
  provider: string;
  model: string;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  output: any;
  summary: string;
}

export interface SystemKnowledgeRouteItem {
  title: string;
  path: string;
  description?: string;
}

export interface SystemKnowledgeChatMessage {
  role: "user" | "assistant";
  content: string;
  suggested_routes?: SystemKnowledgeRouteItem[];
  suggested_questions?: string[];
  timestamp?: string;
}

export interface SystemKnowledgeChatRequest {
  message: string;
  history?: { role: "user" | "assistant"; content: string }[];
}

export interface SystemKnowledgeChatResponse {
  reply: string;
  suggested_routes: SystemKnowledgeRouteItem[];
  suggested_questions: string[];
  runtime_mode: string;
  provider: string;
  model: string;
  tokens_used: number;
  latency_ms: number;
}

export interface SystemKnowledgeInfoResponse {
  title: string;
  filename: string;
  last_updated: string;
  content: string;
  size_bytes: number;
  sections: string[];
}

