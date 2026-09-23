"use client";

import { useState } from "react";
import { AlertCircle, Check } from "lucide-react";

interface ZeroPriceModalProps {
  isOpen: boolean;
  itemNumber: number;
  itemDescription: string;
  initialReason?: string;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

export function ZeroPriceModal({
  isOpen,
  itemNumber,
  itemDescription,
  initialReason = "",
  onConfirm,
  onCancel,
}: ZeroPriceModalProps) {
  const [reason, setReason] = useState(initialReason);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      alert("Alasan barang bernilai Rp 0 wajib diisi (misal: Sampel Gratis / Bonus Pengadaan).");
      return;
    }
    onConfirm(reason.trim());
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
      <div className="bg-card border border-border w-full max-w-md rounded-lg shadow-xl overflow-hidden font-sans">
        <div className="px-4 py-3 border-b border-border flex items-center gap-2 bg-amber-950/20">
          <AlertCircle className="w-4 h-4 text-amber-400" />
          <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
            Konfirmasi Barang Bernilai Rp 0 (Gratis/Bonus)
          </h3>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-3 text-xs">
          <p className="text-muted-foreground">
            Barang baris <span className="font-mono font-bold text-foreground">#{itemNumber}</span> (
            <span className="font-semibold text-foreground">{itemDescription}</span>) diatur dengan harga
            final <span className="font-mono text-amber-400 font-bold">Rp 0,00</span>.
          </p>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Alasan Barang Tanpa Biaya (Wajib)
            </label>
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Contoh: Bonus pengadaan dari rekanan, sampel buku pengenalan kurikulum..."
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
              autoFocus
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onCancel}
              className="px-3 py-1 text-xs rounded border border-border bg-muted/40 hover:bg-muted text-muted-foreground transition"
            >
              Batal
            </button>
            <button
              type="submit"
              className="flex items-center gap-1 px-3 py-1 text-xs font-semibold rounded bg-amber-500 hover:bg-amber-400 text-black transition"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Konfirmasi Alasan</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
