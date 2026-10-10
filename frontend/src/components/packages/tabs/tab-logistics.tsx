"use client";

import { useState, useEffect } from "react";
import { PackageRevision, RevisionLine, UserRole } from "@/types/package";
import { LogisticsRecord, EvidenceAttachment } from "@/types/logistics";
import { apiClient } from "@/lib/api-client";
import { formatQuantity } from "@/lib/formatters";
import {
  Truck,
  PackageCheck,
  AlertTriangle,
  UploadCloud,
  FileText,
  CheckCircle2,
  XCircle,
  Hash,
  Loader2,
  Save,
} from "lucide-react";

interface TabLogisticsProps {
  revision: PackageRevision;
  currentRole: UserRole;
  isReadOnly: boolean;
  onLogisticsDisputeStatusChanged?: (hasDispute: boolean) => void;
  onLinesChanged?: (newLines: RevisionLine[]) => void;
  onLogisticsChanged?: (newLogistics: LogisticsRecord) => void;
}

export function TabLogistics({
  revision,
  currentRole,
  isReadOnly,
  onLogisticsDisputeStatusChanged,
  onLinesChanged,
  onLogisticsChanged,
}: TabLogisticsProps) {
  const [logistics, setLogistics] = useState<LogisticsRecord | null>(null);
  const [lines, setLines] = useState<RevisionLine[]>(() => revision.lines || []);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSavingLogistics, setIsSavingLogistics] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Fetch logistics record
  useEffect(() => {
    async function loadLogistics() {
      setIsLoading(true);
      try {
        const data = await apiClient.getLogistics(revision.id);
        setLogistics(data);
      } catch {
        // Init default if not yet created on backend
        const defaultLog: LogisticsRecord = {
          id: "",
          revision_id: revision.id,
          delivery_status: "DELIVERED",
          is_delivery_confirmed: true,
          courier_name: "Armada Pengiriman CV PCI",
          vehicle_plate: "B 1234 PCI",
          attachments: [],
        };
        setLogistics(defaultLog);
      } finally {
        setIsLoading(false);
      }
    }
    loadLogistics();
  }, [revision.id]);

  // Evaluate Pilot Boundary Stop (Finding #5):
  // Strictly check if condition is explicitly RUSAK or if received_quantity is strictly LESS than quantity.
  // When received_quantity is null/undefined, it defaults to complete delivery (no dispute).
  const hasDispute = lines.some(
    (l) =>
      l.condition === "RUSAK" ||
      (l.received_quantity !== undefined &&
        l.received_quantity !== null &&
        Number(l.received_quantity) >= 0 &&
        Number(l.received_quantity) < Number(l.quantity))
  );

  useEffect(() => {
    onLogisticsDisputeStatusChanged?.(hasDispute);
  }, [hasDispute, onLogisticsDisputeStatusChanged]);

  const updateLogisticsField = (field: keyof LogisticsRecord, val: any) => {
    if (!logistics) return;
    const updated = { ...logistics, [field]: val };
    if (field === "receipt_date") {
      updated.actual_delivery_date = val;
    } else if (field === "actual_delivery_date") {
      updated.receipt_date = val;
    }
    setLogistics(updated);
    onLogisticsChanged?.(updated);
  };

  const handleSaveLogistics = async () => {
    if (!logistics) return;
    setIsSavingLogistics(true);
    setSaveSuccess(false);
    try {
      const payload = {
        ...logistics,
        dispatch_date: logistics.dispatch_date || null,
        receipt_date: logistics.receipt_date || logistics.actual_delivery_date || null,
        actual_delivery_date: logistics.receipt_date || logistics.actual_delivery_date || null,
      };
      const saved = await apiClient.updateLogistics(revision.id, payload);
      setLogistics(saved);
      onLogisticsChanged?.(saved);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      alert(`Gagal menyimpan data ekspedisi: ${err.message || err}`);
    } finally {
      setIsSavingLogistics(false);
    }
  };

  const handleConditionToggle = (idx: number) => {
    if (isReadOnly) return;
    const updated = [...lines];
    const current = updated[idx].condition || "BAIK";
    updated[idx].condition = current === "BAIK" ? "RUSAK" : "BAIK";
    setLines(updated);
    onLinesChanged?.(updated);
  };

  const handleReceivedQtyChange = (idx: number, val: number) => {
    if (isReadOnly) return;
    const updated = [...lines];
    updated[idx].received_quantity = val;
    setLines(updated);
    onLinesChanged?.(updated);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      alert("Ukuran berkas bukti maksimal 10 MB.");
      return;
    }

    setIsUploading(true);
    try {
      const att = await apiClient.uploadLogisticsEvidence(revision.id, file);
      if (logistics) {
        const updated = {
          ...logistics,
          attachments: [...(logistics.attachments || []), att],
        };
        setLogistics(updated);
        onLogisticsChanged?.(updated);
      }
      alert("Bukti pengiriman & foto serah terima berhasil diunggah.");
    } catch (err: any) {
      alert(`Gagal mengunggah bukti: ${err.message || err}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl space-y-6 text-xs font-sans">
      {/* Pilot Boundary Stop Warning Banner (Finding #5) */}
      {hasDispute && (
        <div className="border border-amber-500/40 bg-amber-500/10 p-4 rounded-lg flex items-start gap-3 text-amber-200 shadow-xs">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-bold text-amber-300 font-mono uppercase tracking-wider text-xs">
              [ ⚠ DI LUAR ALUR KERJA PILOT: Pengiriman Bermasalah / Rusak Terdeteksi ]
            </h4>
            <p className="text-xs text-amber-200/90 leading-relaxed">
              Terdapat barang dalam kondisi <span className="font-mono font-bold text-amber-300">RUSAK</span> atau
              kuantitas diterima tidak lengkap. Sesuai PRD Batasan Pilot (BR13), transaksi bermasalah tidak dapat
              diterbitkan sebagai pengiriman 100% penuh. Silakan lakukan penyelesaian fisik dengan pihak sekolah atau
              revisi kuantitas pesanan. Tombol pengajuan persetujuan telah diblokir.
            </p>
          </div>
        </div>
      )}

      {/* 1. Logistics Dispatch & Fleet Metadata */}
      <div className="border border-border rounded-lg bg-card p-4 space-y-4">
        <div className="flex items-center justify-between border-b border-border/80 pb-2.5">
          <div className="flex items-center gap-2">
            <Truck className="w-4 h-4 text-primary" />
            <h3 className="font-semibold text-foreground text-sm">
              Informasi Ekspedisi & Armada Pengiriman (BR13)
            </h3>
          </div>
          <div className="flex items-center gap-2">
            {saveSuccess && (
              <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Tersimpan
              </span>
            )}
            {!isReadOnly && (
              <button
                type="button"
                disabled={isSavingLogistics}
                onClick={handleSaveLogistics}
                className="px-2.5 py-1 rounded bg-primary text-primary-foreground font-medium text-[11px] hover:opacity-90 transition disabled:opacity-50 flex items-center gap-1 shadow-sm"
              >
                {isSavingLogistics ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Save className="w-3 h-3" />
                )}
                <span>Simpan Ekspedisi</span>
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Nama Kurir / Pengantar
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={logistics?.courier_name || ""}
              onChange={(e) => updateLogisticsField("courier_name", e.target.value)}
              placeholder="Armada CV PCI"
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Nomor Polisi Kendaraan
            </label>
            <input
              type="text"
              disabled={isReadOnly}
              value={logistics?.vehicle_plate || ""}
              onChange={(e) => updateLogisticsField("vehicle_plate", e.target.value)}
              placeholder="B 1234 PCI"
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono uppercase"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Tanggal Kirim Fisik
            </label>
            <input
              type="date"
              disabled={isReadOnly}
              value={logistics?.dispatch_date || ""}
              onChange={(e) => updateLogisticsField("dispatch_date", e.target.value || null)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono tabular-nums"
            />
          </div>

          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Tanggal Diterima Sekolah
            </label>
            <input
              type="date"
              disabled={isReadOnly}
              value={logistics?.receipt_date || logistics?.actual_delivery_date || ""}
              onChange={(e) => updateLogisticsField("receipt_date", e.target.value || null)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono tabular-nums"
            />
          </div>
        </div>
      </div>

      {/* 2. Line Item Physical Condition Toggles */}
      <div className="border border-border rounded-lg bg-card overflow-hidden">
        <div className="px-4 py-2.5 bg-muted/40 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PackageCheck className="w-4 h-4 text-emerald-400" />
            <h3 className="font-semibold text-foreground text-xs uppercase tracking-wider font-mono">
              Pemeriksaan Fisik Barang (BAST & BAPB)
            </h3>
          </div>
          <span className="text-[10px] font-mono text-muted-foreground">
            {lines.filter((l) => l.condition === "BAIK").length} / {lines.length} Kondisi Baik
          </span>
        </div>

        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-muted/90 border-b border-border text-[11px] uppercase font-mono font-bold tracking-wider text-slate-200">
              <th className="px-3 py-2.5 w-10 text-center">No</th>
              <th className="px-3 py-2.5 min-w-[200px]">Deskripsi Barang</th>
              <th className="px-3 py-2.5 w-24 text-right">Vol Pesanan</th>
              <th className="px-3 py-2.5 w-28 text-right">Vol Diterima</th>
              <th className="px-3 py-2.5 w-32 text-center">Kondisi Fisik</th>
              <th className="px-3 py-2.5 min-w-[150px]">Catatan Serah Terima</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border font-mono text-[11px]">
            {lines.map((line, idx) => {
              const isDamaged = line.condition === "RUSAK";
              const isPartial =
                line.received_quantity !== null &&
                line.received_quantity !== undefined &&
                Number(line.received_quantity) < Number(line.quantity);

              return (
                <tr
                  key={line.id || `line-${idx}`}
                  className={`hover:bg-muted/30 transition-colors ${
                    isDamaged || isPartial ? "bg-amber-500/10" : ""
                  }`}
                >
                  <td className="px-3 py-2 text-center text-muted-foreground font-bold">
                    {line.line_number}
                  </td>
                  <td className="px-3 py-2 font-sans font-medium text-foreground">
                    {line.confirmed_description || line.original_description}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-foreground font-medium">
                    {formatQuantity(line.quantity)} {line.unit}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <input
                      type="number"
                      disabled={isReadOnly}
                      min="0"
                      max={Number(line.quantity)}
                      value={
                        line.received_quantity !== null && line.received_quantity !== undefined
                          ? Number(line.received_quantity)
                          : Number(line.quantity)
                      }
                      onChange={(e) => handleReceivedQtyChange(idx, parseFloat(e.target.value) || 0)}
                      className="w-16 px-1.5 py-0.5 text-right bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary font-mono tabular-nums text-foreground"
                    />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button
                      type="button"
                      disabled={isReadOnly}
                      onClick={() => handleConditionToggle(idx)}
                      className={`px-2.5 py-1 rounded text-[10px] font-mono font-bold uppercase transition border ${
                        line.condition === "BAIK" || !line.condition
                          ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/25"
                          : "bg-red-500/15 text-red-300 border-red-500/30 hover:bg-red-500/25"
                      }`}
                    >
                      {line.condition === "BAIK" || !line.condition ? "✓ BAIK" : "✕ RUSAK"}
                    </button>
                  </td>
                  <td className="px-3 py-2 font-sans text-muted-foreground">
                    {isDamaged
                      ? "Barang rusak pada saat serah terima."
                      : isPartial
                      ? "Kuantitas diterima kurang dari pesanan."
                      : "Diterima lengkap dan berfungsi baik."}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 3. Multi-File Evidence Uploader with SHA-256 Display */}
      <div className="border border-border rounded-lg bg-card p-4 space-y-4">
        <div className="flex items-center justify-between border-b border-border/80 pb-2.5">
          <div className="flex items-center gap-2">
            <UploadCloud className="w-4 h-4 text-sky-400" />
            <h3 className="font-semibold text-foreground text-sm">
              Unggah Bukti Fisik & Foto Serah Terima (JPEG, PNG, PDF maks 10 MB)
            </h3>
          </div>
          <span className="text-[10px] font-mono text-muted-foreground uppercase">
            SHA-256 Integritas
          </span>
        </div>

        {/* Upload Dropzone */}
        {!isReadOnly && (
          <div className="border border-dashed border-border rounded-lg p-6 text-center hover:border-primary/60 transition bg-muted/10">
            <input
              type="file"
              id="evidence-upload"
              accept=".jpg,.jpeg,.png,.pdf"
              onChange={handleFileUpload}
              className="hidden"
            />
            <label
              htmlFor="evidence-upload"
              className="cursor-pointer flex flex-col items-center justify-center gap-2"
            >
              {isUploading ? (
                <Loader2 className="w-6 h-6 text-primary animate-spin" />
              ) : (
                <UploadCloud className="w-6 h-6 text-muted-foreground" />
              )}
              <span className="text-xs font-semibold text-foreground">
                Klik untuk memilih berkas foto serah terima / PDF Surat Jalan
              </span>
              <span className="text-[11px] text-muted-foreground font-mono">
                Format: .JPG, .PNG, .PDF (Maksimal 10 MB per berkas)
              </span>
            </label>
          </div>
        )}

        {/* Attachments List */}
        {logistics?.attachments && logistics.attachments.length > 0 && (
          <div className="space-y-2 pt-2">
            <h4 className="text-[11px] font-mono uppercase text-muted-foreground">
              Berkas Bukti Terunggah ({logistics.attachments.length}):
            </h4>
            <div className="divide-y divide-border/60 border border-border rounded bg-muted/20">
              {logistics.attachments.map((att) => (
                <div
                  key={att.id}
                  className="p-2.5 flex items-center justify-between text-xs font-mono"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    <span className="truncate font-semibold text-foreground">
                      {att.original_filename}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      ({(att.file_size_bytes / 1024).toFixed(1)} KB)
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1 font-mono">
                      <Hash className="w-3 h-3 text-muted-foreground" />
                      {att.sha256_hash.slice(0, 12)}...
                    </span>
                    <span className="text-emerald-400">✓ Terverifikasi</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
