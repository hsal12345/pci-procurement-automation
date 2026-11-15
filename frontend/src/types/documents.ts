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
  drive_file_id?: string | null;
  drive_web_view_link?: string | null;
  drive_synced_at?: string | null;
  created_at: string;
  download_url?: string | null;
}

export interface ArchiveRecord {
  id: string;
  package_id: string;
  revision_id: string;
  target_provider: string;
  folder_path: string;
  drive_folder_id?: string | null;
  drive_folder_url?: string | null;
  status: "PENDING" | "SYNCING" | "SYNCED" | "FAILED" | "SUPERSEDED";
  progress_percent: number;
  current_step?: string | null;
  uploaded_files: number;
  total_files: number;
  total_bytes: number;
  attempt_count: number;
  last_error?: string | null;
  last_attempt_at?: string | null;
  synced_at?: string | null;
  created_at: string;
  revision_number?: number | null;
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
