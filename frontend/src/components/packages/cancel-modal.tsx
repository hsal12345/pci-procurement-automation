"use client";

import { useState } from "react";
import { XCircle, X, Loader2 } from "lucide-react";

interface CancelModalProps {
  isOpen: boolean;
  packageCode: string;
  onConfirm: (reason: string) => Promise<void>;
  onClose: () => void;
}

export function CancelModal({ isOpen, packageCode, onConfirm, onClose }: CancelModalProps) {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim() || reason.trim().length < 5) {
      alert("Alasan pembatalan paket pengadaan wajib diisi minimal 5 karakter.");
      return;
    }
    setIsSubmitting(true);
    try {
      await onConfirm(reason.trim());
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4">
      <div className="bg-card border border-red-500/40 w-full max-w-md rounded-lg shadow-2xl overflow-hidden font-sans">
        <div className="px-4 py-3 bg-red-500/15 border-b border-red-500/30 flex items-center justify-between">
          <div className="flex items-center gap-2 text-red-300 font-mono text-xs font-bold uppercase">
            <XCircle className="w-4 h-4 text-red-400" />
            <span>Batalkan Paket Pengadaan</span>
          </div>
          <button type="button" onClick={onClose} className="p-1 rounded hover:bg-red-500/20 text-muted-foreground hover:text-foreground transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-3 text-xs">
          <p className="text-foreground leading-relaxed">
            Apakah Anda yakin ingin membatalkan paket <span className="font-mono font-bold text-primary">{packageCode}</span>?
            Tindakan ini akan mengunci transaksi dan melepaskan nomor reservasi dokumen.
          </p>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Alasan Pembatalan Resmi (Wajib)
            </label>
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Contoh: Alokasi anggaran sekolah dibatalkan oleh dinas pendidikan..."
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
              autoFocus
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs rounded border border-border bg-card hover:bg-muted text-foreground transition"
            >
              Kembali
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !reason.trim()}
              className="flex items-center gap-1 px-3.5 py-1.5 text-xs font-semibold rounded bg-red-600 hover:bg-red-500 text-white transition disabled:opacity-50"
            >
              {isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />}
              <span>Konfirmasi Pembatalan</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
