"use client";

import { useState } from "react";
import { UploadCloud, FileSpreadsheet, AlertTriangle, CheckCircle2, X, Loader2, Sparkles } from "lucide-react";

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ImportModal({ isOpen, onClose, onSuccess }: ImportModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [fiscalYear, setFiscalYear] = useState<number>(2026);
  const [quarter, setQuarter] = useState<number>(2);
  const [fundSource, setFundSource] = useState<string>("BOS_REGULER");

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.name.endsWith(".xlsx") && !f.name.endsWith(".xls")) {
      alert("Hanya berkas format Excel (.xlsx / .xls) yang diperbolehkan.");
      return;
    }
    setFile(f);
  };

  const handleUpload = async () => {
    if (!file) {
      alert("Pilih berkas spreadsheet terlebih dahulu.");
      return;
    }
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("fiscal_year", String(fiscalYear));
      formData.append("quarter", String(quarter));
      formData.append("fund_source", fundSource);

      const res = await fetch("/api/v1/imports/upload", {
        method: "POST",
        headers: {
          "X-User-Role": "ADMINISTRATION",
          "X-Actor-Name": "Staf Administrasi",
        },
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Gagal mengimpor spreadsheet.");
      }

      const uploadData = await res.json();

      // Automatically confirm the parsed import to create Package & Revision
      const confirmRes = await fetch(`/api/v1/imports/${uploadData.import_id}/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Role": "ADMINISTRATION",
          "X-Actor-Name": "Staf Administrasi",
        },
        body: JSON.stringify({
          funding_source_code: fundSource,
          notes: `Diimpor dari berkas ${file.name}`,
        }),
      });

      if (!confirmRes.ok) {
        const errConfirm = await confirmRes.json().catch(() => ({}));
        throw new Error(errConfirm.detail || "Gagal mengonfirmasi dan membuat paket transaksi.");
      }

      const confirmData = await confirmRes.json();
      alert(`Berkas berhasil diimpor dan dibuat sebagai paket baru!\nNomor Paket: ${confirmData.package_number}\nNilai: Rp ${Number(confirmData.grand_total).toLocaleString("id-ID")}`);
      onSuccess();
    } catch (err: any) {
      alert(`Gagal mengimpor: ${err.message || err}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4">
      <div className="bg-card border border-border w-full max-w-lg rounded-lg shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="px-4 py-3 bg-muted/40 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
              Impor Buku Kerja Excel (4 PCI KK09.xlsx)
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

        {/* Content */}
        <div className="p-5 space-y-4 text-xs">
          {/* Metadata selection */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                Tahun Anggaran
              </label>
              <input
                type="number"
                value={fiscalYear}
                onChange={(e) => setFiscalYear(parseInt(e.target.value) || 2026)}
                className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono tabular-nums transition"
              />
            </div>
            <div>
              <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                Triwulan (TW)
              </label>
              <select
                value={quarter}
                onChange={(e) => setQuarter(parseInt(e.target.value) || 1)}
                className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono transition"
              >
                <option value={1}>TW I</option>
                <option value={2}>TW II</option>
                <option value={3}>TW III</option>
                <option value={4}>TW IV</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                Sumber Dana
              </label>
              <select
                value={fundSource}
                onChange={(e) => setFundSource(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono text-[11px] transition"
              >
                <option value="BOS_REGULER">BOS Reguler</option>
                <option value="BOS_KINERJA">BOS Kinerja</option>
                <option value="BOP">BOP</option>
                <option value="LAINNYA">Lainnya</option>
              </select>
            </div>
          </div>

          {/* File Dropzone */}
          <div className="border border-dashed border-border rounded-lg p-6 text-center hover:border-primary/60 transition bg-card/60">
            <input
              type="file"
              id="xlsx-upload"
              accept=".xlsx,.xls"
              onChange={handleFileChange}
              className="hidden"
            />
            <label
              htmlFor="xlsx-upload"
              className="cursor-pointer flex flex-col items-center justify-center gap-2"
            >
              <FileSpreadsheet className="w-8 h-8 text-primary/70" />
              {file ? (
                <div className="space-y-0.5">
                  <span className="font-semibold text-foreground font-mono">{file.name}</span>
                  <span className="block text-[10px] text-muted-foreground">
                    ({(file.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              ) : (
                <div className="space-y-0.5">
                  <span className="text-xs font-semibold text-foreground">
                    Pilih berkas Excel (.xlsx) yang akan diimpor
                  </span>
                  <span className="block text-[10px] text-muted-foreground font-mono">
                    Mendukung template 4 PCI KK09.xlsx
                  </span>
                </div>
              )}
            </label>
          </div>

          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-mono bg-muted/20 p-2.5 rounded border border-border">
            <Sparkles className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
            <span>
              Parser akan mengekstrak otomatis lembar HPS, Surat Penawaran, SP, BAST, dan Kwitansi serta memetakan kolom.
            </span>
          </div>

          {/* Buttons */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs rounded border border-border bg-card hover:bg-muted text-foreground transition"
            >
              Batal
            </button>
            <button
              type="button"
              onClick={handleUpload}
              disabled={isUploading || !file}
              className="flex items-center gap-1 px-4 py-1.5 text-xs font-semibold rounded bg-primary text-primary-foreground hover:opacity-90 transition shadow-xs disabled:opacity-50"
            >
              {isUploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UploadCloud className="w-3.5 h-3.5" />}
              <span>Mulai Ekstraksi & Impor</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
