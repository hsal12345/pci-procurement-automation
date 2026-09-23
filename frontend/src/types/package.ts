export type PackageCommercialStatus = "ACTIVE" | "ISSUED" | "CANCELLED";
export type RevisionStatus =
  | "DRAFT"
  | "UNDER_REVIEW"
  | "RETURNED"
  | "APPROVED"
  | "ISSUED"
  | "SUPERSEDED"
  | "CANCELLED";

export type AIReviewStatus =
  | "NOT_RUN"
  | "CLEAN"
  | "WARNINGS_DETECTED"
  | "MANUAL_REVIEW_RECORDED"
  | "FAILED"
  | "COMPLETED";

export type UserRole =
  | "ADMINISTRATION"
  | "LOGISTICS"
  | "FINANCE_DIRECTOR"
  | "SYSTEM_ADMINISTRATOR";

export interface RevisionLine {
  id?: string;
  revision_id?: string;
  line_number: number;
  item_id?: string | null;
  original_description: string;
  confirmed_description?: string | null;
  specification?: string | null;
  quantity: number;
  received_quantity?: number;
  unit: string;
  hps_unit_price: number;
  offer_unit_price: number;
  final_unit_price: number;
  discount: number;
  line_total: number;
  condition?: "BAIK" | "RUSAK";
  notes?: string | null;
}

export interface DocumentEvent {
  id?: string;
  revision_id?: string;
  event_code: string;
  event_date: string;
  day_name_id?: string | null;
  location?: string | null;
  notes?: string | null;
}

export interface DocumentNumber {
  id?: string;
  revision_id?: string;
  doc_code: string;
  doc_number: string;
  issuer?: string;
  counter_val?: number;
  issue_date?: string;
  is_reserved?: boolean;
}

export interface OfficialSnapshotItem {
  role?: string;
  role_title?: string;
  name: string;
  person_name?: string;
  nip?: string | null;
  position_sk_number?: string | null;
  sk_date?: string | null;
}

export interface SchoolSnapshot {
  npsn?: string;
  name?: string;
  address?: string;
  district?: string;
  regency?: string;
  province?: string;
  principal_name?: string;
  principal_nip?: string;
}

export interface CompanySnapshot {
  name?: string;
  npwp?: string;
  address?: string;
  director_name?: string;
  bank_name?: string;
  bank_account_number?: string;
  bank_account_holder?: string;
}

export interface TaxPolicySnapshotItem {
  tax_type: "PPN" | "PPH22" | "PPH23" | string;
  rate_percent?: number;
  rate?: number | string;
  is_withholding?: boolean;
  withholding_rule?: string;
  is_inclusive?: boolean;
  rounding_rule?: string;
  notes?: string;
}

export interface PackageRevision {
  id: string;
  package_id: string;
  revision_number: number;
  version: number;
  fiscal_year?: number;
  status: RevisionStatus;
  ai_review_status: AIReviewStatus;
  is_locked: boolean;
  school_snapshot?: SchoolSnapshot | null;
  company_snapshot?: CompanySnapshot | null;
  tax_policy_snapshot?: TaxPolicySnapshotItem[] | null;
  officials_snapshot?: OfficialSnapshotItem[] | null;
  subtotal: number;
  tax_total: number;
  grand_total: number;
  terbilang_grand_total?: string | null;
  notes?: string | null;
  lines: RevisionLine[];
  events: DocumentEvent[];
  numbers: DocumentNumber[];
  created_at?: string;
  updated_at?: string;
}

export interface PackageItem {
  id: string;
  package_code: string;
  package_number?: string;
  fiscal_year: number;
  quarter: number;
  fund_source: "BOS_REGULER" | "BOS_KINERJA" | "BOP" | "LAINNYA";
  status: PackageCommercialStatus;
  current_revision_id?: string | null;
  revisions: PackageRevision[];
  created_at?: string;
  updated_at?: string;
}

