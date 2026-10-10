"use client";

import { useState, useEffect } from "react";
import { PackageRevision } from "@/types/package";
import { Artifact, GenerationJob } from "@/types/documents";
import { apiClient } from "@/lib/api-client";
import {
  FileText,
  FileSpreadsheet,
  Archive,
  Eye,
  Download,
  Printer,
  Hash,
  RefreshCw,
  Loader2,
  X,
  AlertCircle,
} from "lucide-react";

interface TabDocumentsProps {
  revision: PackageRevision;
  isReadOnly: boolean;
}

const DOC_REGISTRY = [
  { code: "XLSX", name: "Buku Kerja Konsolidasi SPJ (00_PAKET_PENGADAAN)", format: "XLSX", stage: "Semua Tahap" },
  { code: "D01", name: "Harga Perkiraan Sendiri (HPS)", format: "DOCX / PDF", stage: "HPS" },
  { code: "D02", name: "Surat Permintaan Penawaran (SPP)", format: "DOCX / PDF", stage: "SPP" },
  { code: "D03", name: "Surat Penawaran Harga (Rekanan)", format: "DOCX / PDF", stage: "Penawaran" },
  { code: "D04", name: "Berita Acara Klarifikasi & Negosiasi", format: "DOCX / PDF", stage: "Negosiasi" },
  { code: "D05", name: "Surat Pesanan (SP)", format: "DOCX / PDF", stage: "Pesanan" },
  { code: "D06", name: "Faktur Tagihan Pajak (Invoice)", format: "DOCX / PDF", stage: "Tagihan / Pajak" },
  { code: "D07", name: "Kwitansi Pembayaran Resmi BOS", format: "DOCX / PDF", stage: "Pembayaran" },
  { code: "D08", name: "Surat Jalan Pengantar Barang", format: "DOCX / PDF", stage: "Pengiriman" },
  { code: "D09", name: "Berita Acara Pemeriksaan Barang (BAPB)", format: "DOCX / PDF", stage: "Pemeriksaan" },
  { code: "D10", name: "Berita Acara Serah Terima (BAST Sekolah)", format: "DOCX / PDF", stage: "Serah Terima" },
  { code: "D11", name: "Berita Acara Pembayaran (BAPP)", format: "DOCX / PDF", stage: "Penyelesaian" },
  { code: "D12", name: "Lampiran Berita Acara Pembayaran (Lamp BAPP)", format: "DOCX / PDF", stage: "Penyelesaian" },
  { code: "D13", name: "BAST Rekanan (CV PCI)", format: "DOCX / PDF", stage: "Serah Terima Rekanan" },
  { code: "MERGED_PDF", name: "Bundel Seluruh Dokumen (PDF Gabungan)", format: "PDF", stage: "Gabungan" },
  { code: "ZIP", name: "Paket Arsip Lengkap + Manifest (29 Berkas)", format: "ZIP", stage: "Arsip" },
];

export function TabDocuments({ revision }: TabDocumentsProps) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null);
  const [isManifestOpen, setIsManifestOpen] = useState(false);

  const isDraft = revision.status === "DRAFT" || revision.status === "UNDER_REVIEW";

  const loadArtifacts = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getArtifacts(revision.id);
      setArtifacts(data);
    } catch {
      setArtifacts([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadArtifacts();
  }, [revision.id]);

  const handleTriggerGeneration = async () => {
    setIsGenerating(true);
    try {
      await apiClient.triggerGeneration(revision.id, ["ALL"]);
      alert("Proses pembuatan dokumen (XLSX, Word, PDF, ZIP) telah dimulai di latar belakang.");
      await loadArtifacts();
    } catch (err: any) {
      alert(`Gagal memicu pembuatan dokumen: ${err.message || err}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const getArtifactForCode = (code: string, format: string) => {
    return artifacts.find((a) => a.doc_code === code && a.format.toUpperCase() === format.toUpperCase());
  };

  return (
    <div className="p-6 max-w-5xl space-y-6 text-xs font-sans">
      {/* Top Action Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            Registri 13 Dokumen Pengadaan & SPJ (D01-D13)
          </h3>
          <p className="text-xs text-muted-foreground font-mono mt-0.5">
            Format: XlsxWriter • DocxTemplate • LibreOffice Headless PDF • ZIP Manifest
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadArtifacts}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition"
            title="Segarkan daftar berkas"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            onClick={handleTriggerGeneration}
            disabled={isGenerating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary text-primary-foreground font-semibold text-xs hover:opacity-90 transition shadow-sm"
          >
            {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Printer className="w-3.5 h-3.5" />}
            <span>Hasilkan Seluruh Dokumen (Generate)</span>
          </button>
        </div>
      </div>

      {/* Watermark Notice Banner for Drafts */}
      {isDraft && (
        <div className="border border-amber-500/40 bg-amber-500/10 p-3 rounded-lg flex items-center justify-between text-amber-300 font-mono text-xs shadow-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <span>
              STATUS REVISI MASIH DRAF: Dokumen Word & PDF dicetak dengan tanda air watermark &quot;DRAFT / TIDAK RESMI&quot;.
            </span>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/40 text-amber-300 font-bold">
            WATERMARK AKTIF
          </span>
        </div>
      )}

      {/* 13-Document Registry Table */}
      <div className="border border-border rounded-lg bg-card overflow-hidden">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-muted/90 border-b border-border text-[11px] uppercase font-mono font-bold tracking-wider text-slate-200">
              <th className="px-3 py-2.5 w-16">Kode</th>
              <th className="px-3 py-2.5 min-w-[240px]">Nama Dokumen Resmi</th>
              <th className="px-3 py-2.5 w-28">Tahap Harga</th>
              <th className="px-3 py-2.5 w-28">Status Berkas</th>
              <th className="px-3 py-2.5 w-36 text-center">Unduh Berkas</th>
              <th className="px-3 py-2.5 w-24 text-center">Pratinjau</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border font-mono text-[11px]">
            {DOC_REGISTRY.map((doc) => {
              const docxArt = getArtifactForCode(doc.code, "DOCX");
              const pdfArt = getArtifactForCode(doc.code, "PDF");
              const xlsxArt = getArtifactForCode(doc.code, "XLSX");
              const zipArt = getArtifactForCode(doc.code, "ZIP");

              const hasGenerated = docxArt || pdfArt || xlsxArt || zipArt;

              return (
                <tr key={doc.code} className="hover:bg-muted/30 transition-colors">
                  <td className="px-3 py-2 font-bold text-foreground">{doc.code}</td>
                  <td className="px-3 py-2 font-sans font-medium text-foreground">
                    {doc.name}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground text-[10px]">{doc.stage}</td>
                  <td className="px-3 py-2">
                    {hasGenerated ? (
                      <span className="text-emerald-300 font-bold text-[10px] inline-flex items-center gap-1">
                        ● Tersedia
                      </span>
                    ) : (
                      <span className="text-muted-foreground text-[10px]">○ Belum Dibuat</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <div className="flex items-center justify-center gap-1.5">
                      {docxArt && (
                        <a
                          href={`/api/v1/artifacts/${docxArt.id}/download`}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2 py-0.5 rounded bg-blue-500/15 hover:bg-blue-500/25 text-blue-300 border border-blue-500/30 text-[10px] font-bold transition"
                          title="Unduh DOCX"
                        >
                          DOCX
                        </a>
                      )}
                      {pdfArt && (
                        <a
                          href={`/api/v1/artifacts/${pdfArt.id}/download`}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2 py-0.5 rounded bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/30 text-[10px] font-bold transition"
                          title="Unduh PDF"
                        >
                          PDF
                        </a>
                      )}
                      {xlsxArt && (
                        <a
                          href={`/api/v1/artifacts/${xlsxArt.id}/download`}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2 py-0.5 rounded bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold transition"
                          title="Unduh Excel"
                        >
                          XLSX
                        </a>
                      )}
                      {zipArt && (
                        <a
                          href={`/api/v1/artifacts/${zipArt.id}/download`}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2 py-0.5 rounded bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 border border-purple-500/30 text-[10px] font-bold transition"
                          title="Unduh ZIP Manifest"
                        >
                          ZIP
                        </a>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-center">
                    {pdfArt && (
                      <button
                        type="button"
                        onClick={() => setPreviewPdfUrl(`/api/v1/artifacts/${pdfArt.id}/download`)}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground text-[10px] transition"
                      >
                        <Eye className="w-3 h-3" />
                        <span>Lihat</span>
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* PDF Modal Viewer with Cross-Browser Fallback (Finding #6) */}
      {previewPdfUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4">
          <div className="bg-card border border-border w-full max-w-5xl h-[85vh] rounded-lg shadow-2xl flex flex-col overflow-hidden">
            <div className="px-4 py-2.5 border-b border-border flex items-center justify-between bg-muted/40 font-mono text-xs">
              <span className="font-semibold text-foreground flex items-center gap-2">
                <FileText className="w-4 h-4 text-red-400" /> Pratinjau Berkas PDF
                {isDraft && (
                  <span className="text-[10px] text-amber-300 px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/40 font-bold">
                    DRAFT WATERMARK
                  </span>
                )}
              </span>
              <button
                type="button"
                onClick={() => setPreviewPdfUrl(null)}
                className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Embedded Object with In-Place Fallback Bar */}
            <div className="flex-1 bg-black/40 relative">
              <object data={previewPdfUrl} type="application/pdf" className="w-full h-full">
                <div className="flex flex-col items-center justify-center h-full p-6 text-center border border-dashed border-border bg-muted/20 font-sans">
                  <p className="text-sm text-muted-foreground mb-3 font-mono">
                    Pratinjau PDF tidak didukung langsung oleh peramban ini.
                  </p>
                  <a
                    href={previewPdfUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 bg-primary text-primary-foreground text-xs font-semibold rounded hover:bg-primary/90 transition"
                  >
                    Buka Dokumen di Tab Baru
                  </a>
                </div>
              </object>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
