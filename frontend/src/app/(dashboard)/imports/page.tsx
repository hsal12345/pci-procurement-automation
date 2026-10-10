"use client";

import { useState } from "react";
import { FileSpreadsheet, UploadCloud, Sparkles, ArrowRight, Download, Loader2, CheckCircle2 } from "lucide-react";
import { ImportModal } from "@/components/imports/import-modal";
import { apiClient } from "@/lib/api-client";
import { useRouter } from "next/navigation";

export default function ImportsPage() {
  const [isImportOpen, setIsImportOpen] = useState(false);
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

  return (
    <div className="p-6 max-w-4xl space-y-6 text-xs font-sans">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="w-5 h-5 text-primary" />
          <h1 className="text-base font-semibold text-foreground">
            Impor Buku Kerja Spreadsheet Pengadaan & SPJ (FR02)
          </h1>
        </div>
        <div className="flex items-center gap-2">
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
          <button
            type="button"
            onClick={() => setIsImportOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary text-primary-foreground font-semibold text-xs hover:opacity-90 transition shadow-sm"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Impor Berkas Excel (.xlsx)</span>
          </button>
        </div>
      </div>

      {/* Template Download Card */}
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

      <div className="border border-border rounded-lg bg-card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <span>Alur Ekstraksi Multi-Lembar Otomatis</span>
        </h2>
        <p className="text-muted-foreground leading-relaxed">
          Sistem mendukung impor langsung dari buku kerja Excel referensi CV Pustaka Cemerlang Indonesia (seperti{" "}
          <span className="font-mono text-foreground font-semibold">4 PCI KK09.xlsx</span> atau template standar). Parser struktural
          akan mengekstrak dan memverifikasi data secara otomatis:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 font-mono text-[11px]">
          <div className="border border-border rounded p-3 bg-muted/20 space-y-1">
            <span className="font-bold text-foreground">1. Lembar HPS & SPP (D01, D02)</span>
            <p className="text-muted-foreground font-sans text-xs">
              Mengekstrak spesifikasi awal, kuantitas volume, satuan barang, dan harga pagu anggaran sekolah.
            </p>
          </div>

          <div className="border border-border rounded p-3 bg-muted/20 space-y-1">
            <span className="font-bold text-foreground">2. Surat Penawaran & Negosiasi (D03, D07)</span>
            <p className="text-muted-foreground font-sans text-xs">
              Mengekstrak perbandingan harga penawaran rekanan dan harga kesepakatan final setelah negosiasi.
            </p>
          </div>

          <div className="border border-border rounded p-3 bg-muted/20 space-y-1">
            <span className="font-bold text-foreground">3. Surat Pesanan & BAST (D04, D09)</span>
            <p className="text-muted-foreground font-sans text-xs">
              Mengekstrak tanggal pesanan, berita acara serah terima barang, dan daftar penerimaan barang fisik.
            </p>
          </div>

          <div className="border border-border rounded p-3 bg-muted/20 space-y-1">
            <span className="font-bold text-foreground">4. BAPP, Kwitansi & Faktur (D11, D12, D13)</span>
            <p className="text-muted-foreground font-sans text-xs">
              Mengekstrak tanggal pembayaran, nomor faktur tagihan, serta perhitungan potongan PPh dan PPN 11%.
            </p>
          </div>
        </div>

        <div className="pt-2 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setIsImportOpen(true)}
            className="px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded font-medium text-xs flex items-center gap-1.5 transition"
          >
            <span>Buka Dialog Unggah Berkas</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={handleDownloadTemplate}
            disabled={isDownloading}
            className="px-4 py-2 border border-border hover:bg-muted/50 text-muted-foreground hover:text-foreground rounded font-medium text-xs flex items-center gap-1.5 transition disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Unduh Template Kosong / Contoh (.xlsx)</span>
          </button>
        </div>
      </div>

      <ImportModal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onSuccess={() => {
          setIsImportOpen(false);
          router.push("/packages");
        }}
      />
    </div>
  );
}
