export interface Artifact {
  id: string;
  job_id?: string | null;
  revision_id: string;
  doc_code: string;
  format: "XLSX" | "DOCX" | "PDF" | "ZIP" | "JSON";
  filename: string;
  file_name?: string;
  file_path?: string;
  file_size: number;
  file_size_bytes?: number;
  sha256_hash: string;
  is_draft?: boolean;
  archive_status?: string;
  created_at: string;
  download_url?: string | null;
}

export interface GenerationJob {
  id: string;
  revision_id: string;
  status: "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED" | "CANCELLED";
  progress_percent: number;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at?: string;
}
