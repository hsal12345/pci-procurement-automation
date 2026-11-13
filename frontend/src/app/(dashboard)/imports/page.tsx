"use client";

import { useState } from "react";
import { FileSpreadsheet, Sparkles, Download, Loader2, CheckCircle2 } from "lucide-react";
import { ImportWizard } from "@/components/imports/import-wizard";
import { apiClient } from "@/lib/api-client";
import { useRouter } from "next/navigation";
import { ImportConfirmResponse } from "@/types/imports";

export default function ImportsPage() {
  const [isDownloading, setIsDownloading] = useState(false);
  const router = useRouter();

  const handleDownloadTemplate = async () => {
    setIsDownloading(true);
    try {
      await apiClient.downloadImportTemplate();
    } catch (err: any) {
      alert(err.message || "Gagal mengunduh format template.");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleWizardSuccess = (result: ImportConfirmResponse) => {
    alert(
      `Berkas berhasil dikonfirmasi dan dibuat sebagai draf paket!\n` +
        `Nomor Paket: ${result.package_number}\n` +
        `Mode Pemetaan: ${result.mapping_source}\n` +
        `Nilai: Rp ${Number(result.grand_total).toLocaleString("id-ID")}`
    );
    router.push(`/packages/${result.package_id}`);
  };

  return (
    <div className="p-6 max-w-6xl space-y-6 text-xs font-sans">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="w-5 h-5 text-primary" />
          <h1 className="text-base font-semibold text-foreground">
            Impor Buku Kerja Spreadsheet Pengadaan & Konfirmasi Pemetaan AI (FR02 / SD-02)
          </h1>
        </div>
        <button
          type="button"
          onClick={handleDownloadTemplate}
          disabled={isDownloading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-border bg-card hover:bg-muted text-foreground font-semibold text-xs transition shadow-xs disabled:opacity-50"
        >
          {isDownloading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
          ) : (
            <Download className="w-3.5 h-3.5 text-primary" />
          )}
          <span>Unduh Format Impor (.xlsx)</span>
        </button>
      </div>

      {/* Interactive 3-Step Import & AI Mapping Wizard */}
      <div className="border border-border rounded-lg bg-card p-5 space-y-4 shadow-xs">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <span>Alur Unggah Excel, Pemetaan AI, & Konfirmasi Draf</span>
          </h2>
          <span className="text-[11px] font-mono text-muted-foreground">
            Human-in-the-Loop + Fallback Manual
          </span>
        </div>

        <ImportWizard onSuccess={handleWizardSuccess} />
      </div>

      {/* Template Download Info Card */}
      <div className="border border-primary/30 rounded-lg bg-primary/5 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-foreground text-xs">
            <CheckCircle2 className="w-4 h-4 text-primary" />
            <span>Format Standar Buku Kerja Impor (.xlsx)</span>
          </div>
          <p className="text-muted-foreground leading-relaxed">
            Unduh berkas template resmi (<span className="font-mono text-foreground">Format_Impor_Pengadaan_SPJ_PCI.xlsx</span>) yang telah dilengkapi struktur kolom standar lembar <span className="font-mono text-foreground">HPS</span>, contoh pengisian barang, serta lembar <span className="font-mono text-foreground">PETUNJUK_PENGISIAN</span>.
          </p>
        </div>
        <button
          type="button"
          onClick={handleDownloadTemplate}
          disabled={isDownloading}
          className="shrink-0 flex items-center gap-1.5 px-3.5 py-2 rounded bg-primary text-primary-foreground font-semibold text-xs hover:opacity-90 transition shadow-xs disabled:opacity-50"
        >
          {isDownloading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Download className="w-3.5 h-3.5" />
          )}
          <span>Unduh Format (.xlsx)</span>
        </button>
      </div>
    </div>
  );
}
