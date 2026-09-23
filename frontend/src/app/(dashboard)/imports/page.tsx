"use client";

import { useState } from "react";
import { FileSpreadsheet, UploadCloud, Sparkles, ArrowRight } from "lucide-react";
import { ImportModal } from "@/components/imports/import-modal";
import { useRouter } from "next/navigation";

export default function ImportsPage() {
  const [isImportOpen, setIsImportOpen] = useState(false);
  const router = useRouter();

  return (
    <div className="p-6 max-w-4xl space-y-6 text-xs font-sans">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="w-5 h-5 text-primary" />
          <h1 className="text-base font-semibold text-foreground">
            Impor Buku Kerja Spreadsheet Pengadaan & SPJ (FR02)
          </h1>
        </div>
        <button
          type="button"
          onClick={() => setIsImportOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary text-primary-foreground font-semibold text-xs hover:opacity-90 transition shadow-sm"
        >
          <UploadCloud className="w-3.5 h-3.5" />
          <span>Impor Berkas Excel (.xlsx)</span>
        </button>
      </div>

      <div className="border border-border rounded-lg bg-card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <span>Alur Ekstraksi Multi-Lembar Otomatis</span>
        </h2>
        <p className="text-muted-foreground leading-relaxed">
          Sistem mendukung impor langsung dari buku kerja Excel referensi CV Pustaka Cemerlang Indonesia (seperti{" "}
          <span className="font-mono text-foreground font-semibold">4 PCI KK09.xlsx</span>). Parser struktural
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

        <div className="pt-2">
          <button
            type="button"
            onClick={() => setIsImportOpen(true)}
            className="px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded font-medium text-xs flex items-center gap-1.5 transition"
          >
            <span>Buka Dialog Unggah Berkas</span>
            <ArrowRight className="w-3.5 h-3.5" />
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
