export interface EvidenceAttachment {
  id: string;
  logistics_record_id: string;
  original_filename: string;
  storage_path: string;
  content_type: string;
  file_size_bytes: number;
  sha256_hash: string;
  uploaded_at: string;
}

export interface LogisticsRecord {
  id: string;
  revision_id: string;
  courier_name?: string | null;
  vehicle_plate?: string | null;
  delivery_reference?: string | null;
  tracking_number?: string | null;
  dispatch_date?: string | null;
  receipt_date?: string | null;
  actual_delivery_date?: string | null;
  recipient_name?: string | null;
  delivery_status: "PENDING" | "DELIVERED" | "DISPUTED";
  is_delivery_confirmed: boolean;
  inspection_status?: string | null;
  inspection_notes?: string | null;
  inspected_by?: string | null;
  inspected_at?: string | null;
  notes?: string | null;
  attachments?: EvidenceAttachment[];
}
