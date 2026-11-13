"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Loader2,
  Plus,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import { apiClient, ApiError } from "@/lib/api-client";
import { CandidateMappingProposal } from "@/types/ai";
import {
  CandidateLineItem,
  ImportConfirmResponse,
  ImportPreviewResponse,
} from "@/types/imports";

interface SchoolOption {
  id: string;
  name: string;
  npsn?: string | null;
  level?: string | null;
}

interface ImportWizardProps {
  onCancel?: () => void;
  onSuccess: (result: ImportConfirmResponse) => void;
  onStepChange?: (step: 1 | 2 | 3) => void;
}

const CANONICAL_FIELDS: Array<{
  key: string;
  label: string;
  required?: boolean;
  hint: string;
}> = [
  { key: "line_no", label: "No. Urut", hint: "No / Nomor" },
  { key: "description", label: "Nama / Uraian Barang", required: true, hint: "Nama Barang / Uraian" },
  { key: "specification", label: "Spesifikasi", hint: "Spesifikasi / Ukuran" },
  { key: "quantity", label: "Volume / Kuantitas", required: true, hint: "Volume / Qty" },
  { key: "unit", label: "Satuan", required: true, hint: "Satuan (liter, buah)" },
  { key: "hps_price", label: "Harga Satuan (HPS)", required: true, hint: "Harga Satuan / HPS" },
  { key: "offer_price", label: "Harga Penawaran", hint: "Opsional (default = HPS)" },
  { key: "final_price", label: "Harga Final / Negosiasi", hint: "Opsional (default = Penawaran)" },
];

function colIndexToLetter(colIdx: number): string {
  let n = colIdx;
  let result = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    result = String.fromCharCode(65 + rem) + result;
    n = Math.floor((n - 1) / 26);
  }
  return result || "-";
}

export function ImportWizard({ onCancel, onSuccess, onStepChange }: ImportWizardProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Step 1 state: Upload & Context
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragDepthRef = useRef(0);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [schools, setSchools] = useState<SchoolOption[]>([]);
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>("");
  const [fiscalYear, setFiscalYear] = useState<number>(2026);
  const [quarter, setQuarter] = useState<number>(2);
  const [fundSource, setFundSource] = useState<string>("BOS_REGULER");
  const [isDownloading, setIsDownloading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Step 2 state: AI Mapping Proposal & Manual Override
  const [importId, setImportId] = useState<string | null>(null);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [activeSheet, setActiveSheet] = useState<string>("HPS");
  const [headerRowIndex, setHeaderRowIndex] = useState<number>(1);
  const [columnMapping, setColumnMapping] = useState<Record<string, number>>({});
  const [aiProposal, setAiProposal] = useState<CandidateMappingProposal | null>(null);
  const [aiMode, setAiMode] = useState<"LOADING" | "AI" | "AMBIGUOUS" | "MANUAL_FALLBACK">("LOADING");
  const [aiMessage, setAiMessage] = useState<string | null>(null);
  const [hasEditedMapping, setHasEditedMapping] = useState(false);
  const [isReparsing, setIsReparsing] = useState(false);

  // Step 3 state: Candidate Lines Review & Confirm
  const [editableLines, setEditableLines] = useState<CandidateLineItem[]>([]);
  const [notes, setNotes] = useState<string>("");
  const [isConfirming, setIsConfirming] = useState(false);
  const [validationErrors, setValidationErrors] = useState<
    Array<{ row_index: number; field: string; message: string }>
  >([]);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  useEffect(() => {
    onStepChange?.(step);
  }, [step, onStepChange]);

  useEffect(() => {
    let mounted = true;
    apiClient
      .getSchools()
      .then((list) => {
        if (mounted && Array.isArray(list)) {
          setSchools(list);
        }
      })
      .catch(() => {
        // Non-blocking: auto-detect fallback remains available
      });
    return () => {
      mounted = false;
    };
  }, []);

  const mappingSource: "AI" | "AI_EDITED" | "MANUAL_FALLBACK" = useMemo(() => {
    if (aiMode === "MANUAL_FALLBACK") return "MANUAL_FALLBACK";
    return hasEditedMapping ? "AI_EDITED" : "AI";
  }, [aiMode, hasEditedMapping]);

  const maxGridCols = useMemo(() => {
    if (!preview?.raw_preview_rows?.length) return 10;
    return Math.max(8, ...preview.raw_preview_rows.map((r) => r.length));
  }, [preview]);

  const estimatedTotals = useMemo(() => {
    const subtotal = editableLines.reduce((acc, line) => {
      const qty = Number(line.quantity) || 0;
      const price = Number(line.final_unit_price) || 0;
      const disc = Number(line.discount) || 0;
      return acc + Math.max(0, qty * price - disc);
    }, 0);
    const taxTotal = Math.round(subtotal * 0.11);
    return {
      subtotal,
      taxTotal,
      grandTotal: subtotal + taxTotal,
    };
  }, [editableLines]);

  const handleDownloadTemplate = async () => {
    setIsDownloading(true);
    try {
      await apiClient.downloadImportTemplate();
    } catch (err: any) {
      setUploadError(err?.message || "Gagal mengunduh format template.");
    } finally {
      setIsDownloading(false);
    }
  };

  const selectExcelFile = (selected: File | null | undefined) => {
    setUploadError(null);
    if (!selected) return;

    const lowerName = selected.name.toLowerCase();
    if (lowerName.endsWith(".xls") && !lowerName.endsWith(".xlsx")) {
      setUploadError(
        "Format lama .xls tidak didukung langsung. Silakan simpan ulang berkas sebagai .xlsx terlebih dahulu."
      );
      setFile(null);
      return;
    }
    if (!lowerName.endsWith(".xlsx")) {
      setUploadError(
        "Hanya berkas format Excel (.xlsx) yang didukung untuk impor berkas pengadaan."
      );
      setFile(null);
      return;
    }
    if (selected.size <= 0) {
      setUploadError("Berkas Excel kosong (0 byte) dan tidak dapat diproses.");
      setFile(null);
      return;
    }
    if (selected.size > 20 * 1024 * 1024) {
      setUploadError("Ukuran berkas Excel melebihi batas maksimal 20 MB.");
      setFile(null);
      return;
    }

    setFile(selected);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    selectExcelFile(f);
    e.target.value = "";
  };

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepthRef.current += 1;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
    if (!isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) {
      setIsDragging(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepthRef.current = 0;
    setIsDragging(false);

    const droppedFiles = e.dataTransfer.files;
    if (!droppedFiles || droppedFiles.length === 0) return;
    if (droppedFiles.length > 1) {
      setUploadError("Unggah satu berkas Excel (.xlsx) dalam satu waktu.");
      return;
    }
    selectExcelFile(droppedFiles[0]);
  };

  const handleClearFile = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setFile(null);
    setUploadError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const runAIMappingAndLoadPreview = async (
    targetImportId: string,
    sheetOverride?: string
  ) => {
    setAiMode("LOADING");
    setAiMessage(null);
    setHasEditedMapping(false);

    // Run preview fetch & AI suggestion concurrently / gracefully handle AI failure (UC-02 3a)
    let loadedPreview: ImportPreviewResponse | null = null;
    try {
      loadedPreview = await apiClient.getImportPreview(targetImportId);
      setPreview(loadedPreview);
      const sheetToUse = sheetOverride || loadedPreview.active_sheet || "HPS";
      setActiveSheet(sheetToUse);
      setEditableLines(loadedPreview.candidate_lines || []);
    } catch (err: any) {
      setUploadError(err?.message || "Gagal memuat pratinjau berkas impor.");
      return;
    }

    const targetSheet = sheetOverride || loadedPreview.active_sheet || loadedPreview.sheet_names?.[0];

    try {
      const proposal = await apiClient.suggestAIMapping(targetImportId, targetSheet);
      setAiProposal(proposal);
      setColumnMapping(proposal.column_mapping || loadedPreview.detected_mapping || {});
      setHeaderRowIndex(proposal.header_row_index || loadedPreview.header_row_index || 1);
      if (proposal.sheet_name) setActiveSheet(proposal.sheet_name);

      if (proposal.is_ambiguous || proposal.confidence_score < 0.8) {
        setAiMode("AMBIGUOUS");
        setAiMessage(
          `Skor keyakinan AI ${(proposal.confidence_score * 100).toFixed(0)}% (< 80%). Wajib tinjau dan sesuaikan pemetaan kolom secara manual.`
        );
      } else {
        setAiMode("AI");
        setAiMessage(
          `AI memetakan ${Object.keys(proposal.column_mapping || {}).length} kolom dengan keyakinan ${(proposal.confidence_score * 100).toFixed(0)}%.`
        );
      }
    } catch (err: any) {
      // UC-02 3a: Fallback gracefully to manual + heuristic mapping
      setAiProposal(null);
      setAiMode("MANUAL_FALLBACK");
      setColumnMapping(loadedPreview.detected_mapping || {});
      setHeaderRowIndex(loadedPreview.header_row_index || 1);
      const detail =
        err instanceof ApiError
          ? err.message
          : err?.message || "Layanan AI sedang tidak tersedia atau batas anggaran tercapai.";
      setAiMessage(`${detail} Dialihkan ke Mode Pemetaan Manual dengan deteksi heuristik awal.`);
    }
  };

  // Step 1 -> Step 2 (SD-02 Message 1 & 2)
  const handleUploadAndAnalyze = async () => {
    if (!file) {
      setUploadError("Pilih berkas Excel (.xlsx) terlebih dahulu.");
      return;
    }
    setUploadError(null);
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (selectedSchoolId) formData.append("school_id", selectedSchoolId);
      formData.append("fiscal_year", String(fiscalYear));
      formData.append("quarter", String(quarter));
      formData.append("fund_source", fundSource);

      const uploadData = await apiClient.uploadImportExcel(formData);
      setImportId(uploadData.import_id);
      setStep(2);
      await runAIMappingAndLoadPreview(uploadData.import_id, uploadData.active_sheet || undefined);
    } catch (err: any) {
      setUploadError(err?.message || "Berkas Excel gagal diunggah atau strukturnya tidak valid.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleSheetChange = async (newSheet: string) => {
    setActiveSheet(newSheet);
    if (!importId) return;
    setIsReparsing(true);
    try {
      const updated = await apiClient.reparseImport(importId, {
        sheet_name: newSheet,
        column_mapping: {},
        mapping_source: aiMode === "MANUAL_FALLBACK" ? "MANUAL_FALLBACK" : "AI_EDITED",
      });
      setPreview(updated);
      setEditableLines(updated.candidate_lines || []);
      await runAIMappingAndLoadPreview(importId, newSheet);
    } catch (err: any) {
      setAiMessage(err?.message || "Gagal memuat lembar kerja yang dipilih.");
    } finally {
      setIsReparsing(false);
    }
  };

  const handleMappingFieldChange = (fieldKey: string, colVal: string) => {
    setHasEditedMapping(true);
    setColumnMapping((prev) => {
      const next = { ...prev };
      const parsed = parseInt(colVal, 10);
      if (!parsed || parsed < 1) {
        delete next[fieldKey];
      } else {
        next[fieldKey] = parsed;
      }
      return next;
    });
  };

  // Step 2 -> Step 3 (Apply mapping & preview extracted lines)
  const handleApplyMappingAndContinue = async () => {
    if (!importId) return;
    setIsReparsing(true);
    setConfirmError(null);
    setValidationErrors([]);

    try {
      const updated = await apiClient.reparseImport(importId, {
        sheet_name: activeSheet,
        header_row_index: headerRowIndex,
        column_mapping: columnMapping,
        mapping_source: mappingSource,
      });
      setPreview(updated);
      setEditableLines(updated.candidate_lines || []);
      setStep(3);
    } catch (err: any) {
      setAiMessage(err?.message || "Gagal mengekstrak baris menggunakan pemetaan yang dipilih.");
    } finally {
      setIsReparsing(false);
    }
  };

  const updateLineField = (idx: number, field: keyof CandidateLineItem, value: any) => {
    setEditableLines((prev) =>
      prev.map((line, i) => {
        if (i !== idx) return line;
        const next = { ...line, [field]: value };
        const qty = Number(next.quantity) || 0;
        const finalPrice = Number(next.final_unit_price) || 0;
        const disc = Number(next.discount) || 0;
        next.line_total = Math.max(0, qty * finalPrice - disc);
        return next;
      })
    );
  };

  const addEmptyLine = () => {
    setEditableLines((prev) => [
      ...prev,
      {
        line_number: prev.length + 1,
        original_description: "",
        confirmed_description: "",
        specification: "",
        quantity: 1,
        unit: "buah",
        hps_unit_price: 0,
        offer_unit_price: 0,
        final_unit_price: 0,
        discount: 0,
        line_total: 0,
        condition: "BAIK",
      },
    ]);
  };

  const removeLine = (idx: number) => {
    setEditableLines((prev) =>
      prev
        .filter((_, i) => i !== idx)
        .map((item, newIdx) => ({ ...item, line_number: newIdx + 1 }))
    );
  };

  // Step 3 -> Confirm & Save Draft (SD-02 Messages 5-8)
  const handleConfirmImport = async () => {
    if (!importId) return;
    setIsConfirming(true);
    setConfirmError(null);
    setValidationErrors([]);

    try {
      const result = await apiClient.confirmImport(importId, {
        school_id: selectedSchoolId || null,
        fiscal_year: fiscalYear,
        quarter,
        sheet_name: activeSheet,
        header_row_index: headerRowIndex,
        column_mapping: columnMapping,
        mapping_source: mappingSource,
        confirmed_lines: editableLines,
        funding_source_code: fundSource,
        notes: notes.trim() || `Diimpor dari berkas ${file?.name || preview?.filename || "Excel"}`,
      });
      onSuccess(result);
    } catch (err: any) {
      if (err instanceof ApiError && err.data?.detail && typeof err.data.detail === "object") {
        setConfirmError(err.data.detail.message || "Validasi baris impor gagal.");
        if (Array.isArray(err.data.detail.errors)) {
          setValidationErrors(err.data.detail.errors);
        }
      } else {
        setConfirmError(err?.message || "Gagal mengonfirmasi impor dan membentuk draf transaksi.");
      }
    } finally {
      setIsConfirming(false);
    }
  };

  return (
    <div className="space-y-4 text-xs font-sans">
      {/* Stepper Indicator */}
      <div className="grid grid-cols-3 gap-2 p-2 rounded-lg bg-muted/30 border border-border">
        {[
          { num: 1, label: "1. Unggah Excel & Sekolah" },
          { num: 2, label: "2. Tinjau Pemetaan AI" },
          { num: 3, label: "3. Validasi & Simpan Draf" },
        ].map((s) => {
          const active = step === s.num;
          const done = step > s.num;
          return (
            <div
              key={s.num}
              className={`px-3 py-1.5 rounded text-[11px] font-mono flex items-center gap-1.5 transition ${
                active
                  ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                  : done
                  ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                  : "text-muted-foreground"
              }`}
            >
              {done ? <CheckCircle2 className="w-3.5 h-3.5 shrink-0" /> : null}
              <span className="truncate">{s.label}</span>
            </div>
          );
        })}
      </div>

      {/* ================================================================= */}
      {/* STEP 1: Upload File & Select School / Fiscal Metadata             */}
      {/* ================================================================= */}
      {step === 1 && (
        <div className="space-y-4">
          {uploadError && (
            <div className="p-3 rounded-lg bg-destructive/15 border border-destructive/40 text-destructive flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="font-semibold">Berkas Ditolak pada Pemeriksaan Struktur</p>
                <p className="text-[11px] opacity-90">{uploadError}</p>
              </div>
            </div>
          )}

          {/* School Selector */}
          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Sekolah Penerima (Master Sekolah)
            </label>
            <select
              value={selectedSchoolId}
              onChange={(e) => setSelectedSchoolId(e.target.value)}
              className="w-full px-2.5 py-2 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition"
            >
              <option value="">Deteksi Otomatis dari Kop Excel (atau buat baru jika belum ada)</option>
              {schools.map((sc) => (
                <option key={sc.id} value={sc.id}>
                  {sc.name} {sc.npsn ? `(NPSN: ${sc.npsn})` : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Fiscal & Funding Metadata */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                Tahun Anggaran
              </label>
              <input
                type="number"
                value={fiscalYear}
                onChange={(e) => setFiscalYear(parseInt(e.target.value, 10) || 2026)}
                className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono tabular-nums transition"
              />
            </div>
            <div>
              <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                Triwulan (TW)
              </label>
              <select
                value={quarter}
                onChange={(e) => setQuarter(parseInt(e.target.value, 10) || 1)}
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

          {/* File Dropzone (Drag & Drop + Click) */}
          <div
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`relative border-2 border-dashed rounded-lg p-6 text-center transition-all ${
              isDragging
                ? "border-primary bg-primary/10 ring-2 ring-primary/30 scale-[1.01]"
                : file
                ? "border-emerald-500/50 bg-emerald-500/5 hover:border-primary/60"
                : "border-border bg-card/60 hover:border-primary/60"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              id="xlsx-upload-wizard"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={handleFileChange}
              className="hidden"
            />
            {file && (
              <button
                type="button"
                onClick={handleClearFile}
                title="Hapus berkas terpilih"
                className="absolute top-2.5 right-2.5 p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
            <label
              htmlFor="xlsx-upload-wizard"
              className="cursor-pointer flex flex-col items-center justify-center gap-2"
            >
              {isDragging ? (
                <>
                  <UploadCloud className="w-9 h-9 text-primary animate-bounce" />
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-primary">
                      Lepaskan berkas Excel (.xlsx) di sini
                    </span>
                    <span className="block text-[10px] text-primary/80 font-mono">
                      Berkas akan langsung divalidasi sebelum dikirim ke AI
                    </span>
                  </div>
                </>
              ) : file ? (
                <>
                  <FileSpreadsheet className="w-8 h-8 text-emerald-400" />
                  <div className="space-y-0.5">
                    <span className="font-semibold text-foreground font-mono">{file.name}</span>
                    <span className="block text-[10px] text-muted-foreground">
                      ({(file.size / 1024).toFixed(1)} KB) — Seret berkas lain atau klik untuk mengganti
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <UploadCloud className="w-8 h-8 text-primary/70" />
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-foreground">
                      Seret &amp; lepaskan berkas Excel (.xlsx) ke sini, atau klik untuk memilih
                    </span>
                    <span className="block text-[10px] text-muted-foreground font-mono">
                      Mendukung format standar maupun non-standar (HPS / 4 PCI KK09.xlsx, maks. 20 MB)
                    </span>
                  </div>
                </>
              )}
            </label>
          </div>

          {/* Template Download Strip */}
          <div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground font-mono bg-muted/20 p-2.5 rounded border border-border">
            <div className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
              <span>Belum punya formatnya? Unduh template Excel standar.</span>
            </div>
            <button
              type="button"
              onClick={handleDownloadTemplate}
              disabled={isDownloading}
              className="shrink-0 flex items-center gap-1 px-2.5 py-1 rounded bg-primary/10 hover:bg-primary/20 text-primary font-sans font-semibold text-[11px] transition disabled:opacity-50"
            >
              {isDownloading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
              <span>Unduh Format</span>
            </button>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="px-3 py-1.5 text-xs rounded border border-border bg-card hover:bg-muted text-foreground transition"
              >
                Batal
              </button>
            )}
            <button
              type="button"
              onClick={handleUploadAndAnalyze}
              disabled={isUploading || !file}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded bg-primary text-primary-foreground hover:opacity-90 transition shadow-xs disabled:opacity-50"
            >
              {isUploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UploadCloud className="w-3.5 h-3.5" />}
              <span>Unggah & Minta Pemetaan AI</span>
            </button>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* STEP 2: Preview AI Proposal & Adjust Column Mapping               */}
      {/* ================================================================= */}
      {step === 2 && preview && (
        <div className="space-y-4">
          {/* AI Status Banner */}
          {aiMode === "LOADING" ? (
            <div className="p-3 rounded-lg bg-primary/10 border border-primary/30 flex items-center gap-2 text-primary">
              <Loader2 className="w-4 h-4 animate-spin shrink-0" />
              <span>Modul AI sedang membaca struktur header lembar kerja &ldquo;{activeSheet}&rdquo;...</span>
            </div>
          ) : aiMode === "AI" ? (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-start justify-between gap-3">
              <div className="flex items-start gap-2">
                <Sparkles className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <p className="font-semibold text-emerald-200">
                    Usulan Pemetaan AI Siap Ditinjau ({((aiProposal?.confidence_score || 0) * 100).toFixed(0)}%)
                  </p>
                  <p className="text-[11px] opacity-90">{aiProposal?.reasoning || aiMessage}</p>
                </div>
              </div>
              <span className="shrink-0 px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-200 font-mono text-[10px]">
                {mappingSource}
              </span>
            </div>
          ) : aiMode === "AMBIGUOUS" ? (
            <div className="p-3 rounded-lg bg-amber-500/15 border border-amber-500/40 text-amber-200 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="font-semibold">Pemetaan AI Ambigu — Wajib Verifikasi Manual</p>
                <p className="text-[11px] opacity-90">{aiMessage}</p>
                {aiProposal?.reasoning && (
                  <p className="text-[10px] font-mono opacity-80">Alasan AI: {aiProposal.reasoning}</p>
                )}
              </div>
            </div>
          ) : (
            <div className="p-3 rounded-lg bg-orange-500/15 border border-orange-500/40 text-orange-200 flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-orange-400 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="font-semibold">Mode Pemetaan Manual Aktif (Fallback AI)</p>
                <p className="text-[11px] opacity-90">{aiMessage}</p>
              </div>
            </div>
          )}

          {/* Sheet & Header Row Selector */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-lg bg-muted/20 border border-border">
            <div>
              <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                Lembar Kerja (Sheet)
              </label>
              <select
                value={activeSheet}
                onChange={(e) => handleSheetChange(e.target.value)}
                disabled={isReparsing || aiMode === "LOADING"}
                className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs font-mono outline-none focus:ring-2 focus:ring-primary/40"
              >
                {preview.sheet_names.map((sname) => (
                  <option key={sname} value={sname}>
                    {sname}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                Baris Header Tabel (1-based)
              </label>
              <input
                type="number"
                min={1}
                max={50}
                value={headerRowIndex}
                onChange={(e) => {
                  setHasEditedMapping(true);
                  setHeaderRowIndex(Math.max(1, parseInt(e.target.value, 10) || 1));
                }}
                className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs font-mono outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>
            <div className="flex items-end">
              <button
                type="button"
                onClick={() => importId && runAIMappingAndLoadPreview(importId, activeSheet)}
                disabled={aiMode === "LOADING" || isReparsing}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded border border-border bg-card hover:bg-muted text-foreground text-xs font-medium transition disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${aiMode === "LOADING" ? "animate-spin" : ""}`} />
                <span>Minta Ulang Saran AI</span>
              </button>
            </div>
          </div>

          {/* Canonical Field -> Excel Column Selectors */}
          <div className="p-3 rounded-lg border border-border bg-card space-y-2.5">
            <div className="flex items-center justify-between">
              <h4 className="font-mono font-semibold text-[11px] uppercase text-foreground">
                Pemetaan Kolom Skema Transaksi
              </h4>
              <span className="text-[10px] font-mono text-muted-foreground">
                File: {preview.filename} ({preview.file_hash?.slice(0, 12)}…)
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
              {CANONICAL_FIELDS.map((field) => {
                const selectedCol = columnMapping[field.key] || "";
                const headerSample =
                  selectedCol &&
                  preview.raw_preview_rows?.[headerRowIndex - 1]?.[Number(selectedCol) - 1];
                return (
                  <div key={field.key} className="space-y-1">
                    <label className="block text-[11px] font-medium text-foreground">
                      {field.label}
                      {field.required && <span className="text-destructive ml-0.5">*</span>}
                    </label>
                    <select
                      value={selectedCol}
                      onChange={(e) => handleMappingFieldChange(field.key, e.target.value)}
                      className="w-full px-2 py-1.5 bg-background border border-border rounded text-[11px] font-mono outline-none focus:ring-2 focus:ring-primary/40"
                    >
                      <option value="">-- Tidak Dipetakan --</option>
                      {Array.from({ length: maxGridCols }, (_, i) => i + 1).map((colNum) => {
                        const cellText = preview.raw_preview_rows?.[headerRowIndex - 1]?.[colNum - 1];
                        return (
                          <option key={colNum} value={colNum}>
                            Kolom {colIndexToLetter(colNum)} (#{colNum})
                            {cellText ? ` — ${String(cellText).slice(0, 20)}` : ""}
                          </option>
                        );
                      })}
                    </select>
                    <p className="text-[10px] text-muted-foreground truncate">
                      {headerSample ? `Header: "${String(headerSample)}"` : field.hint}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Raw Spreadsheet Grid Preview */}
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="px-3 py-2 bg-muted/40 border-b border-border flex items-center justify-between text-[11px] font-mono">
              <span>Pratinjau Sel Mentah (Baris 1–{preview.raw_preview_rows.length})</span>
              <span className="text-muted-foreground">Klik nomor baris untuk memilih baris header</span>
            </div>
            <div className="max-h-52 overflow-auto">
              <table className="w-full border-collapse text-[11px] font-mono">
                <thead className="bg-muted/60 sticky top-0 z-10">
                  <tr>
                    <th className="px-2 py-1 border-b border-r border-border text-left w-10">#</th>
                    {Array.from({ length: maxGridCols }, (_, i) => i + 1).map((c) => {
                      const mappedFields = Object.entries(columnMapping)
                        .filter(([, col]) => Number(col) === c)
                        .map(([k]) => k);
                      return (
                        <th
                          key={c}
                          className={`px-2 py-1 border-b border-r border-border text-left whitespace-nowrap ${
                            mappedFields.length ? "bg-primary/15 text-primary" : "text-muted-foreground"
                          }`}
                        >
                          {colIndexToLetter(c)}
                          {mappedFields.length ? ` (${mappedFields.join(",")})` : ""}
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {preview.raw_preview_rows.map((row, rIdx) => {
                    const rowNum = rIdx + 1;
                    const isHeader = rowNum === headerRowIndex;
                    return (
                      <tr
                        key={rowNum}
                        onClick={() => {
                          setHasEditedMapping(true);
                          setHeaderRowIndex(rowNum);
                        }}
                        className={`cursor-pointer transition ${
                          isHeader
                            ? "bg-primary/15 text-foreground font-semibold"
                            : "hover:bg-muted/30 text-muted-foreground"
                        }`}
                      >
                        <td className="px-2 py-1 border-b border-r border-border text-right">
                          {rowNum}
                        </td>
                        {Array.from({ length: maxGridCols }, (_, cIdx) => (
                          <td
                            key={cIdx}
                            className="px-2 py-1 border-b border-r border-border max-w-[160px] truncate"
                            title={row[cIdx] != null ? String(row[cIdx]) : ""}
                          >
                            {row[cIdx] != null ? String(row[cIdx]) : ""}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Step 2 Footer */}
          <div className="flex items-center justify-between gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="flex items-center gap-1 px-3 py-1.5 text-xs rounded border border-border bg-card hover:bg-muted text-foreground transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Kembali</span>
            </button>
            <button
              type="button"
              onClick={handleApplyMappingAndContinue}
              disabled={isReparsing || aiMode === "LOADING"}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded bg-primary text-primary-foreground hover:opacity-90 transition shadow-xs disabled:opacity-50"
            >
              {isReparsing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowRight className="w-3.5 h-3.5" />}
              <span>Terapkan Pemetaan & Tinjau Baris</span>
            </button>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* STEP 3: Review Candidate Lines, Discrepancies & Confirm Draft     */}
      {/* ================================================================= */}
      {step === 3 && preview && (
        <div className="space-y-4">
          {/* Validation Errors (UC-02 5a) */}
          {(confirmError || validationErrors.length > 0) && (
            <div className="p-3 rounded-lg bg-destructive/15 border border-destructive/40 text-destructive space-y-1.5">
              <div className="flex items-center gap-2 font-semibold">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{confirmError || "Terdapat baris data yang belum valid."}</span>
              </div>
              {validationErrors.length > 0 && (
                <ul className="list-disc pl-5 text-[11px] space-y-0.5">
                  {validationErrors.map((ve, i) => (
                    <li key={i}>{ve.message}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-[11px]">
            <div className="p-2.5 rounded border border-border bg-muted/20">
              <span className="block font-mono text-muted-foreground uppercase text-[10px]">
                Sekolah & Periode
              </span>
              <span className="font-semibold text-foreground block truncate">
                {selectedSchoolId
                  ? schools.find((s) => s.id === selectedSchoolId)?.name || "Sekolah Terpilih"
                  : preview.school_candidate?.name || "Deteksi Otomatis"}
              </span>
              <span className="font-mono text-muted-foreground">
                TA {fiscalYear} • TW {quarter} • {fundSource}
              </span>
            </div>
            <div className="p-2.5 rounded border border-border bg-muted/20">
              <span className="block font-mono text-muted-foreground uppercase text-[10px]">
                Referensi Sumber & Pemetaan
              </span>
              <span className="font-mono text-foreground block truncate">{preview.filename}</span>
              <span className="font-mono text-muted-foreground">
                Mode: {mappingSource} • Sheet: {activeSheet}
              </span>
            </div>
            <div className="p-2.5 rounded border border-border bg-primary/5">
              <span className="block font-mono text-muted-foreground uppercase text-[10px]">
                Estimasi Finansial (Hitung Ulang)
              </span>
              <span className="font-mono font-bold text-primary text-sm block tabular-nums">
                Rp {estimatedTotals.grandTotal.toLocaleString("id-ID")}
              </span>
              <span className="font-mono text-muted-foreground text-[10px] tabular-nums">
                Subtotal Rp {estimatedTotals.subtotal.toLocaleString("id-ID")} + PPN Rp{" "}
                {estimatedTotals.taxTotal.toLocaleString("id-ID")}
              </span>
            </div>
          </div>

          {/* Discrepancy Warnings */}
          {preview.detected_discrepancies && preview.detected_discrepancies.length > 0 && (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 space-y-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-amber-300">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                <span>
                  Terdeteksi {preview.detected_discrepancies.length} Anomali Sumber Excel (Akan Ditinjau di Draf)
                </span>
              </div>
              <div className="max-h-24 overflow-auto space-y-1 text-[11px] text-amber-200/90">
                {preview.detected_discrepancies.slice(0, 5).map((d, i) => (
                  <div key={i} className="font-mono">
                    [{d.sheet_name}
                    {d.cell_coordinate ? `!${d.cell_coordinate}` : ""}] {d.rule_category}: {d.expected_or_note}
                  </div>
                ))}
                {preview.detected_discrepancies.length > 5 && (
                  <div className="text-[10px] opacity-80">
                    +{preview.detected_discrepancies.length - 5} temuan lainnya…
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Editable Extracted Lines Table */}
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="px-3 py-2 bg-muted/40 border-b border-border flex items-center justify-between">
              <span className="font-mono font-semibold text-[11px]">
                Rincian Item Transaksi ({editableLines.length} baris)
              </span>
              <button
                type="button"
                onClick={addEmptyLine}
                className="flex items-center gap-1 px-2 py-1 rounded bg-primary/10 hover:bg-primary/20 text-primary text-[11px] font-semibold transition"
              >
                <Plus className="w-3 h-3" />
                <span>Tambah Baris</span>
              </button>
            </div>
            <div className="max-h-60 overflow-auto">
              <table className="w-full border-collapse text-[11px]">
                <thead className="bg-muted/50 sticky top-0 z-10 font-mono text-muted-foreground">
                  <tr>
                    <th className="px-2 py-1.5 border-b border-border text-left w-8">No</th>
                    <th className="px-2 py-1.5 border-b border-border text-left">Uraian Barang *</th>
                    <th className="px-2 py-1.5 border-b border-border text-left">Spesifikasi</th>
                    <th className="px-2 py-1.5 border-b border-border text-right w-16">Qty *</th>
                    <th className="px-2 py-1.5 border-b border-border text-left w-20">Satuan *</th>
                    <th className="px-2 py-1.5 border-b border-border text-right w-28">Harga HPS</th>
                    <th className="px-2 py-1.5 border-b border-border text-right w-28">Harga Final</th>
                    <th className="px-2 py-1.5 border-b border-border text-right w-28">Total</th>
                    <th className="px-2 py-1.5 border-b border-border w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {editableLines.map((line, idx) => {
                    const hasRowErr = validationErrors.some((ve) => ve.row_index === idx + 1);
                    return (
                      <tr
                        key={idx}
                        className={`border-b border-border ${hasRowErr ? "bg-destructive/10" : "hover:bg-muted/20"}`}
                      >
                        <td className="px-2 py-1 font-mono text-muted-foreground">{idx + 1}</td>
                        <td className="px-1.5 py-1">
                          <input
                            type="text"
                            value={line.confirmed_description || ""}
                            onChange={(e) => updateLineField(idx, "confirmed_description", e.target.value)}
                            className="w-full px-1.5 py-1 bg-background border border-border rounded text-[11px]"
                          />
                        </td>
                        <td className="px-1.5 py-1">
                          <input
                            type="text"
                            value={line.specification || ""}
                            onChange={(e) => updateLineField(idx, "specification", e.target.value)}
                            className="w-full px-1.5 py-1 bg-background border border-border rounded text-[11px]"
                          />
                        </td>
                        <td className="px-1.5 py-1">
                          <input
                            type="number"
                            min={0}
                            step="any"
                            value={line.quantity}
                            onChange={(e) =>
                              updateLineField(idx, "quantity", parseFloat(e.target.value) || 0)
                            }
                            className="w-full px-1.5 py-1 bg-background border border-border rounded text-[11px] text-right font-mono tabular-nums"
                          />
                        </td>
                        <td className="px-1.5 py-1">
                          <input
                            type="text"
                            value={line.unit || ""}
                            onChange={(e) => updateLineField(idx, "unit", e.target.value)}
                            className="w-full px-1.5 py-1 bg-background border border-border rounded text-[11px]"
                          />
                        </td>
                        <td className="px-1.5 py-1">
                          <input
                            type="number"
                            min={0}
                            step="any"
                            value={line.hps_unit_price}
                            onChange={(e) =>
                              updateLineField(idx, "hps_unit_price", parseFloat(e.target.value) || 0)
                            }
                            className="w-full px-1.5 py-1 bg-background border border-border rounded text-[11px] text-right font-mono tabular-nums"
                          />
                        </td>
                        <td className="px-1.5 py-1">
                          <input
                            type="number"
                            min={0}
                            step="any"
                            value={line.final_unit_price}
                            onChange={(e) =>
                              updateLineField(idx, "final_unit_price", parseFloat(e.target.value) || 0)
                            }
                            className="w-full px-1.5 py-1 bg-background border border-border rounded text-[11px] text-right font-mono tabular-nums"
                          />
                        </td>
                        <td className="px-2 py-1 text-right font-mono tabular-nums">
                          Rp {Number(line.line_total || 0).toLocaleString("id-ID")}
                        </td>
                        <td className="px-1.5 py-1 text-center">
                          <button
                            type="button"
                            onClick={() => removeLine(idx)}
                            title="Hapus baris"
                            className="p-1 text-muted-foreground hover:text-destructive transition"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                  {editableLines.length === 0 && (
                    <tr>
                      <td colSpan={9} className="px-3 py-4 text-center text-muted-foreground font-mono">
                        Tidak ada baris item terekstrak. Kembali ke Langkah 2 untuk menyesuaikan pemetaan kolom atau tambah baris manual.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
              Catatan Impor (Opsional)
            </label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={`Contoh: Impor HPS ${preview.filename}`}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {/* Step 3 Footer */}
          <div className="flex items-center justify-between gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={() => setStep(2)}
              className="flex items-center gap-1 px-3 py-1.5 text-xs rounded border border-border bg-card hover:bg-muted text-foreground transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Ubah Pemetaan Kolom</span>
            </button>
            <button
              type="button"
              onClick={handleConfirmImport}
              disabled={isConfirming || editableLines.length === 0}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded bg-primary text-primary-foreground hover:opacity-90 transition shadow-xs disabled:opacity-50"
            >
              {isConfirming ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5" />
              )}
              <span>Konfirmasi & Simpan sebagai Draf</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
