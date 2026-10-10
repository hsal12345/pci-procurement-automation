"use client";

import { useState } from "react";
import { PackageRevision } from "@/types/package";
import { apiClient } from "@/lib/api-client";
import { formatIDR } from "@/lib/formatters";
import { ShieldCheck, RotateCcw, AlertTriangle, Hash, Check, X, Loader2 } from "lucide-react";

interface ApprovalModalProps {
  isOpen: boolean;
  revision: PackageRevision;
  onSuccess: () => Promise<void>;
  onClose: () => void;
}

export function ApprovalModal({ isOpen, revision, onSuccess, onClose }: ApprovalModalProps) {
  const [isConfirmChecked, setIsConfirmChecked] = useState(false);
  const [approvalNote, setApprovalNote] = useState("");
  const [isRejecting, setIsRejecting] = useState(false);
  const [returnComment, setReturnComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleApprove = async () => {
    if (!isConfirmChecked) {
      alert("Harap centang konfirmasi verifikasi kepatuhan terlebih dahulu.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiClient.approveRevision(
        revision.id,
        revision.version,
        undefined,
        approvalNote || "Disetujui oleh Direktur Keuangan"
      );
      alert("Paket pengadaan berhasil disetujui (APPROVED).");
      await onSuccess();
      onClose();
    } catch (err: any) {
      alert(`Persetujuan gagal: ${err.message || err}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReturn = async () => {
    if (!returnComment.trim()) {
      alert("Alasan pengembalian berkas untuk perbaikan wajib diisi.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiClient.returnRevision(revision.id, revision.version, returnComment.trim());
      alert("Paket berhasil dikembalikan ke staf administrasi (RETURNED).");
      await onSuccess();
      onClose();
    } catch (err: any) {
      alert(`Gagal mengembalikan berkas: ${err.message || err}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4">
      <div className="bg-card border border-border w-full max-w-xl rounded-lg shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="px-4 py-3 bg-muted/40 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
              Persetujuan Dokumen Resmi — Direktur Keuangan (PRD Section 9)
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body Content */}
        <div className="p-5 space-y-4 text-xs">
          {/* Summary Box */}
          <div className="border border-border rounded bg-muted/20 p-3 space-y-2 font-mono text-[11px]">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Lembaga Sekolah:</span>
              <span className="font-semibold text-foreground">
                {revision.school_snapshot?.name || "-"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Revisi & Versi Token:</span>
              <span className="font-bold text-foreground">
                Revisi {revision.revision_number} (v{revision.version})
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Jumlah Baris Barang:</span>
              <span className="font-bold text-foreground">{revision.lines?.length || 0} Barang</span>
            </div>
            <div className="flex justify-between pt-1 border-t border-border">
              <span className="text-muted-foreground uppercase font-bold">Grand Total Transaksi:</span>
              <span className="font-bold text-emerald-400 text-sm">
                {formatIDR(revision.grand_total)}
              </span>
            </div>
          </div>

          {!isRejecting ? (
            /* Approval Form */
            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Catatan Persetujuan (Opsional)
                </label>
                <input
                  type="text"
                  value={approvalNote}
                  onChange={(e) => setApprovalNote(e.target.value)}
                  placeholder="Contoh: Telah disetujui sesuai alokasi dana BOS TW II 2026."
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              {/* Mandatory Confirmation Checkbox */}
              <label className="flex items-start gap-2.5 p-3 rounded bg-card border border-border cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isConfirmChecked}
                  onChange={(e) => setIsConfirmChecked(e.target.checked)}
                  className="mt-0.5 rounded border-border text-primary focus:ring-2 focus:ring-primary/40"
                />
                <span className="text-[11px] text-foreground leading-snug">
                  Saya mengonfirmasi bahwa perhitungan aritmatika, kebijakan pajak, tanggal kronologis,
                  dan kelengkapan 13 dokumen telah diverifikasi dan tidak mengandung kesalahan memblokir.
                </span>
              </label>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsRejecting(true)}
                  className="text-red-400 hover:text-red-300 font-medium text-xs flex items-center gap-1 transition"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Kembalikan untuk Koreksi</span>
                </button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-3 py-1.5 text-xs rounded border border-border bg-card hover:bg-muted text-foreground transition"
                  >
                    Batal
                  </button>
                  <button
                    type="button"
                    onClick={handleApprove}
                    disabled={!isConfirmChecked || isSubmitting}
                    className={`flex items-center gap-1 px-4 py-1.5 text-xs font-semibold rounded transition shadow-xs ${
                      isConfirmChecked && !isSubmitting
                        ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                        : "bg-muted text-muted-foreground cursor-not-allowed"
                    }`}
                  >
                    {isSubmitting ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Check className="w-3.5 h-3.5" />
                    )}
                    <span>Setujui & Kunci</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* Rejection / Return Form */
            <div className="space-y-3 border-t border-border pt-3">
              <div className="flex items-center gap-1.5 text-red-400 font-mono font-bold text-xs uppercase">
                <AlertTriangle className="w-4 h-4" />
                <span>Pengembalian Berkas ke Petugas Administrasi</span>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Alasan Koreksi / Catatan Perbaikan (Wajib)
                </label>
                <textarea
                  rows={3}
                  value={returnComment}
                  onChange={(e) => setReturnComment(e.target.value)}
                  placeholder="Jelaskan bagian yang perlu diperbaiki (misal: Tanggal Berita Acara mendahului Surat Pesanan, atau harga final melebihi HPS)..."
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                  autoFocus
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsRejecting(false)}
                  className="px-3 py-1.5 text-xs rounded border border-border bg-card hover:bg-muted text-foreground transition"
                >
                  Kembali ke Penyetujuan
                </button>
                <button
                  type="button"
                  onClick={handleReturn}
                  disabled={isSubmitting || !returnComment.trim()}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded bg-red-600 hover:bg-red-500 text-white transition shadow-xs"
                >
                  {isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                  <span>Kirim Perintah Koreksi</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
