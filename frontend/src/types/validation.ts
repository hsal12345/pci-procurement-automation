export type FindingSeverity = "BLOCK" | "WARNING" | "INFO";

export interface Finding {
  id: string;
  run_id?: string;
  rule_code: string;
  severity: FindingSeverity;
  sheet_name?: string | null;
  cell_coordinate?: string | null;
  current_value?: string | null;
  expected_value?: string | null;
  message: string;
  disposition_status?: "OPEN" | "DISPOSITIONED" | "SUPERSEDED";
  disposition_notes?: string | null;
  disposition_actor?: string | null;
  created_at?: string;
}

export interface ValidationRun {
  id: string;
  revision_id: string;
  is_valid: boolean;
  error_count: number;
  warning_count: number;
  info_count: number;
  findings: Finding[];
  executed_at?: string;
}
