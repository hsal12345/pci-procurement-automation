"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  FileSpreadsheet,
  FileText,
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
  ImportProgressState,
  ImportUploadResponse,
} from "@/types/imports";
import { ImportAIProgressPanel } from "./ai-progress-panel";

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

function normalizeSchoolName(name?: string | null, stripShift = false, stripLeadingZeros = false): string {
  if (!name) return "";
  let txt = name
    .toUpperCase()
    .replace(/[^A-Z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const replacements: Array<[RegExp, string]> = [
    [/\bSEKOLAH DASAR NEGERI\b/g, "SDN"],
    [/\bSD NEGERI\b/g, "SDN"],
    [/\bSEKOLAH DASAR SWASTA\b/g, "SDS"],
    [/\bSD SWASTA\b/g, "SDS"],
    [/\bSEKOLAH MENENGAH PERTAMA NEGERI\b/g, "SMPN"],
    [/\bSMP NEGERI\b/g, "SMPN"],
    [/\bSEKOLAH MENENGAH ATAS NEGERI\b/g, "SMAN"],
    [/\bSMA NEGERI\b/g, "SMAN"],
    [/\bSEKOLAH MENENGAH KEJURUAN NEGERI\b/g, "SMKN"],
    [/\bSMK NEGERI\b/g, "SMKN"],
  ];
  for (const [pat, repl] of replacements) {
    txt = txt.replace(pat, repl);
  }
  if (stripShift) {
    txt = txt.replace(/\b(PAGI|PETANG|SIANG|SORE)\b/g, "");
  }
  if (stripLeadingZeros) {
    txt = txt.replace(/\b0+(\d+)\b/g, "$1");
  }
  return txt.replace(/\s+/g, " ").trim();
}

function matchMasterSchool(
  schools: SchoolOption[],
  candidateName?: string | null,
  npsn?: string | null
): SchoolOption | undefined {
  if (!schools.length) return undefined;
  const cleanNpsn = (npsn || "").replace(/\D/g, "");
  if (cleanNpsn) {
    const byNpsn = schools.find((s) => (s.npsn || "").replace(/\D/g, "") === cleanNpsn);
    if (byNpsn) return byNpsn;
  }
  if (!candidateName) return undefined;

  const exactNorm = normalizeSchoolName(candidateName, false, false);
  if (exactNorm) {
    const exactMatch = schools.find((s) => normalizeSchoolName(s.name, false, false) === exactNorm);
    if (exactMatch) return exactMatch;
  }
  const relaxed = normalizeSchoolName(candidateName, true, true);
  if (relaxed) {
    const relaxedMatch = schools.find((s) => normalizeSchoolName(s.name, true, true) === relaxed);
    if (relaxedMatch) return relaxedMatch;
  }
  if (relaxed.length >= 8) {
    return schools.find((s) => {
      const sRel = normalizeSchoolName(s.name, true, true);
      return sRel.length >= 8 && (sRel.includes(relaxed) || relaxed.includes(sRel));
    });
  }
  return undefined;
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
  const [hasManualSchool, setHasManualSchool] = useState(false);
  const [hasManualFiscalYear, setHasManualFiscalYear] = useState(false);
  const [hasManualQuarter, setHasManualQuarter] = useState(false);
  const [fundSource, setFundSource] = useState<string>("BOS_REGULER");
  const [isDownloading, setIsDownloading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [aiProgress, setAiProgress] = useState<ImportProgressState | null>(null);
  const [showDocContext, setShowDocContext] = useState(false);
  const progressUnsubRef = useRef<(() => void) | null>(null);

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
    return () => {
      progressUnsubRef.current?.();
      progressUnsubRef.current = null;
    };
  }, []);

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

  useEffect(() => {
    if (hasManualSchool || selectedSchoolId || schools.length === 0 || !preview) {
      return;
    }
    const cand = preview.school_candidate || {};
    if (cand.matched_school_id && schools.some((s) => s.id === cand.matched_school_id)) {
      setSelectedSchoolId(cand.matched_school_id);
      return;
    }
    const aiName = aiProposal?.detected_school_name || null;
    const candName = cand.detected ? cand.name : null;
    const matched =
      (aiName ? matchMasterSchool(schools, aiName, cand.npsn) : undefined) ||
      (candName ? matchMasterSchool(schools, candName, cand.npsn) : undefined);
    if (matched) {
      setSelectedSchoolId(matched.id);
    }
  }, [schools, preview, aiProposal, hasManualSchool, selectedSchoolId]);

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

  const getFormatBadge = (filename: string): string => {
    const ext = filename.split(".").pop()?.toUpperCase() || "FILE";
    return ["XLSX", "PDF", "DOCX", "DOC"].includes(ext) ? ext : "DOKUMEN";
  };

  const selectImportFile = (selected: File | null | undefined) => {
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
    const supported = [".xlsx", ".pdf", ".docx", ".doc"];
    if (!supported.some((ext) => lowerName.endsWith(ext))) {
      setUploadError(
        "Format berkas tidak didukung. Unggah berkas berekstensi .xlsx, .pdf, .doc, atau .docx."
      );
      setFile(null);
      return;
    }
    if (selected.size <= 0) {
      setUploadError("Berkas dokumen kosong (0 byte) dan tidak dapat diproses.");
      setFile(null);
      return;
    }
    if (selected.size > 20 * 1024 * 1024) {
      setUploadError("Ukuran berkas dokumen melebihi batas maksimal 20 MB.");
      setFile(null);
      return;
    }

    setFile(selected);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    selectImportFile(f);
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
      setUploadError("Unggah satu dokumen pengadaan (.xlsx, .pdf, .doc, .docx) dalam satu waktu.");
      return;
    }
    selectImportFile(droppedFiles[0]);
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

  const applyDetectedContextFromPreview = (
    freshPreview: ImportPreviewResponse,
    prop?: CandidateMappingProposal | ImportPreviewResponse["ai_proposal"] | null
  ) => {
    const trx = freshPreview.transaction_metadata || {};
    const cand = freshPreview.school_candidate || {};

    if (!hasManualFiscalYear) {
      const detectedYear =
        prop?.detected_fiscal_year ||
        (trx.tahun_anggaran_detected && trx.tahun_anggaran ? Number(trx.tahun_anggaran) : null);
      if (detectedYear && detectedYear >= 2000 && detectedYear <= 2100) {
        setFiscalYear(detectedYear);
      }
    }

    if (!hasManualQuarter) {
      const detectedQ =
        prop?.detected_quarter ||
        (trx.triwulan_detected && trx.triwulan ? Number(trx.triwulan) : null);
      if (detectedQ && detectedQ >= 1 && detectedQ <= 4) {
        setQuarter(detectedQ);
      }
    }

    if (!hasManualSchool && schools.length > 0) {
      if (cand.matched_school_id && schools.some((s) => s.id === cand.matched_school_id)) {
        setSelectedSchoolId(cand.matched_school_id);
      } else {
        const aiName = prop?.detected_school_name || null;
        const candName = cand.detected ? cand.name : null;
        const matched =
          (aiName ? matchMasterSchool(schools, aiName, cand.npsn) : undefined) ||
          (candName ? matchMasterSchool(schools, candName, cand.npsn) : undefined) ||
          (!candName && !aiName && cand.name ? matchMasterSchool(schools, cand.name, cand.npsn) : undefined);
        if (matched) {
          setSelectedSchoolId(matched.id);
        }
      }
    }
  };

  const applyResolvedPreviewAndProposal = (
    freshPreview: ImportPreviewResponse,
    proposalOverride?: CandidateMappingProposal | ImportPreviewResponse["ai_proposal"] | null
  ) => {
    setPreview(freshPreview);
    setEditableLines(freshPreview.candidate_lines || []);
    const prop = proposalOverride ?? freshPreview.ai_proposal ?? null;
    applyDetectedContextFromPreview(freshPreview, prop);
    if (prop && prop.column_mapping && Object.keys(prop.column_mapping).length > 0) {
      setAiProposal({
        sheet_name: prop.sheet_name || freshPreview.active_sheet,
        header_row_index: prop.header_row_index,
        column_mapping: prop.column_mapping,
        confidence_score: prop.confidence_score,
        reasoning: prop.reasoning || "",
        is_ambiguous: prop.is_ambiguous,
        detected_school_name: prop.detected_school_name ?? null,
        detected_fiscal_year: prop.detected_fiscal_year ?? null,
        detected_quarter: prop.detected_quarter ?? null,
      });
      setColumnMapping(prop.column_mapping || freshPreview.detected_mapping || {});
      setHeaderRowIndex(prop.header_row_index || freshPreview.header_row_index || 1);
      if (prop.sheet_name) setActiveSheet(prop.sheet_name);

      if (prop.is_ambiguous || prop.confidence_score < 0.8) {
        setAiMode("AMBIGUOUS");
        setAiMessage(
          `Skor keyakinan AI ${(prop.confidence_score * 100).toFixed(0)}% (< 80%). Wajib tinjau dan sesuaikan pemetaan kolom secara manual.`
        );
      } else {
        setAiMode("AI");
        setAiMessage(
          `AI memetakan ${Object.keys(prop.column_mapping || {}).length} kolom dengan keyakinan ${(prop.confidence_score * 100).toFixed(0)}%.`
        );
      }
    } else {
      setAiProposal(null);
      setAiMode("MANUAL_FALLBACK");
      setColumnMapping(freshPreview.detected_mapping || {});
      setHeaderRowIndex(freshPreview.header_row_index || 1);
      setAiMessage(
        `${freshPreview.ai_error || "Layanan AI tidak menghasilkan usulan pemetaan."} Dialihkan ke Mode Pemetaan Manual dengan deteksi heuristik awal.`
      );
    }
  };

  const runAIMappingAndLoadPreview = async (
    targetImportId: string,
    sheetOverride?: string,
    uploadInfo?: ImportUploadResponse
  ) => {
    progressUnsubRef.current?.();
    progressUnsubRef.current = null;

    setAiMode("LOADING");
    setAiMessage(null);
    setHasEditedMapping(false);

    let loadedPreview: ImportPreviewResponse | null = null;
    try {
      loadedPreview = await apiClient.getImportPreview(targetImportId);
      setPreview(loadedPreview);
      const sheetToUse = sheetOverride || loadedPreview.active_sheet || "HPS";
      setActiveSheet(sheetToUse);
      setEditableLines(loadedPreview.candidate_lines || []);
      if (loadedPreview.progress) {
        setAiProgress(loadedPreview.progress);
      }
    } catch (err: any) {
      setUploadError(err?.message || "Gagal memuat pratinjau berkas impor.");
      return;
    }

    const targetSheet = sheetOverride || loadedPreview.active_sheet || loadedPreview.sheet_names?.[0];

    try {
      const startRes = await apiClient.suggestAIMappingAsync(targetImportId, targetSheet);
      if (startRes?.progress) {
        setAiProgress(startRes.progress);
      }

      await new Promise<void>((resolve) => {
        const unsub = apiClient.subscribeImportProgress(
          targetImportId,
          (state) => {
            setAiProgress(state);
          },
          async (finalState) => {
            setAiProgress(finalState);
            try {
              const latestPreview = await apiClient.getImportPreview(targetImportId);
              applyResolvedPreviewAndProposal(latestPreview, finalState.result || latestPreview.ai_proposal);
            } catch {
              if (finalState.result) {
                applyResolvedPreviewAndProposal(loadedPreview!, finalState.result);
              } else {
                setAiProposal(null);
                setAiMode("MANUAL_FALLBACK");
                setColumnMapping(loadedPreview!.detected_mapping || {});
                setHeaderRowIndex(loadedPreview!.header_row_index || 1);
                setAiMessage(finalState.error || "Layanan AI tidak tersedia; dialihkan ke pemetaan manual.");
              }
            }
            resolve();
          },
          async () => {
            // Fallback to direct synchronous suggestAIMapping if both SSE and polling fail
            try {
              const proposal = await apiClient.suggestAIMapping(targetImportId, targetSheet);
              applyResolvedPreviewAndProposal(loadedPreview!, proposal);
            } catch (err: any) {
              setAiProposal(null);
              setAiMode("MANUAL_FALLBACK");
              setColumnMapping(loadedPreview!.detected_mapping || {});
              setHeaderRowIndex(loadedPreview!.header_row_index || 1);
              const detail =
                err instanceof ApiError
                  ? err.message
                  : err?.message || "Layanan AI sedang tidak tersedia atau batas anggaran tercapai.";
              setAiMessage(`${detail} Dialihkan ke Mode Pemetaan Manual dengan deteksi heuristik awal.`);
            }
            resolve();
          }
        );
        progressUnsubRef.current = unsub;
      });
    } catch (err: any) {
      // Fallback to synchronous call or manual mode
      try {
        const proposal = await apiClient.suggestAIMapping(targetImportId, targetSheet);
        applyResolvedPreviewAndProposal(loadedPreview, proposal);
      } catch (syncErr: any) {
        setAiProposal(null);
        setAiMode("MANUAL_FALLBACK");
        setColumnMapping(loadedPreview.detected_mapping || {});
        setHeaderRowIndex(loadedPreview.header_row_index || 1);
        const detail =
          syncErr instanceof ApiError
            ? syncErr.message
            : syncErr?.message || err?.message || "Layanan AI sedang tidak tersedia atau batas anggaran tercapai.";
        setAiMessage(`${detail} Dialihkan ke Mode Pemetaan Manual dengan deteksi heuristik awal.`);
        if (uploadInfo?.source_format) {
          setAiProgress((prev) =>
            prev
              ? { ...prev, status: "FALLBACK", percent: 100, detail: detail }
              : null
          );
        }
      }
    }
  };

  // Step 1 -> Step 2 (SD-02 Message 1 & 2)
  const handleUploadAndAnalyze = async () => {
    if (!file) {
      setUploadError("Pilih dokumen (.xlsx, .pdf, .doc, atau .docx) terlebih dahulu.");
      return;
    }
    setUploadError(null);
    setIsUploading(true);
    const fmt = getFormatBadge(file.name);
    setAiProgress({
      import_id: "pending",
      stage: "UPLOAD",
      stage_index: 1,
      total_stages: 5,
      percent: 5,
      label: "Mengunggah Berkas",
      detail: `Mengirim ${file.name} (${(file.size / 1024).toFixed(1)} KB)...`,
      status: "RUNNING",
      source_format: fmt,
      elapsed_ms: 0,
      events: [
        {
          timestamp: new Date().toISOString(),
          elapsed_ms: 0,
          stage: "UPLOAD",
          percent: 5,
          label: "Mengunggah Berkas",
          detail: `Memulai unggahan dokumen ${fmt} (${file.name})...`,
          status: "RUNNING",
        },
      ],
    });

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (selectedSchoolId) formData.append("school_id", selectedSchoolId);
      if (hasManualFiscalYear) formData.append("fiscal_year", String(fiscalYear));
      if (hasManualQuarter) formData.append("quarter", String(quarter));
      formData.append("fund_source", fundSource);

      const uploadData = await apiClient.uploadImportDocumentWithProgress(formData, (pct) => {
        if (pct < 100) {
          const scaled = Math.max(5, Math.min(18, Math.round(5 + pct * 0.13)));
          setAiProgress((prev) =>
            prev
              ? {
                  ...prev,
                  stage: "UPLOAD",
                  stage_index: 1,
                  percent: scaled,
                  detail: `Mengunggah berkas ke server (${pct}%)...`,
                }
              : prev
          );
        } else {
          setAiProgress((prev) =>
            prev
              ? {
                  ...prev,
                  stage: "EXTRACT_VALIDATE",
                  stage_index: 2,
                  percent: 28,
                  label: "Ekstraksi Konten & Konteks",
                  detail: `Kode backend sedang memvalidasi & mengekstrak tabel + konteks ${fmt}...`,
                  events: [
                    ...prev.events,
                    {
                      timestamp: new Date().toISOString(),
                      elapsed_ms: 400,
                      stage: "EXTRACT_VALIDATE",
                      percent: 28,
                      label: "Ekstraksi Konten & Konteks",
                      detail: `Berkas diterima; mengekstrak tabel, kop sekolah, dan metadata ${fmt}...`,
                      status: "RUNNING",
                    },
                  ],
                }
              : prev
          );
        }
      });

      setImportId(uploadData.import_id);
      setStep(2);
      setIsUploading(false);
      await runAIMappingAndLoadPreview(uploadData.import_id, uploadData.active_sheet || undefined, uploadData);
    } catch (err: any) {
      setUploadError(err?.message || "Dokumen gagal diunggah atau strukturnya tidak valid.");
      setAiProgress(null);
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
          { num: 1, label: "1. Unggah Dokumen & Sekolah" },
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
              onChange={(e) => {
                const val = e.target.value;
                setSelectedSchoolId(val);
                setHasManualSchool(Boolean(val));
              }}
              className="w-full px-2.5 py-2 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition"
            >
              <option value="">Deteksi Otomatis dari Dokumen (cocokkan Master Sekolah)</option>
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
                Tahun Anggaran{" "}
                {!hasManualFiscalYear && (
                  <span className="text-[9px] text-primary lowercase">(auto dokumen)</span>
                )}
              </label>
              <input
                type="number"
                value={fiscalYear}
                onChange={(e) => {
                  setFiscalYear(parseInt(e.target.value, 10) || 2026);
                  setHasManualFiscalYear(true);
                }}
                className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono tabular-nums transition"
              />
            </div>
            <div>
              <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                Triwulan (TW){" "}
                {!hasManualQuarter && (
                  <span className="text-[9px] text-primary lowercase">(auto dokumen)</span>
                )}
              </label>
              <select
                value={quarter}
                onChange={(e) => {
                  setQuarter(parseInt(e.target.value, 10) || 1);
                  setHasManualQuarter(true);
                }}
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
              id="doc-upload-wizard"
              accept=".xlsx,.pdf,.doc,.docx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
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
              htmlFor="doc-upload-wizard"
              className="cursor-pointer flex flex-col items-center justify-center gap-2"
            >
              {isDragging ? (
                <>
                  <UploadCloud className="w-9 h-9 text-primary animate-bounce" />
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-primary">
                      Lepaskan dokumen (.xlsx, .pdf, .doc, .docx) di sini
                    </span>
                    <span className="block text-[10px] text-primary/80 font-mono">
                      Tabel &amp; konteks dokumen akan diekstrak otomatis sebelum dipetakan oleh AI
                    </span>
                  </div>
                </>
              ) : file ? (
                <>
                  {file.name.toLowerCase().endsWith(".xlsx") ? (
                    <FileSpreadsheet className="w-8 h-8 text-emerald-400" />
                  ) : (
                    <FileText className="w-8 h-8 text-emerald-400" />
                  )}
                  <div className="space-y-1">
                    <div className="flex items-center justify-center gap-1.5">
                      <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-[10px] border border-emerald-500/30">
                        {getFormatBadge(file.name)}
                      </span>
                      <span className="font-semibold text-foreground font-mono">{file.name}</span>
                    </div>
                    <span className="block text-[10px] text-muted-foreground">
                      ({(file.size / 1024).toFixed(1)} KB) — Seret berkas lain atau klik untuk mengganti
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <UploadCloud className="w-8 h-8 text-primary/70" />
                  <div className="space-y-1.5">
                    <span className="text-xs font-semibold text-foreground">
                      Seret &amp; lepaskan dokumen ke sini, atau klik untuk memilih
                    </span>
                    <div className="flex flex-wrap items-center justify-center gap-1 text-[10px] font-mono">
                      {[".XLSX", ".PDF", ".DOCX", ".DOC"].map((ext) => (
                        <span
                          key={ext}
                          className="px-1.5 py-0.5 rounded bg-muted/60 text-foreground border border-border"
                        >
                          {ext}
                        </span>
                      ))}
                      <span className="text-muted-foreground ml-1">• Maks. 20 MB</span>
                    </div>
                    <span className="block text-[10px] text-muted-foreground">
                      Konten &amp; tabel diekstrak otomatis di server agar LLM lebih akurat memetakan kolom
                    </span>
                  </div>
                </>
              )}
            </label>
          </div>

          {isUploading && aiProgress && (
            <ImportAIProgressPanel progress={aiProgress} filename={file?.name} compactAfterComplete={false} />
          )}

          {/* Template Download Strip */}
          <div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground font-mono bg-muted/20 p-2.5 rounded border border-border">
            <div className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
              <span>Ingin format paling rapi? Gunakan template Excel standar (.xlsx) atau unggah PDF/Word langsung.</span>
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
          {/* Live AI Progress Tracker & Result Banner */}
          {aiProgress && (
            <ImportAIProgressPanel
              progress={aiProgress}
              filename={preview.filename}
              compactAfterComplete={aiMode !== "LOADING"}
            />
          )}

          {aiMode === "LOADING" && !aiProgress ? (
            <div className="p-3 rounded-lg bg-primary/10 border border-primary/30 flex items-center gap-2 text-primary">
              <Loader2 className="w-4 h-4 animate-spin shrink-0" />
              <span>Menyiapkan aliran progres ekstraksi &amp; pemetaan AI...</span>
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
          ) : aiMode === "MANUAL_FALLBACK" ? (
            <div className="p-3 rounded-lg bg-orange-500/15 border border-orange-500/40 text-orange-200 flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-orange-400 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="font-semibold">Mode Pemetaan Manual Aktif (Fallback AI)</p>
                <p className="text-[11px] opacity-90">{aiMessage}</p>
              </div>
            </div>
          ) : null}

          {/* Collapsible Extracted Document Context (Pre-LLM) */}
          {preview.document_context?.snippets && preview.document_context.snippets.length > 0 && (
            <div className="border border-border rounded-lg bg-muted/15 overflow-hidden">
              <button
                type="button"
                onClick={() => setShowDocContext((v) => !v)}
                className="w-full px-3 py-2 flex items-center justify-between text-[11px] font-mono hover:bg-muted/30 transition"
              >
                <div className="flex items-center gap-2 text-foreground">
                  <FileText className="w-3.5 h-3.5 text-primary" />
                  <span>
                    Konteks Dokumen Terekstrak ({preview.source_format || "DOKUMEN"} •{" "}
                    {preview.document_context.snippets.length} baris konteks pra-LLM)
                  </span>
                </div>
                {showDocContext ? (
                  <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
                )}
              </button>
              {showDocContext && (
                <div className="px-3 pb-2.5 pt-1 border-t border-border/60 space-y-1.5 text-[11px]">
                  <div className="flex flex-wrap gap-2 font-mono text-[10px]">
                    {preview.school_candidate?.name && (
                      <span className="px-2 py-0.5 rounded bg-background border border-border">
                        Sekolah: <strong>{preview.school_candidate.name}</strong>
                      </span>
                    )}
                    {preview.transaction_metadata?.kegiatan && (
                      <span className="px-2 py-0.5 rounded bg-background border border-border">
                        Kegiatan: <strong>{preview.transaction_metadata.kegiatan}</strong>
                      </span>
                    )}
                  </div>
                  <div className="max-h-28 overflow-y-auto bg-background/70 border border-border rounded p-2 font-mono text-[10px] text-muted-foreground space-y-0.5">
                    {preview.document_context.snippets.slice(0, 15).map((line, i) => (
                      <div key={i} className="truncate">
                        {line}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Section / Table & Header Row Selector */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-lg bg-muted/20 border border-border">
            <div>
              <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                Bagian / Tabel Dokumen
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

          {/* Summary & Verification Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-[11px]">
            <div className="p-2.5 rounded border border-border bg-muted/20 space-y-1.5">
              <div className="flex items-center justify-between gap-1">
                <span className="font-mono text-muted-foreground uppercase text-[10px]">
                  Sekolah &amp; Periode Penugasan
                </span>
                <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary font-mono text-[9px]">
                  {hasManualSchool || hasManualFiscalYear || hasManualQuarter
                    ? "Disunting"
                    : "Hasil Ekstraksi / AI"}
                </span>
              </div>
              <select
                value={selectedSchoolId}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedSchoolId(val);
                  setHasManualSchool(true);
                }}
                aria-label="Verifikasi Sekolah Penerima"
                className="w-full px-2 py-1 bg-background border border-border rounded text-[11px] font-semibold text-foreground outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">
                  Deteksi Otomatis:{" "}
                  {aiProposal?.detected_school_name ||
                    preview.school_candidate?.name ||
                    "Sekolah Baru"}
                </option>
                {schools.map((sc) => (
                  <option key={sc.id} value={sc.id}>
                    {sc.name} {sc.npsn ? `(${sc.npsn})` : ""}
                  </option>
                ))}
              </select>
              <div className="flex items-center gap-1.5 font-mono">
                <span className="text-[10px] text-muted-foreground">TA</span>
                <input
                  type="number"
                  value={fiscalYear}
                  onChange={(e) => {
                    setFiscalYear(parseInt(e.target.value, 10) || 2026);
                    setHasManualFiscalYear(true);
                  }}
                  aria-label="Verifikasi Tahun Anggaran"
                  className="w-16 px-1.5 py-0.5 bg-background border border-border rounded text-[11px] tabular-nums outline-none focus:ring-1 focus:ring-primary"
                />
                <span className="text-[10px] text-muted-foreground">•</span>
                <select
                  value={quarter}
                  onChange={(e) => {
                    setQuarter(parseInt(e.target.value, 10) || 2);
                    setHasManualQuarter(true);
                  }}
                  aria-label="Verifikasi Triwulan"
                  className="px-1.5 py-0.5 bg-background border border-border rounded text-[11px] outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value={1}>TW I</option>
                  <option value={2}>TW II</option>
                  <option value={3}>TW III</option>
                  <option value={4}>TW IV</option>
                </select>
                <select
                  value={fundSource}
                  onChange={(e) => setFundSource(e.target.value)}
                  aria-label="Verifikasi Sumber Dana"
                  className="flex-1 min-w-0 px-1.5 py-0.5 bg-background border border-border rounded text-[10px] outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="BOS_REGULER">BOS_REGULER</option>
                  <option value="BOS_KINERJA">BOS_KINERJA</option>
                  <option value="BOP">BOP</option>
                  <option value="LAINNYA">LAINNYA</option>
                </select>
              </div>
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
