"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PackageItem, PackageRevision, UserRole } from "@/types/package";
import { apiClient } from "@/lib/api-client";
import { formatIDR } from "@/lib/formatters";
import {
  CheckCircle2,
  AlertTriangle,
  Send,
  RotateCcw,
  ShieldCheck,
  Printer,
  FileCheck2,
  Lock,
  XCircle,
  Eye,
  Loader2,
  Trash2,
} from "lucide-react";

interface WorkspaceHeaderProps {
  packageData: PackageItem;
  revision: PackageRevision;
  currentRole: UserRole;
  isDirty: boolean;
  isSaving: boolean;
  onSave: () => Promise<number | null | void>;
  onRefresh: () => Promise<void>;
  onOpenApproval: () => void;
  onOpenRejection: () => void;
  onOpenReopen: () => void;
  onOpenCancel: () => void;
  onSwitchTab: (tabKey: string) => void;
  hasLogisticsDispute?: boolean;
  blockingErrorsCount?: number;
}

export function WorkspaceHeader({
  packageData,
  revision,
  currentRole,
  isDirty,
  isSaving,
  onSave,
  onRefresh,
  onOpenApproval,
  onOpenRejection,
  onOpenReopen,
  onOpenCancel,
  onSwitchTab,
  hasLogisticsDispute = false,
  blockingErrorsCount = 0,
}: WorkspaceHeaderProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isIssuing, setIsIssuing] = useState(false);

  const status = revision.status;
  const isDraft = status === "DRAFT" || status === "RETURNED";
  const isUnderReview = status === "UNDER_REVIEW";
  const isApproved = status === "APPROVED";
  const isIssued = status === "ISSUED";
  const isCancelled = status === "CANCELLED";

  const schoolName = revision.school_snapshot?.name || "Nama Sekolah Belum Diatur";

  const handleSubmit = async () => {
    if (hasLogisticsDispute) {
      alert("Tidak dapat mengajukan: Transaksi memiliki pengiriman rusak/tidak lengkap (di luar alur pilot).");
      return;
    }
    let targetVersion = revision.version;
    if (isDirty) {
      const savedVer = await onSave();
      if (typeof savedVer === "number") {
        targetVersion = savedVer;
      }
    }
    setIsSubmitting(true);
    try {
      await apiClient.submitRevision(revision.id, targetVersion, "Diajukan untuk persetujuan");
      await onRefresh();
    } catch (err: any) {
      alert(`Gagal mengajukan persetujuan: ${err.message || err}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleIssue = async () => {
    if (!confirm("Apakah Anda yakin ingin menerbitkan dokumen resmi tanpa watermark (Final Issuance)?")) {
      return;
    }
    setIsIssuing(true);
    try {
      await apiClient.issueRevision(packageData.id, revision.id);
      await onRefresh();
      alert("Paket dokumen resmi berhasil diterbitkan!");
    } catch (err: any) {
      alert(`Penerbitan gagal: ${err.message || err}`);
    } finally {
      setIsIssuing(false);
    }
  };

  const router = useRouter();
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteDraft = async () => {
    const pkgCode = packageData.package_code || packageData.package_number || "Paket Ini";
    if (
      !confirm(
        `Apakah Anda yakin ingin menghapus permanen draf paket pengadaan ${pkgCode}? Seluruh revisi dan data terkait akan dihapus secara permanen.`
      )
    ) {
      return;
    }
    setIsDeleting(true);
    try {
      await apiClient.deletePackage(packageData.id);
      alert(`Draf paket pengadaan ${pkgCode} berhasil dihapus.`);
      router.push("/packages");
    } catch (err: any) {
      alert(`Gagal menghapus draf: ${err.message || err}`);
      setIsDeleting(false);
    }
  };

  return (
    <header className="border-b border-border bg-card select-none">
      {/* Top Metadata Strip */}
      <div className="px-4 py-2 flex flex-wrap items-center justify-between gap-3 border-b border-border/80">
        <div className="flex items-center gap-3 text-xs">
          {/* Package ID & School */}
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-foreground bg-muted px-2 py-0.5 rounded border border-border">
              {packageData.package_code || packageData.package_number || "PKG"}
            </span>

            <span className="font-semibold text-foreground truncate max-w-sm" title={schoolName}>
              {schoolName}
            </span>
          </div>

          <span className="text-muted-foreground">|</span>

          {/* Fiscal Year & Fund Source */}
          <div className="flex items-center gap-2 font-mono text-muted-foreground text-[11px]">
            <span>TA {packageData.fiscal_year} TW {packageData.quarter}</span>
            <span>•</span>
            <span className="text-foreground font-medium">{packageData.fund_source}</span>
          </div>

          <span className="text-muted-foreground">|</span>

          {/* Revision & Version */}
          <div className="flex items-center gap-1.5 font-mono text-[11px]">
            <span className="font-medium text-foreground">
              Rev {revision.revision_number} (v{revision.version})
            </span>
            {revision.is_locked && (
              <span className="flex items-center gap-0.5 text-amber-400" title="Terkunci dari penyuntingan langsung">
                <Lock className="w-3 h-3" />
              </span>
            )}
          </div>

          <span className="text-muted-foreground">|</span>

          {/* Status Badge */}
          <StatusBadge status={status} />
        </div>

        {/* Right side: Save state & Grand total */}
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            {isSaving ? (
              <span className="flex items-center gap-1 text-muted-foreground text-[11px]">
                <Loader2 className="w-3 h-3 animate-spin" /> Menyimpan...
              </span>
            ) : isDirty ? (
              <span className="flex items-center gap-1 text-amber-400 text-[11px]">
                <AlertTriangle className="w-3 h-3" /> Perubahan Belum Disimpan
              </span>
            ) : (
              <span className="flex items-center gap-1 text-emerald-400 text-[11px]">
                <CheckCircle2 className="w-3 h-3" /> Tersimpan
              </span>
            )}
          </div>

          <div className="pl-3 border-l border-border flex items-center gap-2">
            <span className="text-[10px] uppercase text-muted-foreground">Total Akhir:</span>
            <span className="font-bold text-foreground tabular-nums text-sm">
              {formatIDR(revision.grand_total)}
            </span>
          </div>
        </div>
      </div>

      {/* Action Toolbar */}
      <div className="px-4 py-1.5 bg-muted/20 flex flex-wrap items-center justify-between gap-2 text-xs">
        {/* Left Action Shortcuts */}
        <div className="flex items-center gap-1.5">
          {/* Run Validation */}
          <button
            type="button"
            onClick={() => onSwitchTab("inspection")}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-muted/60 hover:bg-muted text-foreground border border-border transition text-[11px] font-medium"
          >
            <FileCheck2 className="w-3.5 h-3.5" />
            <span>Pemeriksaan Sistem</span>
            {blockingErrorsCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded bg-red-500/20 text-red-300 font-mono text-[9px] border border-red-500/40 font-bold">
                {blockingErrorsCount} BLOCK
              </span>
            )}
          </button>

          {/* Preview Draft */}
          <button
            type="button"
            onClick={() => onSwitchTab("documents")}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-muted/60 hover:bg-muted text-foreground border border-border transition text-[11px] font-medium"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Pratinjau Dokumen</span>
          </button>

          {/* Manual Save button if dirty */}
          {isDraft && !revision.is_locked && (
            <button
              type="button"
              onClick={onSave}
              disabled={!isDirty || isSaving}
              className={`px-2.5 py-1 rounded text-[11px] font-medium border transition ${
                isDirty
                  ? "bg-primary text-primary-foreground border-primary hover:opacity-90"
                  : "bg-muted/40 text-muted-foreground border-border cursor-not-allowed"
              }`}
            >
              Simpan Perubahan
            </button>
          )}
        </div>

        {/* Right Workflow Actions conditioned on Role & State */}
        <div className="flex items-center gap-2">
          {/* DRAFT / RETURNED: Admin can submit */}
          {isDraft && !revision.is_locked && (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting || hasLogisticsDispute || blockingErrorsCount > 0}
              className={`flex items-center gap-1.5 px-3 py-1 rounded text-[11px] font-semibold border transition ${
                hasLogisticsDispute || blockingErrorsCount > 0
                  ? "bg-muted text-muted-foreground border-border cursor-not-allowed"
                  : "bg-primary text-primary-foreground border-primary hover:opacity-90"
              }`}
              title={
                hasLogisticsDispute
                  ? "Pengiriman bermasalah (RUSAK). Tidak dapat diajukan."
                  : blockingErrorsCount > 0
                  ? `Terdapat ${blockingErrorsCount} kesalahan memblokir (BLOCK). Perbaiki terlebih dahulu.`
                  : "Ajukan paket ke Direktur Keuangan untuk persetujuan"
              }
            >
              {isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
              <span>Ajukan Persetujuan</span>
            </button>
          )}

          {/* UNDER_REVIEW: Finance Director can return or approve */}
          {isUnderReview && (currentRole === "FINANCE_DIRECTOR" || currentRole === "SYSTEM_ADMINISTRATOR") && (
            <>
              <button
                type="button"
                onClick={onOpenRejection}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-red-500/15 text-red-300 border border-red-500/40 hover:bg-red-500/25 text-[11px] font-medium transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Kembalikan</span>
              </button>
              <button
                type="button"
                onClick={onOpenApproval}
                className="flex items-center gap-1 px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold transition"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Tinjau & Setujui</span>
              </button>
            </>
          )}

          {/* APPROVED: Admin or Finance can issue official documents */}
          {isApproved && (
            <button
              type="button"
              onClick={handleIssue}
              disabled={isIssuing || hasLogisticsDispute}
              className="flex items-center gap-1.5 px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold transition shadow-sm"
              title="Terbitkan paket dokumen resmi tanpa watermark"
            >
              {isIssuing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Printer className="w-3.5 h-3.5" />}
              <span>Terbitkan Dokumen Resmi</span>
            </button>
          )}

          {/* Reopen New Revision N+1 (Allowed when APPROVED or ISSUED) */}
          {(isApproved || isIssued) && (
            <button
              type="button"
              onClick={onOpenReopen}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-muted/60 hover:bg-muted text-foreground border border-border text-[11px] font-medium transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Buka Revisi Baru</span>
            </button>
          )}

          {/* Delete Draft Package (ADMINISTRATION & SYSTEM_ADMINISTRATOR) */}
          {isDraft && (currentRole === "ADMINISTRATION" || currentRole === "SYSTEM_ADMINISTRATOR") && (
            <button
              type="button"
              onClick={handleDeleteDraft}
              disabled={isDeleting}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-red-500/15 text-red-300 border border-red-500/40 hover:bg-red-500/25 text-[11px] font-medium transition"
              title="Hapus draf paket pengadaan ini secara permanen"
            >
              {isDeleting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Trash2 className="w-3.5 h-3.5 text-red-400" />
              )}
              <span>Hapus Draf</span>
            </button>
          )}

          {/* Cancel Package (State-contingent RBAC) */}
          {!isCancelled && !isIssued && (
            <button
              type="button"
              onClick={onOpenCancel}
              className="flex items-center gap-1 px-2 py-1 rounded hover:bg-red-500/15 text-muted-foreground hover:text-red-400 text-[11px] transition"
              title="Batalkan paket pengadaan ini"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Batalkan</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "ISSUED") {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
        [ 🟢 ISSUED ]
      </span>
    );
  }
  if (status === "APPROVED") {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-teal-500/15 text-teal-300 border border-teal-500/30">
        [ 🟢 APPROVED ]
      </span>
    );
  }
  if (status === "UNDER_REVIEW") {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
        [ 🟡 UNDER REVIEW ]
      </span>
    );
  }
  if (status === "RETURNED") {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-red-500/15 text-red-300 border border-red-500/30">
        [ 🔴 RETURNED ]
      </span>
    );
  }
  if (status === "CANCELLED") {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-zinc-500/15 text-zinc-300 border border-zinc-500/30">
        [ ✕ CANCELLED ]
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-500/15 text-blue-300 border border-blue-500/30">
      [ ⚪ DRAFT ]
    </span>
  );
}
