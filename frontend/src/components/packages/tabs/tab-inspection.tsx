"use client";

import { useState } from "react";
import { PackageRevision } from "@/types/package";
import { Finding, ValidationRun } from "@/types/validation";
import { apiClient } from "@/lib/api-client";
import {
  FileCheck2,
  AlertOctagon,
  AlertTriangle,
  Info,
  RotateCcw,
  Sparkles,
  ExternalLink,
  CheckCircle,
  Loader2,
  FileSignature,
} from "lucide-react";

interface TabInspectionProps {
  revision: PackageRevision;
  validationRun?: ValidationRun | null;
  onRefresh: () => Promise<void>;
  onNavigateToField: (tabKey: string, fieldId?: string) => void;
}

export function TabInspection({
  revision,
  validationRun,
  onRefresh,
  onNavigateToField,
}: TabInspectionProps) {
  const [isValidating, setIsValidating] = useState(false);
  const [isAuditingAI, setIsAuditingAI] = useState(false);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [dispositionNote, setDispositionNote] = useState("");
  const [isRecordingManual, setIsRecordingManual] = useState(false);
  const [manualReviewNotes, setManualReviewNotes] = useState("");

  const findings = validationRun?.findings || [];
  const blockCount = findings.filter((f) => f.severity === "BLOCK").length;
  const warningCount = findings.filter((f) => f.severity === "WARNING").length;
  const infoCount = findings.filter((f) => f.severity === "INFO").length;

  const handleRunValidation = async () => {
    setIsValidating(true);
    try {
      await apiClient.validateRevision(revision.id);
      await onRefresh();
    } catch (err: any) {
      alert(`Validasi gagal: ${err.message || err}`);
    } finally {
      setIsValidating(false);
    }
  };

  const handleRunAIAudit = async () => {
    setIsAuditingAI(true);
    try {
      const resp = await apiClient.auditWithAI(revision.id);
      await onRefresh();
      alert(`Pemeriksaan teks AI selesai: ${resp.summary}`);
    } catch (err: any) {
      alert(`Audit AI gagal: ${err.message || err}`);
    } finally {
      setIsAuditingAI(false);
    }
  };

  const handleRecordManualReview = async () => {
    if (!manualReviewNotes.trim()) {
      alert("Catatan verifikasi manual wajib diisi.");
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
      alert("Verifikasi manual berhasil dicatat. Status AI telah diperbarui.");
    } catch (err: any) {
      alert(`Gagal mencatat verifikasi manual: ${err.message || err}`);
    }
  };

  return (
    <div className="p-6 max-w-5xl space-y-6 text-xs font-sans">
      {/* 1. Metric Cards Header */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {/* BLOCK */}
        <div className="border border-red-500/30 bg-red-500/10 p-4 rounded-lg flex items-center justify-between shadow-sm">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-red-300 font-bold block">
              Kesalahan Memblokir
            </span>
            <span className="text-2xl font-mono font-bold text-red-200 tabular-nums">
              {blockCount}
            </span>
            <span className="text-[10px] text-red-300/80 block mt-0.5">Wajib Diperbaiki</span>
          </div>
          <AlertOctagon className="w-6 h-6 text-red-400" />
        </div>

        {/* WARNING */}
        <div className="border border-amber-500/30 bg-amber-500/10 p-4 rounded-lg flex items-center justify-between shadow-sm">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-amber-300 font-bold block">
              Peringatan (Warnings)
            </span>
            <span className="text-2xl font-mono font-bold text-amber-200 tabular-nums">
              {warningCount}
            </span>
            <span className="text-[10px] text-amber-300/80 block mt-0.5">Dapat Didisposisi</span>
          </div>
          <AlertTriangle className="w-6 h-6 text-amber-400" />
        </div>

        {/* INFO */}
        <div className="border border-sky-500/30 bg-sky-500/10 p-4 rounded-lg flex items-center justify-between shadow-sm">
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
        <div className="border border-border bg-card p-4 rounded-lg flex items-center justify-between shadow-sm">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-bold block">
              Status Review Teks AI
            </span>
            <span className="text-xs font-mono font-bold text-foreground block mt-1">
              {revision.ai_review_status}
            </span>
            <span className="text-[10px] text-muted-foreground block mt-0.5">FR05 & AT16</span>
          </div>
          <Sparkles className="w-5 h-5 text-amber-400" />
        </div>
      </div>

      {/* 2. Action Trigger Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-y border-border py-2.5">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRunValidation}
            disabled={isValidating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary text-primary-foreground font-medium text-xs hover:opacity-90 transition"
          >
            {isValidating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
            <span>Jalankan Validasi Sistem (BR01-BR15)</span>
          </button>

          <button
            type="button"
            onClick={handleRunAIAudit}
            disabled={isAuditingAI}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-muted hover:bg-muted/80 text-foreground font-medium text-xs border border-border transition"
          >
            {isAuditingAI ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-amber-400" />}
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

      {/* 3. Findings Table */}
      <div className="border border-border rounded-lg bg-card overflow-hidden">
        <div className="px-4 py-2.5 bg-muted/40 border-b border-border flex items-center justify-between">
          <h3 className="font-semibold text-foreground text-xs uppercase tracking-wider font-mono">
            Daftar Temuan Kepatuhan Bisnis & Teks
          </h3>
          <span className="text-[10px] font-mono text-muted-foreground">
            {findings.length} Temuan Terdeteksi
          </span>
        </div>

        {findings.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground font-mono">
            <CheckCircle className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
            <p className="text-xs">
              Tidak ada temuan pelanggaran aturan bisnis (BR01-BR15). Paket valid untuk diajukan.
            </p>
          </div>
        ) : (
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
              {findings.map((finding) => {
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
        )}
      </div>

      {/* Manual Review Recording Modal */}
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
