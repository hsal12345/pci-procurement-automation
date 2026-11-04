"use client";

import { useState } from "react";
import { PackageRevision } from "@/types/package";
import { Finding, ValidationRun } from "@/types/validation";
import { SemanticAuditResponse, SemanticDiscrepancyItem } from "@/types/ai";
import { apiClient } from "@/lib/api-client";
import {
  AlertOctagon,
  AlertTriangle,
  Info,
  RotateCcw,
  Sparkles,
  ExternalLink,
  CheckCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  FileSignature,
  ChevronDown,
  ChevronUp,
  Brain,
  ShieldCheck,
  Bot,
  Layers,
  ArrowRight,
  X,
  FileText,
} from "lucide-react";

interface TabInspectionProps {
  revision: PackageRevision;
  validationRun?: ValidationRun | null;
  onRefresh: () => Promise<void>;
  onNavigateToField: (tabKey: string, fieldId?: string) => void;
}

interface NotificationState {
  type: "success" | "error" | "info" | "warning";
  title: string;
  message: string;
}

export function TabInspection({
  revision,
  validationRun,
  onRefresh,
  onNavigateToField,
}: TabInspectionProps) {
  const [activeSubTab, setActiveSubTab] = useState<"compliance" | "ai_audit">("compliance");
  const [isValidating, setIsValidating] = useState(false);
  const [isAuditingAI, setIsAuditingAI] = useState(false);
  const [aiAuditResult, setAiAuditResult] = useState<SemanticAuditResponse | null>(null);
  const [expandedReasoning, setExpandedReasoning] = useState<Record<string, boolean>>({});
  const [isRecordingManual, setIsRecordingManual] = useState(false);
  const [manualReviewNotes, setManualReviewNotes] = useState("");
  const [notification, setNotification] = useState<NotificationState | null>(null);

  const allFindings = validationRun?.findings || [];
  const deterministicFindings = allFindings.filter((f) => f.rule_code !== "AI_SEMANTIC_DISCREPANCY");
  const aiFindingsFromValidation = allFindings.filter((f) => f.rule_code === "AI_SEMANTIC_DISCREPANCY");

  const blockCount = deterministicFindings.filter((f) => f.severity === "BLOCK").length;
  const warningCount = deterministicFindings.filter((f) => f.severity === "WARNING").length;
  const infoCount = deterministicFindings.filter((f) => f.severity === "INFO").length;
  const aiFindingsCount = aiAuditResult
    ? aiAuditResult.findings_count
    : aiFindingsFromValidation.length;

  const toggleReasoning = (id: string) => {
    setExpandedReasoning((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleRunValidation = async () => {
    setIsValidating(true);
    setNotification(null);
    try {
      await apiClient.validateRevision(revision.id);
      await onRefresh();
      setNotification({
        type: "success",
        title: "Validasi Sistem Selesai",
        message: "Pemeriksaan aturan bisnis deterministik (BR01-BR15) berhasil diperbarui.",
      });
    } catch (err: any) {
      setNotification({
        type: "error",
        title: "Validasi Sistem Gagal",
        message: err.message || String(err),
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleRunAIAudit = async () => {
    setIsAuditingAI(true);
    setNotification(null);
    try {
      const resp = await apiClient.auditWithAI(revision.id);
      setAiAuditResult(resp);
      await onRefresh();
      setActiveSubTab("ai_audit");
      setNotification({
        type: "success",
        title: "Audit Teks Semantik AI Selesai",
        message: resp.summary || `Pemeriksaan selesai dengan status ${resp.status}. Hasil ditampilkan pada sub-tab Audit AI.`,
      });
    } catch (err: any) {
      setNotification({
        type: "error",
        title: "Audit Teks Semantik AI Mengalami Kendala",
        message: err.message || String(err),
      });
    } finally {
      setIsAuditingAI(false);
    }
  };

  const handleRecordManualReview = async () => {
    if (!manualReviewNotes.trim()) {
      setNotification({
        type: "warning",
        title: "Catatan Wajib Diisi",
        message: "Harap masukkan rincian catatan verifikasi manual sebelum menyimpan.",
      });
      return;
    }
    try {
      await apiClient.recordManualReview(
        revision.id,
        "Petugas Pemeriksa Administrasi",
        manualReviewNotes.trim()
      );
      await onRefresh();
      setIsRecordingManual(false);
      setNotification({
        type: "success",
        title: "Verifikasi Manual Berhasil Dicatat",
        message: "Status verifikasi teks AI telah diperbarui menjadi MANUAL_REVIEW_RECORDED.",
      });
    } catch (err: any) {
      setNotification({
        type: "error",
        title: "Gagal Mencatat Verifikasi Manual",
        message: err.message || String(err),
      });
    }
  };

  // Prepare unified list of AI discrepancy items
  const resolvedAIDiscrepancies: SemanticDiscrepancyItem[] = aiAuditResult
    ? aiAuditResult.findings
    : aiFindingsFromValidation.map((f: Finding, idx: number) => {
        const typeMatch = f.message.match(/^\[(.*?)\]/);
        const discType = (typeMatch ? typeMatch[1] : "SUSPECT_ANOMALY") as any;
        const cleanMsg = f.message.replace(/^\[(.*?)\]\s*/, "");
        const expected = f.expected_value || "";
        const sheetMatch = expected.match(/Variasi pada ([^:]+):/);
        const sheetB = sheetMatch ? sheetMatch[1] : "D05";
        const recAction = expected.includes(":") ? expected.split(":")[1].trim() : expected;

        return {
          sheet_a: f.sheet_name || "D01",
          sheet_b: sheetB,
          line_number: idx + 1,
          item_name: f.current_value || "Deskripsi Barang",
          discrepancy_type: discType,
          severity: (f.severity as any) || "WARNING",
          message: cleanMsg,
          recommended_action: recAction || "Lakukan verifikasi kesesuaian fisik dan administratif.",
          explanation: cleanMsg,
        };
      });

  return (
    <div className="p-6 max-w-5xl space-y-6 text-xs font-sans">
      {/* 1. Metric Cards Header */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {/* BLOCK */}
        <div className="border border-red-500/30 bg-red-500/10 p-4 rounded-lg flex items-center justify-between shadow-xs">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-red-300 font-bold block">
              Kesalahan Memblokir
            </span>
            <span className="text-2xl font-mono font-bold text-red-200 tabular-nums">
              {blockCount}
            </span>
            <span className="text-[10px] text-red-300/80 block mt-0.5">Wajib Diperbaiki (BR01-BR15)</span>
          </div>
          <AlertOctagon className="w-6 h-6 text-red-400" />
        </div>

        {/* WARNING */}
        <div className="border border-amber-500/30 bg-amber-500/10 p-4 rounded-lg flex items-center justify-between shadow-xs">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-amber-300 font-bold block">
              Peringatan Bisnis
            </span>
            <span className="text-2xl font-mono font-bold text-amber-200 tabular-nums">
              {warningCount}
            </span>
            <span className="text-[10px] text-amber-300/80 block mt-0.5">Dapat Didisposisi</span>
          </div>
          <AlertTriangle className="w-6 h-6 text-amber-400" />
        </div>

        {/* INFO */}
        <div className="border border-sky-500/30 bg-sky-500/10 p-4 rounded-lg flex items-center justify-between shadow-xs">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-sky-300 font-bold block">
              Informasi Tambahan
            </span>
            <span className="text-2xl font-mono font-bold text-sky-200 tabular-nums">
              {infoCount}
            </span>
            <span className="text-[10px] text-sky-300/80 block mt-0.5">Catatan Sistem</span>
          </div>
          <Info className="w-6 h-6 text-sky-400" />
        </div>

        {/* AI STATUS */}
        <div className="border border-border bg-card p-4 rounded-lg flex items-center justify-between shadow-xs">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-bold block">
              Audit Teks Semantik AI
            </span>
            <span className="text-xs font-mono font-bold text-foreground block mt-1">
              {revision.ai_review_status}
            </span>
            <span className="text-[10px] text-muted-foreground block mt-0.5">
              {aiFindingsCount > 0 ? `${aiFindingsCount} Anomali Terdeteksi` : "FR05 & AT16 Kepatuhan"}
            </span>
          </div>
          <Sparkles className="w-5 h-5 text-amber-400" />
        </div>
      </div>

      {/* 2. Notification Banner (Replacing Native Browser Alerts) */}
      {notification && (
        <div
          className={`p-3.5 rounded-lg border flex items-start justify-between gap-3 animate-in fade-in duration-200 ${
            notification.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-200"
              : notification.type === "error"
              ? "bg-red-500/10 border-red-500/30 text-red-200"
              : notification.type === "warning"
              ? "bg-amber-500/10 border-amber-500/30 text-amber-200"
              : "bg-sky-500/10 border-sky-500/30 text-sky-200"
          }`}
        >
          <div className="flex items-start gap-2.5">
            {notification.type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />}
            {notification.type === "error" && <XCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />}
            {notification.type === "warning" && <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />}
            {notification.type === "info" && <Info className="w-4 h-4 text-sky-400 mt-0.5 shrink-0" />}
            <div>
              <h4 className="font-semibold text-xs font-mono">{notification.title}</h4>
              <p className="text-[11px] opacity-90 mt-0.5 leading-relaxed font-sans">{notification.message}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setNotification(null)}
            className="text-muted-foreground hover:text-foreground p-0.5 rounded transition"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* 3. Action Trigger Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-y border-border py-2.5">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRunValidation}
            disabled={isValidating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary text-primary-foreground font-medium text-xs hover:opacity-90 transition shadow-xs"
          >
            {isValidating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
            <span>Jalankan Validasi Sistem (BR01-BR15)</span>
          </button>

          <button
            type="button"
            onClick={handleRunAIAudit}
            disabled={isAuditingAI}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-muted hover:bg-muted/80 text-foreground font-medium text-xs border border-border transition shadow-xs"
          >
            {isAuditingAI ? <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" /> : <Sparkles className="w-3.5 h-3.5 text-amber-400" />}
            <span>Audit Teks AI (Semantik)</span>
          </button>
        </div>

        {/* Manual Review Recording Fallback Button */}
        <button
          type="button"
          onClick={() => setIsRecordingManual(true)}
          className="flex items-center gap-1 px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground border border-dashed border-border rounded hover:bg-muted/40 transition font-mono"
        >
          <FileSignature className="w-3.5 h-3.5 text-sky-400" />
          <span>Catat Verifikasi Manual</span>
        </button>
      </div>

      {/* 4. Sub-Tab Navigation Bar */}
      <div className="flex border-b border-border gap-2">
        <button
          type="button"
          onClick={() => setActiveSubTab("compliance")}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-mono font-medium border-b-2 transition -mb-px ${
            activeSubTab === "compliance"
              ? "border-primary text-primary font-bold bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Aturan Kepatuhan Bisnis (BR01–BR15)</span>
          <span
            className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono tabular-nums ${
              blockCount > 0
                ? "bg-red-500/20 text-red-300 font-bold"
                : deterministicFindings.length > 0
                ? "bg-amber-500/20 text-amber-300 font-bold"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {deterministicFindings.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSubTab("ai_audit")}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-mono font-medium border-b-2 transition -mb-px ${
            activeSubTab === "ai_audit"
              ? "border-amber-400 text-amber-400 font-bold bg-amber-400/5"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted"
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Hasil Evaluasi Audit Teks AI (Semantik)</span>
          <span
            className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono tabular-nums ${
              aiFindingsCount > 0
                ? "bg-amber-500/20 text-amber-300 font-bold"
                : revision.ai_review_status === "COMPLETED"
                ? "bg-emerald-500/20 text-emerald-300 font-bold"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {aiFindingsCount > 0
              ? `${aiFindingsCount} Anomali`
              : revision.ai_review_status === "COMPLETED"
              ? "Bersih"
              : revision.ai_review_status}
          </span>
        </button>
      </div>

      {/* 5. Sub-Tab 1: Business Rule Compliance (Deterministic Findings) */}
      {activeSubTab === "compliance" && (
        <div className="border border-border rounded-lg bg-card overflow-hidden animate-in fade-in duration-150">
          <div className="px-4 py-2.5 bg-muted/40 border-b border-border flex items-center justify-between">
            <h3 className="font-semibold text-foreground text-xs uppercase tracking-wider font-mono flex items-center gap-2">
              <ShieldCheck className="w-3.5 h-3.5 text-primary" />
              <span>Daftar Temuan Kepatuhan Aturan Bisnis (BR01-BR15)</span>
            </h3>
            <span className="text-[10px] font-mono text-muted-foreground">
              {deterministicFindings.length} Temuan Terdeteksi
            </span>
          </div>

          {deterministicFindings.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground font-mono">
              <CheckCircle className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
              <p className="text-xs font-medium text-foreground">
                Tidak ada temuan pelanggaran aturan bisnis deterministik (BR01-BR15).
              </p>
              <p className="text-[11px] text-muted-foreground mt-1">
                Kalkulasi matematis, kelengkapan kop surat, dan urutan tanggal dokumen telah terverifikasi valid.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-muted/90 border-b border-border text-[11px] uppercase font-mono font-bold tracking-wider text-slate-200">
                    <th className="px-3 py-2.5 w-28">Tingkat</th>
                    <th className="px-3 py-2.5 w-24">Aturan</th>
                    <th className="px-3 py-2.5 min-w-[200px]">Deskripsi Temuan & Pesan</th>
                    <th className="px-3 py-2.5 w-48">Koordinat Sumber</th>
                    <th className="px-3 py-2.5 w-28 text-center">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border font-mono text-[11px]">
                  {deterministicFindings.map((finding) => {
                    const isBlock = finding.severity === "BLOCK";
                    const isWarning = finding.severity === "WARNING";

                    return (
                      <tr
                        key={finding.id}
                        className={`hover:bg-muted/30 transition-colors ${
                          isBlock ? "bg-red-500/10" : isWarning ? "bg-amber-500/10" : ""
                        }`}
                      >
                        {/* Severity Badge */}
                        <td className="px-3 py-2 whitespace-nowrap">
                          {isBlock ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/15 text-red-300 border border-red-500/30">
                              [ 🔴 BLOCK ]
                            </span>
                          ) : isWarning ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                              [ 🟡 WARNING ]
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/15 text-sky-300 border border-sky-500/30">
                              [ ℹ️ INFO ]
                            </span>
                          )}
                        </td>

                        {/* Rule Code */}
                        <td className="px-3 py-2 font-bold text-foreground whitespace-nowrap">
                          {finding.rule_code}
                        </td>

                        {/* Message & Difference */}
                        <td className="px-3 py-2 font-sans text-foreground leading-relaxed">
                          <div>{finding.message}</div>
                          {(finding.current_value || finding.expected_value) && (
                            <div className="mt-1 text-[10px] font-mono text-muted-foreground">
                              Nilai saat ini:{" "}
                              <span className="text-red-400 font-bold">{finding.current_value || "-"}</span> |
                              Harapan:{" "}
                              <span className="text-emerald-400 font-bold">
                                {finding.expected_value || "-"}
                              </span>
                            </div>
                          )}
                        </td>

                        {/* Coordinate Breadcrumb */}
                        <td className="px-3 py-2 text-muted-foreground whitespace-nowrap font-mono text-[10px]">
                          {finding.sheet_name ? (
                            <span>
                              {finding.sheet_name}
                              {finding.cell_coordinate ? ` → ${finding.cell_coordinate}` : ""}
                            </span>
                          ) : (
                            "-"
                          )}
                        </td>

                        {/* Action Button */}
                        <td className="px-3 py-2 text-center whitespace-nowrap">
                          <button
                            type="button"
                            onClick={() => {
                              if (finding.rule_code.includes("BR07") || finding.rule_code.includes("DATE")) {
                                onNavigateToField("dates");
                              } else if (finding.rule_code.includes("BR13") || finding.rule_code.includes("LOGISTIC")) {
                                onNavigateToField("logistics");
                              } else if (finding.rule_code.includes("BR01") || finding.rule_code.includes("BR09")) {
                                onNavigateToField("identity");
                              } else {
                                onNavigateToField("items");
                              }
                            }}
                            className="flex items-center justify-center gap-1 px-2 py-0.5 rounded bg-muted/60 hover:bg-muted text-foreground border border-border text-[10px] font-medium transition mx-auto"
                          >
                            <ExternalLink className="w-3 h-3" />
                            <span>Tinjau</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* 6. Sub-Tab 2: AI Semantic Audit Evaluation & Analysis */}
      {activeSubTab === "ai_audit" && (
        <div className="space-y-4 animate-in fade-in duration-150">
          {/* Header Evaluation Status Card */}
          <div className="border border-border rounded-lg bg-card p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-amber-400" />
                <h3 className="font-mono text-xs uppercase font-bold tracking-wider text-foreground">
                  Status Hasil Audit Teks AI (Semantik)
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border ${
                    revision.ai_review_status === "COMPLETED"
                      ? resolvedAIDiscrepancies.length > 0
                        ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
                        : "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                      : revision.ai_review_status === "MANUAL_REVIEW_RECORDED"
                      ? "bg-sky-500/10 text-sky-300 border-sky-500/30"
                      : (revision.ai_review_status as string) === "BUDGET_EXCEEDED"
                      ? "bg-rose-500/10 text-rose-300 border-rose-500/30"
                      : "bg-muted text-muted-foreground border-border"
                  }`}
                >
                  {revision.ai_review_status === "COMPLETED"
                    ? resolvedAIDiscrepancies.length > 0
                      ? "SELESAI (ADA TEMUAN)"
                      : "SELESAI (BERSIH 100%)"
                    : revision.ai_review_status}
                </span>
                <span className="text-[10px] font-mono text-muted-foreground">
                  {resolvedAIDiscrepancies.length} Diskrepansi
                </span>
              </div>
            </div>

            {/* Narrative Summary from Engine */}
            <div className="p-3 rounded-md bg-muted/40 border border-border text-xs leading-relaxed font-sans text-foreground">
              {aiAuditResult?.summary || (
                revision.ai_review_status === "COMPLETED"
                  ? resolvedAIDiscrepancies.length > 0
                    ? `Audit semantik menemukan ${resolvedAIDiscrepancies.length} variasi penamaan atau substitusi merek antar lembar dokumen cetak (D01 s.d D05). Periksa rincian analisis di bawah.`
                    : "Pemeriksaan semantik lengkap: Semua deskripsi barang, spesifikasi, dan satuan konsisten di seluruh lembar dokumen cetak (D01 s.d D06)."
                  : revision.ai_review_status === "MANUAL_REVIEW_RECORDED"
                  ? "Verifikasi manual telah dicatat secara resmi oleh staf pemeriksa. Paket diizinkan untuk diajukan tanpa pemblokiran sistem."
                  : (revision.ai_review_status as string) === "BUDGET_EXCEEDED"
                  ? "Batas anggaran AI bulanan telah tercapai. Anda dapat mencatat verifikasi manual untuk melanjutkan alur persetujuan."
                  : "Audit teks AI belum dijalankan. Klik tombol 'Audit Teks AI (Semantik)' di atas untuk memeriksa konsistensi lintas dokumen secara otomatis."
              )}
            </div>
          </div>

          {/* Fallback Warning Card if Budget Exceeded or Failed */}
          {(revision.ai_review_status as string) === "BUDGET_EXCEEDED" && (
            <div className="p-4 rounded-lg border border-amber-500/30 bg-amber-500/10 text-xs flex items-center justify-between gap-3">
              <div>
                <h4 className="font-bold text-amber-200 font-mono">Batas Kuota AI Bulanan Tercapai</h4>
                <p className="text-[11px] text-amber-300/80 mt-0.5 font-sans">
                  Sistem beralih ke kebijakan verifikasi manual (PRD FR05 & AT16). Anda dapat mencatat verifikasi fisik tanpa memblokir pengajuan paket.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsRecordingManual(true)}
                className="px-3 py-1.5 rounded bg-amber-500 text-black font-semibold text-xs hover:opacity-90 transition shrink-0"
              >
                Catat Verifikasi Manual
              </button>
            </div>
          )}

          {/* List of Evaluated Discrepancies */}
          {resolvedAIDiscrepancies.length > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <span className="font-mono text-[11px] uppercase tracking-wider font-bold text-muted-foreground">
                  Rincian Analisis & Rekomendasi Respons AI ({resolvedAIDiscrepancies.length} Item)
                </span>
                <span className="text-[10px] text-muted-foreground font-mono">
                  Advisory Mode (Tidak Menghentikan Alur Persetujuan)
                </span>
              </div>

              {resolvedAIDiscrepancies.map((item, idx) => {
                const itemKey = `disc_${item.line_number || idx}_${item.sheet_a || "a"}_${item.sheet_b || "b"}`;
                const isExpanded = Boolean(expandedReasoning[itemKey]);

                // Badge styling per discrepancy type
                const isBrand = item.discrepancy_type === "BRAND_SUBSTITUTION";
                const isSpec = item.discrepancy_type === "SPECIFICATION_MISMATCH" || item.discrepancy_type === "SPEC_CONTRADICTION";
                const isUnit = item.discrepancy_type === "UNIT_INCOMPATIBILITY" || item.discrepancy_type === "UNIT_MISMATCH";

                return (
                  <div
                    key={itemKey}
                    className="border border-border rounded-lg bg-card p-4 space-y-3 transition-all hover:border-muted-foreground/40 shadow-xs"
                  >
                    {/* Item Header */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {/* Discrepancy Type Badge */}
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                            isBrand
                              ? "bg-purple-500/15 text-purple-300 border-purple-500/30"
                              : isSpec
                              ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
                              : isUnit
                              ? "bg-sky-500/15 text-sky-300 border-sky-500/30"
                              : "bg-slate-500/15 text-slate-300 border-slate-500/30"
                          }`}
                        >
                          {item.discrepancy_type}
                        </span>

                        {/* Severity Badge */}
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                            item.severity === "WARNING"
                              ? "bg-amber-500/10 text-amber-300 border border-amber-500/30"
                              : "bg-sky-500/10 text-sky-300 border border-sky-500/30"
                          }`}
                        >
                          {item.severity}
                        </span>

                        <span className="text-[10px] font-mono text-muted-foreground">
                          Item Baris #{item.line_number || idx + 1}
                        </span>
                      </div>

                      {/* Documents Compared */}
                      <div className="flex items-center gap-1.5 text-[10px] font-mono bg-muted/60 px-2 py-0.5 rounded border border-border">
                        <FileText className="w-3 h-3 text-primary" />
                        <span className="font-bold text-foreground">{item.sheet_a || "D01"}</span>
                        <ArrowRight className="w-2.5 h-2.5 text-muted-foreground" />
                        <span className="font-bold text-foreground">{item.sheet_b || "D05"}</span>
                      </div>
                    </div>

                    {/* Text Inspection Box (Side-by-side) */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono">
                      <div className="p-2.5 rounded bg-muted/30 border border-border">
                        <span className="text-[10px] text-muted-foreground block uppercase font-bold">
                          Dokumen Sumber ({item.sheet_a || "D01 / HPS"}):
                        </span>
                        <span className="text-foreground font-semibold mt-0.5 block">
                          {item.item_name}
                        </span>
                      </div>
                      <div className="p-2.5 rounded bg-muted/30 border border-border">
                        <span className="text-[10px] text-muted-foreground block uppercase font-bold">
                          Dokumen Pembanding ({item.sheet_b || "D05 / Pesanan"}):
                        </span>
                        <span className="text-amber-300 font-semibold mt-0.5 block">
                          {item.message || item.item_name}
                        </span>
                      </div>
                    </div>

                    {/* Analysis Narrative */}
                    <div className="space-y-1">
                      <span className="text-[10px] font-mono uppercase font-bold text-muted-foreground block">
                        Analisis Evaluasi Semantik:
                      </span>
                      <p className="text-xs font-sans text-foreground leading-relaxed pl-2 border-l-2 border-primary/50">
                        {item.explanation || item.message}
                      </p>
                    </div>

                    {/* Actionable Response */}
                    <div className="p-2.5 rounded bg-primary/5 border border-primary/20 space-y-1">
                      <span className="text-[10px] font-mono uppercase font-bold text-primary block flex items-center gap-1">
                        <ShieldCheck className="w-3 h-3" />
                        Rekomendasi Tindakan Administratif:
                      </span>
                      <p className="text-xs font-sans text-foreground leading-relaxed">
                        {item.recommended_action}
                      </p>
                    </div>

                    {/* Collapsible Reasoning View */}
                    <div className="pt-1">
                      <button
                        type="button"
                        onClick={() => toggleReasoning(itemKey)}
                        className="flex items-center gap-1.5 text-[11px] font-mono text-primary hover:text-primary/80 transition font-semibold"
                      >
                        <Brain className="w-3.5 h-3.5 text-amber-400" />
                        <span>{isExpanded ? "Sembunyikan Penalaran AI" : "Lihat Penalaran / Alasan Mendalam AI"}</span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>

                      {isExpanded && (
                        <div className="mt-2.5 p-3 rounded-md bg-muted/60 border border-border space-y-2 text-[11px] font-mono animate-in fade-in duration-200">
                          <div className="flex items-center gap-1.5 text-foreground font-semibold">
                            <Bot className="w-3.5 h-3.5 text-sky-400" />
                            <span>Rasionalitas & Dasar Analisis Regulasi Pengadaan:</span>
                          </div>
                          <p className="text-muted-foreground font-sans leading-relaxed">
                            {isBrand
                              ? "Model AI mendeteksi perbedaan antara deskripsi generik dan penamaan merek dagang komersial. Berdasarkan etika pengadaan sekolah dan prinsip netralitas spesifikasi teknis, substitusi merek harus diverifikasi kesetaraan mutu dan dicatat resmi pada Berita Acara Klarifikasi & Negosiasi (D04) agar tidak menjadi temuan pemeriksaan administratif SPJ."
                              : isSpec
                              ? "Terdapat ketidaksesuaian parameter numerik/kapasitas (misal volume, gramatur, atau dimensi) antar lembar dokumen perencanaan (HPS) dan realisasi pesanan. Evaluasi ini memastikan barang yang diserahterimakan tidak mengalami penurunan spesifikasi teknis (downgrade)."
                              : isUnit
                              ? "Satuan hitung barang antar dokumen berbeda (misal rim vs lembar, pak vs botol). Ketidakkonsistenan satuan berisiko menimbulkan kesalahan kalkulasi total kuantitas pada laporan fisik barang dan berita acara serah terima (D06)."
                              : "Pemeriksaan semantik mengidentifikasi variasi penulisan atau singkatan teks yang memerlukan verifikasi konsistensi dokumen SPJ resmi."}
                          </p>
                          <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[10px] text-muted-foreground">
                            <span>
                              Tingkat Keparahan:{" "}
                              <strong className={item.severity === "WARNING" ? "text-amber-400" : "text-sky-400"}>
                                {item.severity}
                              </strong>{" "}
                              (Advisori)
                            </span>
                            <span>Kepatuhan: PRD FR05 & AT16</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            revision.ai_review_status === "COMPLETED" && (
              <div className="border border-emerald-500/30 bg-emerald-500/10 p-6 rounded-lg text-center font-mono">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                <h4 className="text-sm font-bold text-emerald-200">Evaluasi Semantik Bersih (100% Konsisten)</h4>
                <p className="text-xs text-emerald-300/80 mt-1 font-sans max-w-md mx-auto leading-relaxed">
                  Semua deskripsi nama barang, merek, dan spesifikasi konsisten di seluruh lembar cetak dokumen D01 hingga D06. Tidak ditemukan indikasi substitusi merek atau kontradiksi spesifikasi.
                </p>
              </div>
            )
          )}
        </div>
      )}

      {/* 7. Manual Review Recording Modal */}
      {isRecordingManual && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
          <div className="bg-card border border-border w-full max-w-md rounded-lg shadow-xl overflow-hidden font-sans">
            <div className="px-4 py-3 border-b border-border flex items-center gap-2 bg-primary/10">
              <FileSignature className="w-4 h-4 text-primary" />
              <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
                Catat Verifikasi Manual (Fallback PRD FR05 & AT16)
              </h3>
            </div>

            <div className="p-4 space-y-3 text-xs">
              <p className="text-muted-foreground leading-relaxed">
                Gunakan opsi ini jika kuota AI bulanan telah tercapai atau server offline. Verifikasi manual
                akan mencatat nama Anda ke dalam audit trail dan mengizinkan paket untuk diajukan.
              </p>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Catatan Hasil Verifikasi Manual
                </label>
                <textarea
                  rows={3}
                  value={manualReviewNotes}
                  onChange={(e) => setManualReviewNotes(e.target.value)}
                  placeholder="Contoh: Seluruh nama barang dan spesifikasi fisik telah dicocokkan langsung dengan dokumen cetak resmi sekolah."
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsRecordingManual(false)}
                  className="px-3 py-1.5 text-xs rounded border border-border bg-card hover:bg-muted text-foreground transition"
                >
                  Batal
                </button>
                <button
                  type="button"
                  onClick={handleRecordManualReview}
                  className="px-3 py-1.5 text-xs font-semibold rounded bg-primary hover:opacity-90 text-primary-foreground transition shadow-xs"
                >
                  Simpan Catatan
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
