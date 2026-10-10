import { UserRole, PackageItem, PackageRevision, RevisionLine } from "@/types/package";
import { ValidationRun } from "@/types/validation";
import { LogisticsRecord, EvidenceAttachment } from "@/types/logistics";
import { Artifact, GenerationJob } from "@/types/documents";
import { SemanticAuditResponse, AIUsageResponse, CandidateMappingProposal } from "@/types/ai";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

// Role Management for Dev / Simulation
const ROLE_STORAGE_KEY = "pci_user_role";
const ACTOR_STORAGE_KEY = "pci_actor_name";

export function getCurrentRole(): UserRole {
  if (typeof window === "undefined") return "ADMINISTRATION";
  return (localStorage.getItem(ROLE_STORAGE_KEY) as UserRole) || "ADMINISTRATION";
}

export function setCurrentRole(role: UserRole): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(ROLE_STORAGE_KEY, role);
    window.dispatchEvent(new Event("pci_role_changed"));
  }
}

export function getCurrentActorName(): string {
  if (typeof window === "undefined") return "Staf Administrasi";
  return localStorage.getItem(ACTOR_STORAGE_KEY) || "Staf Administrasi";
}

export function setCurrentActorName(name: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(ACTOR_STORAGE_KEY, name);
  }
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = "ApiError";
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = new Headers(options.headers || {});

  // Inject RBAC simulation headers
  const role = getCurrentRole();
  const actor = getCurrentActorName();
  headers.set("X-User-Role", role);
  headers.set("X-Actor-Name", actor);

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    let errorDetail = res.statusText;
    let errData: any = null;
    try {
      errData = await res.json();
      if (errData && errData.detail) {
        errorDetail = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore
    }
    throw new ApiError(res.status, errorDetail, errData);
  }

  // Handle empty 204
  if (res.status === 204) {
    return {} as T;
  }

  return res.json() as Promise<T>;
}

export const apiClient = {
  // Packages & Revisions
  getPackages: () => request<PackageItem[]>("/api/v1/packages"),
  getPackage: (id: string) => request<PackageItem>(`/api/v1/packages/${id}`),
  getRevision: (id: string) => request<PackageRevision>(`/api/v1/revisions/${id}`),

  createPackage: (payload: any) =>
    request<PackageItem>("/api/v1/packages", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deletePackage: (id: string) =>
    request<{ message: string; package_id: string; package_number: string }>(`/api/v1/packages/${id}`, {
      method: "DELETE",
    }),

  updateRevisionDetails: (
    revisionId: string,
    payload: {
      expected_version: number;
      lines?: any;
      events?: any;
      numbers?: any;
      school_snapshot?: any;
      company_snapshot?: any;
      tax_policy_snapshot?: any;
      officials_snapshot?: any;
      notes?: string;
    }
  ) =>
    request<PackageRevision>(`/api/v1/revisions/${revisionId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  updateRevisionLines: (
    revisionId: string,
    lines: RevisionLine[],
    expectedVersion: number
  ) =>
    request<PackageRevision>(`/api/v1/revisions/${revisionId}/lines`, {
      method: "PUT",
      body: JSON.stringify({ lines, expected_version: expectedVersion }),
    }),

  calculateRevisionTotals: (revisionId: string, lines: RevisionLine[]) =>
    request<{
      subtotal: number;
      tax_total: number;
      grand_total: number;
      terbilang: string;
      tax_breakdown: Array<{ tax_type: string; amount: number; rate: number }>;
    }>(`/api/v1/revisions/${revisionId}/calculate`, {
      method: "POST",
      body: JSON.stringify({ lines }),
    }).catch(() => null), // Graceful fallback if calculation route not yet mounted

  // Workflow State Machine Actions
  validateRevision: (revisionId: string) =>
    request<ValidationRun>(`/api/v1/revisions/${revisionId}/validate`, {
      method: "POST",
    }),

  submitRevision: (revisionId: string, expectedVersion: number, notes?: string) =>
    request<PackageRevision>(`/api/v1/revisions/${revisionId}/submit`, {
      method: "POST",
      body: JSON.stringify({ expected_version: expectedVersion, notes }),
    }),

  returnRevision: (revisionId: string, expectedVersion: number, comment: string) =>
    request<PackageRevision>(`/api/v1/revisions/${revisionId}/return`, {
      method: "POST",
      body: JSON.stringify({ expected_version: expectedVersion, comment }),
    }),

  approveRevision: (
    revisionId: string,
    expectedVersion: number,
    manifestHash?: string,
    note?: string
  ) =>
    request<PackageRevision>(`/api/v1/revisions/${revisionId}/approve`, {
      method: "POST",
      body: JSON.stringify({
        expected_version: expectedVersion,
        manifest_hash: manifestHash,
        note,
      }),
    }),

  issueRevision: (packageId: string, revisionId: string, notes?: string) =>
    request<any>(`/api/v1/packages/${packageId}/revisions/${revisionId}/issue`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  reopenPackage: (packageId: string, reason: string) =>
    request<PackageRevision>(`/api/v1/packages/${packageId}/reopen`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  cancelPackage: (packageId: string, reason: string, expectedVersion?: number) =>
    request<any>(`/api/v1/packages/${packageId}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason, expected_version: expectedVersion }),
    }),

  // AI Assistance & Semantic Verification
  auditWithAI: (revisionId: string) =>
    request<SemanticAuditResponse>(`/api/v1/ai/revisions/${revisionId}/audit`, {
      method: "POST",
    }),

  recordManualReview: (revisionId: string, verifierName: string, verificationNotes: string) =>
    request<any>(`/api/v1/ai/revisions/${revisionId}/record-manual-review`, {
      method: "POST",
      body: JSON.stringify({
        reviewer_name: verifierName,
        verifier_name: verifierName,
        reason: verificationNotes,
        verification_notes: verificationNotes,
        notes: verificationNotes,
      }),
    }),

  getAIUsage: () => request<AIUsageResponse>("/api/v1/ai/usage"),

  suggestAIMapping: (importId: string) =>
    request<CandidateMappingProposal>(`/api/v1/ai/imports/${importId}/suggest-mapping`, {
      method: "POST",
    }),

  // Logistics
  getLogistics: (revisionId: string) =>
    request<LogisticsRecord>(`/api/v1/revisions/${revisionId}/logistics`),

  updateLogistics: (revisionId: string, payload: any) =>
    request<LogisticsRecord>(`/api/v1/revisions/${revisionId}/logistics`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  uploadLogisticsEvidence: (revisionId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<EvidenceAttachment>(`/api/v1/revisions/${revisionId}/logistics/evidence`, {
      method: "POST",
      body: formData,
    });
  },

  // Documents & Generator
  triggerGeneration: (revisionId: string, formats?: string[]) =>
    request<GenerationJob>(`/api/v1/revisions/${revisionId}/generate`, {
      method: "POST",
      body: JSON.stringify({ formats }),
    }),

  getArtifacts: (revisionId: string) =>
    request<Artifact[]>(`/api/v1/revisions/${revisionId}/artifacts`),

  // Audit Events
  getAuditEvents: (params?: { entity_name?: string; entity_id?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.entity_name) q.set("entity_name", params.entity_name);
    if (params?.entity_id) q.set("entity_id", params.entity_id);
    if (params?.limit) q.set("limit", String(params.limit));
    return request<any[]>(`/api/v1/audit/events?${q.toString()}`).catch(() => []);
  },

  getPackageAudit: (packageId: string) =>
    request<any[]>(`/api/v1/packages/${packageId}/audit`).catch(() => []),

  // Master Data Management
  getSchools: () => request<any[]>("/api/v1/masters/schools"),

  createSchool: (payload: {
    name: string;
    npsn?: string;
    address: string;
    level?: string;
    email?: string;
    phone?: string;
    subdistrict?: string;
    postal_code?: string;
    city?: string;
  }) =>
    request<any>("/api/v1/masters/schools", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateSchool: (
    id: string,
    payload: {
      name?: string;
      npsn?: string;
      level?: string;
      address?: string;
      subdistrict?: string;
      city?: string;
      postal_code?: string;
      phone?: string;
      email?: string;
      letterhead_path?: string;
      is_active?: boolean;
    }
  ) =>
    request<any>(`/api/v1/masters/schools/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  uploadSchoolLetterhead: (id: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<any>(`/api/v1/masters/schools/${id}/letterhead`, {
      method: "POST",
      body: formData,
    });
  },

  getCompanies: () => request<any[]>("/api/v1/masters/companies"),

  createCompany: (payload: any) =>
    request<any>("/api/v1/masters/companies", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateCompany: (id: string, payload: any) =>
    request<any>(`/api/v1/masters/companies/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  uploadCompanyLogo: (id: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<any>(`/api/v1/masters/companies/${id}/logo`, {
      method: "POST",
      body: formData,
    });
  },

  getCompanyOfficials: (companyId: string) =>
    request<any[]>(`/api/v1/masters/companies/${companyId}/officials`),

  createCompanyOfficial: (
    companyId: string,
    payload: {
      role?: string;
      role_title?: string;
      person_name: string;
      nip?: string;
      position_sk_number?: string;
    }
  ) =>
    request<any>(`/api/v1/masters/companies/${companyId}/officials`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSchoolOfficials: (schoolId: string) =>
    request<any[]>(`/api/v1/masters/schools/${schoolId}/officials`),

  createSchoolOfficial: (
    schoolId: string,
    payload: {
      role: string;
      person_name: string;
      nip?: string;
      position_sk_number?: string;
      valid_from?: string;
    }
  ) =>
    request<any>(`/api/v1/masters/schools/${schoolId}/officials`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateSchoolOfficial: (
    schoolId: string,
    officialId: string,
    payload: {
      role?: string;
      person_name?: string;
      nip?: string;
      position_sk_number?: string;
      valid_from?: string;
      valid_to?: string;
      is_active?: boolean;
    }
  ) =>
    request<any>(`/api/v1/masters/schools/${schoolId}/officials/${officialId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  deleteSchoolOfficial: (schoolId: string, officialId: string) =>
    request<any>(`/api/v1/masters/schools/${schoolId}/officials/${officialId}`, {
      method: "DELETE",
    }),

  getTaxPolicies: () => request<any[]>("/api/v1/masters/tax-policies"),
};

