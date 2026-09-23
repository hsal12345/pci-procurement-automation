"use client";

import { useState } from "react";
import { AlertOctagon, RotateCcw, CopyPlus, X } from "lucide-react";

interface ConflictModalProps {
  isOpen: boolean;
  packageId: string;
  serverVersion: number;
  localVersion: number;
  onReloadServer: () => Promise<void>;
  onSaveAsNewRevision: () => Promise<void>;
  onClose: () => void;
}

export function ConflictModal({
  isOpen,
  packageId,
  serverVersion,
  localVersion,
  onReloadServer,
  onSaveAsNewRevision,
  onClose,
}: ConflictModalProps) {
  const [isProcessing, setIsProcessing] = useState(false);

  if (!isOpen) return null;

  const handleReload = async () => {
    setIsProcessing(true);
    try {
      await onReloadServer();
      onClose();
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReopen = async () => {
    setIsProcessing(true);
    try {
      await onSaveAsNewRevision();
      onClose();
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4">
      <div className="bg-card border border-red-800/80 w-full max-w-lg rounded-lg shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="px-4 py-3 bg-red-950/40 border-b border-red-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertOctagon className="w-5 h-5 text-red-400" />
            <h3 className="text-xs font-bold text-red-200 uppercase tracking-wider font-mono">
              [ 🔴 HTTP 409: Konflik Konkurensi Optimistik ]
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-muted-foreground hover:text-foreground rounded"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 text-xs">
          <p className="text-foreground leading-relaxed">
            Paket transaksi ini telah diubah atau diajukan oleh pengguna lain pada saat Anda sedang menyunting.
          </p>

          <div className="border border-border rounded bg-muted/20 p-3 font-mono text-[11px] space-y-1.5">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Versi token lokal Anda:</span>
              <span className="font-bold text-amber-400">Versi {localVersion}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Versi aktif di server:</span>
              <span className="font-bold text-emerald-400">Versi {serverVersion}</span>
            </div>
          </div>

          <p className="text-muted-foreground leading-relaxed">
            Untuk mencegah data tertimpa secara tidak sengaja, pilih salah satu tindakan rekonsiliasi berikut:
          </p>

          {/* Action Paths (Finding #7) */}
          <div className="space-y-2 pt-2">
            {/* Action 1: Reload Server Version */}
            <button
              type="button"
              disabled={isProcessing}
              onClick={handleReload}
              className="w-full p-3 rounded-lg border border-border bg-muted/40 hover:bg-muted text-left transition flex items-start gap-3 group"
            >
              <RotateCcw className="w-4 h-4 text-sky-400 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-foreground block group-hover:text-primary transition font-mono text-xs">
                  [ Muat Ulang Versi Server ]
                </span>
                <span className="text-[11px] text-muted-foreground block mt-0.5">
                  Membatalkan perubahan lokal yang belum disimpan dan memuat data revisi terbaru dari database.
                </span>
              </div>
            </button>

            {/* Action 2: Save as New Revision N+1 */}
            <button
              type="button"
              disabled={isProcessing}
              onClick={handleReopen}
              className="w-full p-3 rounded-lg border border-amber-800/80 bg-amber-950/20 hover:bg-amber-950/40 text-left transition flex items-start gap-3 group"
            >
              <CopyPlus className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-amber-300 block group-hover:text-amber-200 transition font-mono text-xs">
                  [ Simpan Sebagai Revisi Baru (N+1) ]
                </span>
                <span className="text-[11px] text-amber-200/80 block mt-0.5">
                  Membuat draf revisi berikutnya secara otomatis tanpa menimpa data versi yang bertabrakan.
                </span>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
