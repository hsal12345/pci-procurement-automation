export interface DiscrepancyItem {
  sheet_name: string;
  cell_coordinate?: string | null;
  rule_category: string;
  severity: "BLOCK" | "WARNING" | string;
  field: string;
  found_value: any;
  expected_or_note: string;
}

export interface CandidateLineItem {
  line_number: number;
  original_description: string;
  confirmed_description: string;
  specification?: string | null;
  quantity: number;
  unit: string;
  hps_unit_price: number;
  hps_price?: number;
  offer_unit_price: number;
  final_unit_price: number;
  discount: number;
  line_total: number;
  condition: string;
  raw_formula?: string | null;
}

export interface ImportProgressEventItem {
  timestamp: string;
  elapsed_ms: number;
  stage: "UPLOAD" | "EXTRACT_VALIDATE" | "PREPARE_CONTEXT" | "LLM_INFERENCE" | "FINALIZE" | string;
  percent: number;
  label: string;
  detail: string;
  status: string;
}

export interface ImportProgressState {
  import_id: string;
  stage: "UPLOAD" | "EXTRACT_VALIDATE" | "PREPARE_CONTEXT" | "LLM_INFERENCE" | "FINALIZE" | string;
  stage_index: number;
  total_stages: number;
  percent: number;
  label: string;
  detail: string;
  status: "IDLE" | "RUNNING" | "COMPLETED" | "AMBIGUOUS" | "FALLBACK" | "FAILED" | string;
  source_format?: string | null;
  provider?: string | null;
  model?: string | null;
  runtime_mode?: string | null;
  extracted_stats?: Record<string, any>;
  elapsed_ms: number;
  updated_at?: string;
  events: ImportProgressEventItem[];
  result?: {
    sheet_name?: string | null;
    header_row_index: number;
    column_mapping: Record<string, number>;
    confidence_score: number;
    reasoning?: string;
    is_ambiguous: boolean;
    detected_school_name?: string | null;
    detected_fiscal_year?: number | null;
    detected_quarter?: number | null;
  } | null;
  error?: string | null;
}

export interface ImportUploadResponse {
  import_id: string;
  filename: string;
  file_hash: string;
  file_size: number;
  status: string;
  source_format?: string;
  sheet_names: string[];
  active_sheet?: string | null;
  extraction_stats?: Record<string, any>;
  message: string;
}

export interface ImportPreviewResponse {
  import_id: string;
  filename: string;
  file_hash?: string | null;
  status: string;
  source_format?: string;
  sheet_names: string[];
  active_sheet: string;
  raw_preview_rows: any[][];
  header_row_index?: number | null;
  detected_mapping: Record<string, number>;
  ai_proposal?: {
    sheet_name?: string | null;
    header_row_index: number;
    column_mapping: Record<string, number>;
    confidence_score: number;
    reasoning?: string;
    is_ambiguous: boolean;
    detected_school_name?: string | null;
    detected_fiscal_year?: number | null;
    detected_quarter?: number | null;
  } | null;
  ai_status?: string | null;
  ai_error?: string | null;
  upload_context: Record<string, any>;
  document_context?: {
    source_format?: string;
    snippets?: string[];
    section_contexts?: Record<string, string[]>;
  };
  extraction_stats?: Record<string, any>;
  progress?: ImportProgressState | null;
  school_candidate: Record<string, any>;
  transaction_metadata: Record<string, any>;
  candidate_lines: CandidateLineItem[];
  events_candidate: Array<{
    event_code: string;
    event_date: string;
    day_name_id?: string;
  }>;
  detected_discrepancies: DiscrepancyItem[];
  can_proceed_to_confirm: boolean;
}

export interface ImportReparseRequest {
  sheet_name?: string;
  header_row_index?: number;
  column_mapping: Record<string, number>;
  mapping_source: "AI" | "AI_EDITED" | "MANUAL_FALLBACK";
}

export interface ImportConfirmRequest {
  school_id?: string | null;
  fiscal_year?: number;
  quarter?: number;
  sheet_name?: string;
  header_row_index?: number;
  column_mapping?: Record<string, number>;
  mapping_source?: string;
  confirmed_lines?: CandidateLineItem[];
  confirmed_events?: Array<{
    event_code: string;
    event_date: string;
    day_name_id?: string;
  }>;
  funding_source_code?: string;
  notes?: string;
}

export interface ImportConfirmResponse {
  message: string;
  import_id: string;
  file_hash: string;
  package_id: string;
  package_number: string;
  revision_id: string;
  revision_number: number;
  mapping_source: string;
  catalog_matched_count: number;
  subtotal: number;
  tax_total: number;
  grand_total: number;
  terbilang: string;
}
