"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, getCurrentRole } from "@/lib/api-client";
import { UserRole } from "@/types/package";
import {
  FileCode2,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Eye,
  RefreshCw,
  ShieldCheck,
  X,
  Loader2,
  Sliders,
  Download,
  AlertCircle,
} from "lucide-react";

const ALL_DOC_CODES = [
  "D01", "D02", "D03", "D04", "D05", "D06", "D07",
  "D08", "D09", "D10", "D11", "D12", "D13",
];

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export default function TemplatesManagementPage() {
  const queryClient = useQueryClient();
  const [schemeFilter, setSchemeFilter] = useState<string>("ALL");
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [currentRole, setCurrentRole] = useState<UserRole>("ADMINISTRATION");

  useEffect(() => {
    const syncRole = () => setCurrentRole(getCurrentRole());
    syncRole();
    window.addEventListener("pci_role_changed", syncRole);
    window.addEventListener("pci_auth_changed", syncRole);
    return () => {
      window.removeEventListener("pci_role_changed", syncRole);
      window.removeEventListener("pci_auth_changed", syncRole);
    };
  }, []);

  const isSystemAdmin = currentRole === "SYSTEM_ADMINISTRATOR";

  // Validate & Upload modal state
  const [uploadTarget, setUploadTarget] = useState<any | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationRes, setValidationRes] = useState<any | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // Simulation preview modal state
  const [simTarget, setSimTarget] = useState<any | null>(null);
  const [simResult, setSimResult] = useState<any | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);

  const { data: profiles = [], refetch: refetchProfiles } = useQuery<any[]>({
    queryKey: ["package-profiles"],
    queryFn: () => apiClient.getPackageProfiles(),
  });

  const { data: templates = [], isLoading: isLoadingTemplates, refetch: refetchTemplates } = useQuery<any[]>({
    queryKey: ["master-templates", schemeFilter],
    queryFn: () => apiClient.getTemplates(schemeFilter),
  });

  const showToast = (type: "success" | "error", text: string) => {
    setNotice({ type, text });
    setTimeout(() => setNotice(null), 6000);
  };

  const toggleProfileDocMutation = useMutation({
    mutationFn: async ({ profile, docCode }: { profile: any; docCode: string }) => {
      const current: string[] = Array.isArray(profile.required_doc_codes) ? profile.required_doc_codes : [];
      const exists = current.includes(docCode);
      const updated = exists ? current.filter((d) => d !== docCode) : [...current, docCode].sort();
      return apiClient.updatePackageProfile(profile.id, { required_doc_codes: updated });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["package-profiles"] });
      showToast("success", "Konfigurasi dokumen wajib/opsional skema pendanaan berhasil disimpan (FR-03).");
    },
    onError: (err: any) => showToast("error", err.message || "Gagal memperbarui profil paket dokumen."),
  });

  const toggleTemplateMandatoryMutation = useMutation({
    mutationFn: (tmpl: any) =>
      apiClient.updateTemplateConfig(tmpl.doc_code, { is_mandatory: !tmpl.is_mandatory }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["master-templates"] });
      showToast("success", "Status kewajiban dokumen diperbarui.");
    },
    onError: (err: any) => showToast("error", err.message || "Gagal memperbarui status template."),
  });

  const handleOpenUploadModal = async (tmpl: any) => {
    setUploadTarget(tmpl);
    setSelectedFile(null);
    setValidationRes(null);
    setIsValidating(true);
    try {
      const res = await apiClient.validateTemplate(tmpl.doc_code);
      setValidationRes(res);
    } catch (err: any) {
      showToast("error", err.message || "Gagal memeriksa template aktif.");
    } finally {
      setIsValidating(false);
    }
  };

  const handleFileChange = async (file: File | null) => {
    setSelectedFile(file);
    setValidationRes(null);
    if (!file || !uploadTarget) return;
    setIsValidating(true);
    try {
      const res = await apiClient.validateTemplate(uploadTarget.doc_code, file);
      setValidationRes(res);
    } catch (err: any) {
      setValidationRes({
        is_valid: false,
        filename: file.name,
        detected_tokens: [],
        missing_required_tokens: [],
        unrecognized_tokens: [],
        syntax_errors: [err.message || "Gagal membaca file .docx"],
        message: err.message || "Gagal memvalidasi template.",
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleActivateTemplate = async () => {
    if (!uploadTarget || !selectedFile) return;
    setIsUploading(true);
    try {
      await apiClient.uploadTemplate(uploadTarget.doc_code, selectedFile);
      await refetchTemplates();
      setUploadTarget(null);
      showToast(
        "success",
        `Template ${uploadTarget.doc_code} versi baru berhasil divalidasi & diaktifkan tanpa mengubah arsip historis.`
      );
    } catch (err: any) {
      showToast("error", err.message || "Template ditolak karena token atau sintaks tidak valid (UC-03 Alur 4a).");
    } finally {
      setIsUploading(false);
    }
  };

  const handleOpenSimulation = async (tmpl: any, customFile?: File) => {
    setSimTarget(tmpl);
    setSimResult(null);
    setIsSimulating(true);
    try {
      const res = await apiClient.simulateTemplate(tmpl.doc_code, customFile);
      setSimResult(res);
    } catch (err: any) {
      showToast("error", err.message || "Gagal menjalankan simulasi penggabungan dokumen.");
      setSimTarget(null);
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-12 border-b border-border px-4 flex items-center justify-between gap-4 bg-card/60">
        <div className="flex items-center gap-2">
          <FileCode2 className="w-4 h-4 text-primary" />
          <h1 className="text-sm font-semibold tracking-tight text-foreground">
            Manajemen Paket Dokumen &amp; Token Template (.DOCX) — FR-03 &amp; UC-03
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={schemeFilter}
            onChange={(e) => setSchemeFilter(e.target.value)}
            className="px-2.5 py-1 bg-background border border-border rounded text-xs font-mono"
          >
            <option value="ALL">Semua Skema Dana</option>
            <option value="BOS_REGULER">BOS Reguler</option>
            <option value="BOS_KINERJA">BOS Kinerja</option>
            <option value="BOP">BOP Pendidikan</option>
          </select>
          <button
            type="button"
            onClick={() => {
              refetchProfiles();
              refetchTemplates();
            }}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition"
            title="Muat Ulang"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Toast */}
      {notice && (
        <div
          className={`px-4 py-2.5 text-xs flex items-center gap-2 border-b ${
            notice.type === "error"
              ? "bg-red-500/15 border-red-500/30 text-red-300"
              : "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"
          }`}
        >
          {notice.type === "error" ? (
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          )}
          <span>{notice.text}</span>
        </div>
      )}

      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* Section 1: PackageProfile Mandatory vs Optional Matrix */}
        <div className="border border-border rounded-lg bg-card p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-border pb-2">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">
                Konfigurasi Keharusan Dokumen per Sumber Dana BOS / BOP (FR-03)
              </h2>
            </div>
            <span className="text-[11px] font-mono text-muted-foreground">
              {isSystemAdmin
                ? "Klik kode dokumen untuk mengubah status Wajib (Biru) / Opsional (Abu)"
                : "Mode Baca & Simulasi (Perubahan konfigurasi hanya untuk SYSTEM_ADMINISTRATOR)"}
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            {profiles.map((prof) => {
              const reqDocs: string[] = Array.isArray(prof.required_doc_codes) ? prof.required_doc_codes : [];
              return (
                <div key={prof.id} className="border border-border rounded-lg p-3 bg-background/50 space-y-2.5">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-xs text-primary">{prof.code}</span>
                      <span className="text-[10px] font-mono text-muted-foreground">
                        {reqDocs.length} / 13 Wajib
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-foreground mt-0.5">{prof.name}</div>
                    {prof.description && (
                      <div className="text-[11px] text-muted-foreground mt-0.5">{prof.description}</div>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {ALL_DOC_CODES.map((dc) => {
                      const isMandatory = reqDocs.includes(dc);
                      return (
                        <button
                          key={dc}
                          type="button"
                          disabled={!isSystemAdmin}
                          onClick={() => {
                            if (isSystemAdmin) {
                              toggleProfileDocMutation.mutate({ profile: prof, docCode: dc });
                            }
                          }}
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border transition disabled:cursor-not-allowed disabled:opacity-75 ${
                            isMandatory
                              ? "bg-primary/20 text-primary border-primary/40 hover:bg-primary/30"
                              : "bg-muted/40 text-muted-foreground border-border hover:bg-muted"
                          }`}
                          title={
                            !isSystemAdmin
                              ? `${dc}: ${isMandatory ? "WAJIB" : "OPSIONAL"} (Hanya SYSTEM_ADMINISTRATOR)`
                              : isMandatory
                              ? `${dc}: WAJIB (klik untuk opsional)`
                              : `${dc}: OPSIONAL (klik untuk wajib)`
                          }
                        >
                          {dc}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Section 2: Supported Token Reference Banner */}
        <div className="border border-border rounded-lg bg-muted/20 p-3 text-[11px] font-mono text-muted-foreground space-y-1">
          <div className="font-semibold text-foreground flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Kamus Token Variabel Resmi Template (.DOCX / Jinja2):</span>
          </div>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {[
              "{{nama_sekolah}}", "{{school.name}}", "{{npsn_sekolah}}", "{{nama_perusahaan}}",
              "{{nilai_kontrak}}", "{{terbilang_kontrak}}", "{{totals.grand_total_formatted}}",
              "{{totals.terbilang}}", "{{events.HPS.date_id}}", "{{numbers.D05.doc_number}}",
              "{%tr for item in items %}",
            ].map((tok) => (
              <code key={tok} className="px-1.5 py-0.5 rounded bg-card border border-border text-primary">
                {tok}
              </code>
            ))}
          </div>
        </div>

        {/* Section 3: 13 Document Templates Table */}
        <div className="border border-border rounded-lg bg-card overflow-hidden shadow-xs">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-muted/60 border-b border-border text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                <th className="px-3 py-2.5 w-16 text-center">Kode</th>
                <th className="px-3 py-2.5 min-w-[220px]">Jenis Dokumen SPJ</th>
                <th className="px-3 py-2.5 w-20 text-center">Versi</th>
                <th className="px-3 py-2.5 w-28 text-center">Keharusan</th>
                <th className="px-3 py-2.5 min-w-[260px]">Token Terdeteksi</th>
                <th className="px-3 py-2.5 w-52 text-right">Aksi (UC-03)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70">
              {isLoadingTemplates ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-muted-foreground font-mono">
                    Memuat daftar template dokumen...
                  </td>
                </tr>
              ) : (
                templates.map((t) => (
                  <tr key={t.id} className="hover:bg-muted/20 transition">
                    <td className="px-3 py-2.5 text-center font-mono font-bold text-primary">
                      {t.doc_code}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="font-semibold text-foreground">{t.doc_name}</div>
                      <div className="text-[10px] font-mono text-muted-foreground">
                        {t.filename} • Oleh: {t.uploaded_by}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-center font-mono">
                      <span className="px-2 py-0.5 rounded bg-muted border border-border font-bold">
                        v{t.version}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <button
                        type="button"
                        disabled={!isSystemAdmin}
                        onClick={() => {
                          if (isSystemAdmin) {
                            toggleTemplateMandatoryMutation.mutate(t);
                          }
                        }}
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border disabled:cursor-not-allowed disabled:opacity-75 ${
                          t.is_mandatory
                            ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                            : "bg-zinc-500/15 text-zinc-400 border-zinc-500/30"
                        }`}
                        title={isSystemAdmin ? "Ubah status wajib/opsional" : "Hanya SYSTEM_ADMINISTRATOR yang dapat mengubah"}
                      >
                        {t.is_mandatory ? "WAJIB" : "OPSIONAL"}
                      </button>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1 max-w-md">
                        {(t.detected_tokens || []).slice(0, 6).map((tok: string) => (
                          <span
                            key={tok}
                            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted/60 border border-border text-foreground"
                          >
                            {`{{${tok}}}`}
                          </span>
                        ))}
                        {(t.detected_tokens || []).length > 6 && (
                          <span className="text-[10px] font-mono text-muted-foreground">
                            +{(t.detected_tokens || []).length - 6} lagi
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleOpenSimulation(t)}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded border border-border bg-card hover:bg-muted text-[11px] font-medium"
                          title="Simulasi Pratinjau (UC-03 Langkah 5)"
                        >
                          <Eye className="w-3 h-3 text-sky-400" />
                          <span>Simulasi</span>
                        </button>
                        {isSystemAdmin && (
                          <button
                            type="button"
                            onClick={() => handleOpenUploadModal(t)}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded bg-primary/15 border border-primary/30 text-primary hover:bg-primary/25 text-[11px] font-semibold"
                            title="Validasi Token & Unggah Template .docx Baru"
                          >
                            <Upload className="w-3 h-3" />
                            <span>Kelola / Unggah</span>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal 1: Validate & Upload .DOCX Template (UC-03 Steps 3-6 & Flow 4a) */}
      {uploadTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-foreground">
                  Validasi &amp; Unggah Template: {uploadTarget.doc_code} — {uploadTarget.doc_name}
                </h2>
                <p className="text-[11px] text-muted-foreground font-mono">
                  Versi aktif saat ini: v{uploadTarget.version} ({uploadTarget.filename})
                </p>
              </div>
              <button
                type="button"
                onClick={() => setUploadTarget(null)}
                className="text-muted-foreground hover:text-foreground p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-4 overflow-y-auto text-xs">
              <div className="border border-dashed border-border rounded-lg p-4 bg-background/50 space-y-2">
                <label className="block font-mono text-[11px] uppercase text-muted-foreground font-semibold">
                  Pilih Berkas Acuan Microsoft Word (.docx) Baru (Opsional untuk Pemeriksaan)
                </label>
                <input
                  type="file"
                  accept=".docx"
                  onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                  className="block w-full text-xs text-muted-foreground file:mr-3 file:py-1.5 file:px-3 file:rounded file:border file:border-border file:bg-muted file:text-foreground hover:file:bg-muted/80"
                />
                <p className="text-[11px] text-muted-foreground">
                  Sistem akan otomatis memvalidasi sintaks Jinja2/docxtpl serta mengenali seluruh token variabel (UC-03 Langkah 4 &amp; Alur 4a).
                </p>
              </div>

              {isValidating ? (
                <div className="p-6 flex items-center justify-center gap-2 text-muted-foreground font-mono">
                  <Loader2 className="w-4 h-4 animate-spin text-primary" />
                  <span>Memeriksa struktur XML &amp; sintaks token variabel...</span>
                </div>
              ) : validationRes ? (
                <div className="space-y-3">
                  <div
                    className={`p-3 rounded-lg border flex items-start gap-2.5 ${
                      validationRes.is_valid
                        ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300"
                        : "bg-red-500/15 border-red-500/40 text-red-300"
                    }`}
                  >
                    {validationRes.is_valid ? (
                      <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5 text-emerald-400" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" />
                    )}
                    <div className="space-y-1">
                      <div className="font-semibold">{validationRes.message}</div>
                      {validationRes.syntax_errors?.length > 0 && (
                        <ul className="list-disc pl-4 text-[11px] font-mono">
                          {validationRes.syntax_errors.map((err: string, idx: number) => (
                            <li key={idx}>{err}</li>
                          ))}
                        </ul>
                      )}
                      {validationRes.unrecognized_tokens?.length > 0 && (
                        <div className="text-[11px] font-mono">
                          Token tidak dikenal (Alur 4a):{" "}
                          {validationRes.unrecognized_tokens.map((u: string) => `{{${u}}}`).join(", ")}
                        </div>
                      )}
                    </div>
                  </div>

                  {validationRes.missing_required_tokens?.length > 0 && (
                    <div className="p-2.5 rounded border border-amber-500/30 bg-amber-500/10 text-amber-300 text-[11px] font-mono">
                      Catatan token acuan yang belum terdeteksi: {validationRes.missing_required_tokens.join(", ")}
                    </div>
                  )}

                  <div className="border border-border rounded p-3 bg-muted/20 space-y-1.5">
                    <div className="text-[11px] font-mono font-semibold text-foreground">
                      Token Terdeteksi ({validationRes.detected_tokens?.length || 0}):
                    </div>
                    <div className="flex flex-wrap gap-1 max-h-36 overflow-y-auto">
                      {(validationRes.detected_tokens || []).map((tok: string) => {
                        const isUnknown = (validationRes.unrecognized_tokens || []).includes(tok);
                        return (
                          <code
                            key={tok}
                            className={`text-[10px] px-1.5 py-0.5 rounded border ${
                              isUnknown
                                ? "bg-red-500/20 border-red-500/40 text-red-300"
                                : "bg-card border-border text-foreground"
                            }`}
                          >
                            {`{{${tok}}}`}
                          </code>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : null}

              <div className="flex items-center justify-between pt-3 border-t border-border">
                <button
                  type="button"
                  disabled={isValidating || (validationRes && !validationRes.is_valid)}
                  onClick={() => handleOpenSimulation(uploadTarget, selectedFile || undefined)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-border bg-card hover:bg-muted text-foreground disabled:opacity-50"
                >
                  <Eye className="w-3.5 h-3.5 text-sky-400" />
                  <span>Uji Simulasi Penggabungan</span>
                </button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setUploadTarget(null)}
                    className="px-3 py-1.5 rounded border border-border bg-card hover:bg-muted"
                  >
                    Tutup
                  </button>
                  <button
                    type="button"
                    disabled={!selectedFile || !validationRes?.is_valid || isUploading}
                    onClick={handleActivateTemplate}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded bg-primary text-primary-foreground font-semibold hover:opacity-90 disabled:opacity-50"
                  >
                    {isUploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                    <span>Simpan &amp; Aktifkan Versi Baru</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal 2: Live Simulation Preview (UC-03 Step 5) */}
      {simTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-foreground">
                  Simulasi Penggabungan Dokumen: {simTarget.doc_code} — {simTarget.doc_name}
                </h2>
                <p className="text-[11px] font-mono text-muted-foreground">
                  Pratinjau isi dokumen menggunakan data sampel transaksi sekolah (UC-03 Langkah 5)
                </p>
              </div>
              <button type="button" onClick={() => setSimTarget(null)} className="text-muted-foreground hover:text-foreground p-1">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-4 overflow-y-auto text-xs">
              {isSimulating ? (
                <div className="p-10 flex items-center justify-center gap-2 text-muted-foreground font-mono">
                  <Loader2 className="w-4 h-4 animate-spin text-primary" />
                  <span>Merender simulasi template .docx...</span>
                </div>
              ) : simResult ? (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 p-3 rounded border border-border bg-muted/20 font-mono text-[11px]">
                    <div>
                      <span className="text-muted-foreground block text-[10px]">Sekolah Sampel</span>
                      <span className="font-semibold text-foreground">{simResult.sample_context_summary?.nama_sekolah}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">Rekanan</span>
                      <span className="font-semibold text-foreground">{simResult.sample_context_summary?.nama_perusahaan}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">Nilai Kontrak</span>
                      <span className="font-semibold text-emerald-400">{simResult.sample_context_summary?.nilai_kontrak}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">Nomor Paket</span>
                      <span className="font-semibold text-foreground">{simResult.sample_context_summary?.nomor_paket}</span>
                    </div>
                  </div>

                  <div className="border border-border rounded bg-white text-slate-900 p-6 space-y-2 shadow-inner max-h-[50vh] overflow-y-auto font-serif">
                    {(simResult.paragraphs || []).map((p: string, i: number) => (
                      <p key={i} className="text-xs leading-relaxed">
                        {p}
                      </p>
                    ))}
                    {(simResult.tables || []).map((tbl: string[][], ti: number) => (
                      <div key={ti} className="overflow-x-auto pt-2">
                        <table className="w-full border-collapse border border-slate-300 text-[11px] font-sans">
                          <tbody>
                            {tbl.map((row, ri) => (
                              <tr key={ri} className={ri === 0 ? "bg-slate-100 font-semibold" : ""}>
                                {row.map((cell, ci) => (
                                  <td key={ci} className="border border-slate-300 px-2 py-1">
                                    {cell}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                    <form
                      action={`${API_BASE}/api/v1/masters/templates/${simTarget.doc_code}/simulate?download=true`}
                      method="POST"
                      target="_blank"
                    >
                      <button
                        type="submit"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-border bg-card hover:bg-muted text-foreground"
                      >
                        <Download className="w-3.5 h-3.5 text-primary" />
                        <span>Unduh Hasil Simulasi (.DOCX)</span>
                      </button>
                    </form>
                    <button
                      type="button"
                      onClick={() => setSimTarget(null)}
                      className="px-4 py-1.5 rounded bg-primary text-primary-foreground font-semibold"
                    >
                      Selesai Tinjau
                    </button>
                  </div>
                </>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
