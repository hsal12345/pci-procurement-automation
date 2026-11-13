"use client";

import { useState } from "react";
import { FileUp, X } from "lucide-react";
import { ImportWizard } from "@/components/imports/import-wizard";
import { ImportConfirmResponse } from "@/types/imports";

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (result?: ImportConfirmResponse) => void;
}

export function ImportModal({ isOpen, onClose, onSuccess }: ImportModalProps) {
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3>(1);

  if (!isOpen) return null;

  const handleSuccess = (result: ImportConfirmResponse) => {
    alert(
      `Berkas berhasil dikonfirmasi dan dibuat sebagai draf paket!\n` +
        `Nomor Paket: ${result.package_number}\n` +
        `Mode Pemetaan: ${result.mapping_source}\n` +
        `Nilai: Rp ${Number(result.grand_total).toLocaleString("id-ID")}`
    );
    onSuccess(result);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4 overflow-y-auto">
      <div
        className={`bg-card border border-border w-full rounded-lg shadow-2xl overflow-hidden font-sans my-auto transition-all ${
          wizardStep === 1 ? "max-w-xl" : "max-w-5xl"
        }`}
      >
        {/* Header */}
        <div className="px-4 py-3 bg-muted/40 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileUp className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
              Impor Dokumen Pengadaan &amp; Pemetaan AI (.xlsx, .pdf, .doc, .docx)
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

        {/* Wizard Content */}
        <div className="p-5 max-h-[85vh] overflow-y-auto">
          <ImportWizard
            onCancel={onClose}
            onStepChange={setWizardStep}
            onSuccess={handleSuccess}
          />
        </div>
      </div>
    </div>
  );
}
