export interface Artifact {
  id: string;
  revision_id: string;
  doc_code: string;
  format: "XLSX" | "DOCX" | "PDF" | "ZIP" | "JSON";
  file_name: string;
  file_path: string;
  file_size_bytes: number;
  sha256_hash: string;
  created_at: string;
}

export interface GenerationJob {
  id: string;
  revision_id: string;
  status: "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED";
  progress_percent: number;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}
