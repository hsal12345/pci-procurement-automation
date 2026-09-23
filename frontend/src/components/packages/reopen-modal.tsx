"use client";

import { useState } from "react";
import { RotateCcw, X, Loader2 } from "lucide-react";

interface ReopenModalProps {
  isOpen: boolean;
  packageCode: string;
  currentRevisionNumber: number;
  onConfirm: (reason: string) => Promise<void>;
  onClose: () => void;
}

export function ReopenModal({
  isOpen,
  packageCode,
  currentRevisionNumber,
  onConfirm,
  onClose,
}: ReopenModalProps) {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim() || reason.trim().length < 5) {
      alert("Alasan pembukaan kembali paket wajib diisi minimal 5 karakter.");
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
      <div className="bg-card border border-border w-full max-w-md rounded-lg shadow-2xl overflow-hidden font-sans">
        <div className="px-4 py-3 bg-muted/40 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2 text-foreground font-mono text-xs font-bold uppercase">
            <RotateCcw className="w-4 h-4 text-amber-400" />
            <span>Buka Revisi Baru (Revisi {currentRevisionNumber + 1})</span>
          </div>
          <button type="button" onClick={onClose} className="p-1 rounded hover:bg-muted text-muted-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-3 text-xs">
          <p className="text-foreground leading-relaxed">
            Paket <span className="font-mono font-bold">{packageCode}</span> akan dikloning ke{" "}
            <span className="font-mono font-bold text-primary">Revisi {currentRevisionNumber + 1}</span> dalam
            status DRAFT. Seluruh berkas lama tetap aman dan berlaku sampai revisi baru diterbitkan.
          </p>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Alasan Pembukaan Revisi Baru (Wajib)
            </label>
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Contoh: Penyesuaian harga satuan buku semester 2 dan pergantian nama bendahara..."
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
              autoFocus
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs rounded border border-border bg-muted/40 hover:bg-muted text-muted-foreground"
            >
              Batal
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !reason.trim()}
              className="flex items-center gap-1 px-3.5 py-1.5 text-xs font-semibold rounded bg-primary text-primary-foreground hover:opacity-90 transition disabled:opacity-50"
            >
              {isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
              <span>Buat Revisi {currentRevisionNumber + 1}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
