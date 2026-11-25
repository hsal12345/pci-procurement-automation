"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { PackageItem, PackageRevision, UserRole } from "@/types/package";
import { ArchiveRecord, Artifact, GenerationJob } from "@/types/documents";
import { apiClient } from "@/lib/api-client";
import {
  FileText,
  Eye,
  Printer,
  RefreshCw,
  Loader2,
  X,
  AlertCircle,
  CheckCircle2,
  Clock,
  FileSpreadsheet,
  FileArchive,
  Layers,
  Cpu,
  Maximize2,
  ExternalLink,
  Download,
  ChevronLeft,
  ChevronRight,
  Cloud,
  CloudUpload,
  FolderOpen,
  Lock,
  ShieldCheck,
  Link2,
  Unlink,
} from "lucide-react";

interface TabDocumentsProps {
  revision: PackageRevision;
  packageData?: PackageItem;
  currentRole?: UserRole;
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

type StepStatus = "pending" | "active" | "done" | "failed";

interface PipelineStep {
  key: string;
  title: string;
  subtitle: string;
  countLabel: string;
  miniProgress: number;
  status: StepStatus;
  icon: typeof Cpu;
}

export function TabDocuments({ revision, packageData, currentRole }: TabDocumentsProps) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [currentJob, setCurrentJob] = useState<GenerationJob | null>(null);
  const [archiveRecord, setArchiveRecord] = useState<ArchiveRecord | null>(null);
  const [driveHealth, setDriveHealth] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isUploadingDrive, setIsUploadingDrive] = useState(false);
  const [isDisconnectingOAuth, setIsDisconnectingOAuth] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);
  const [driveUploadError, setDriveUploadError] = useState<string | null>(null);
  const [selectedPdfCode, setSelectedPdfCode] = useState<string>("MERGED_PDF");
  const [isPdfFullscreen, setIsPdfFullscreen] = useState(false);
  const pdfViewerRef = useRef<HTMLDivElement | null>(null);

  const isDraft =
    revision.status === "DRAFT" ||
    revision.status === "UNDER_REVIEW" ||
    revision.status === "RETURNED";
  const isApprovedForDrive =
    revision.status === "APPROVED" || revision.status === "ISSUED";
  const canGenerateDocuments =
    !currentRole ||
    currentRole === "ADMINISTRATION" ||
    currentRole === "FINANCE_DIRECTOR" ||
    currentRole === "SYSTEM_ADMINISTRATOR";
  const canTriggerDriveUpload =
    !currentRole ||
    currentRole === "ADMINISTRATION" ||
    currentRole === "SYSTEM_ADMINISTRATOR";

  const schoolName = revision.school_snapshot?.name || "Sekolah";
  const fiscalYear = packageData?.fiscal_year || new Date().getFullYear();
  const quarterNum = packageData?.quarter || 1;
  const packageCode = packageData?.package_code || packageData?.package_number || "Paket";
  const drivePackageFolderName =
    packageCode.replace(/[\\/]+/g, "-").replace(/\s+/g, " ").trim() || "Paket";

  const loadState = useCallback(async () => {
    setIsLoading(true);
    try {
      const [artsData, latestJob, archData, healthData] = await Promise.all([
        apiClient.getArtifacts(revision.id),
        apiClient.getLatestGenerationJob(revision.id),
        apiClient.getRevisionArchive(revision.id).catch(() => null),
        apiClient.getDriveHealth().catch(() => null),
      ]);
      setArtifacts(artsData);
      setCurrentJob(latestJob);
      setArchiveRecord(archData);
      setDriveHealth(healthData);
    } catch {
      setArtifacts([]);
    } finally {
      setIsLoading(false);
    }
  }, [revision.id]);

  useEffect(() => {
    loadState();
  }, [loadState]);

  useEffect(() => {
    const refreshDriveHealth = () => {
      apiClient.getDriveHealth().then(setDriveHealth).catch(() => {});
    };
    const onMessage = (ev: MessageEvent) => {
      if (ev?.data?.type === "gdrive-oauth-connected") {
        refreshDriveHealth();
      }
    };
    window.addEventListener("focus", refreshDriveHealth);
    window.addEventListener("message", onMessage);
    return () => {
      window.removeEventListener("focus", refreshDriveHealth);
      window.removeEventListener("message", onMessage);
    };
  }, []);

  // Poll job status & incremental artifacts while job is QUEUED or RUNNING
  const activeJobId =
    currentJob && (currentJob.status === "QUEUED" || currentJob.status === "RUNNING")
      ? currentJob.id
      : null;

  useEffect(() => {
    if (!activeJobId) {
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      try {
        const [updatedJob, updatedArtifacts] = await Promise.all([
          apiClient.getGenerationJob(activeJobId),
          apiClient.getArtifacts(revision.id).catch(() => null),
        ]);
        if (cancelled) return;

        if (updatedArtifacts) {
          setArtifacts(updatedArtifacts);
        }
        setCurrentJob(updatedJob);

        if (updatedJob.status === "QUEUED" || updatedJob.status === "RUNNING") {
          timer = setTimeout(poll, 800);
        } else {
          // Final artifact fetch once job reaches SUCCEEDED or FAILED
          const finalArts = await apiClient.getArtifacts(revision.id).catch(() => null);
          if (!cancelled && finalArts) {
            setArtifacts(finalArts);
          }
        }
      } catch {
        if (!cancelled) {
          timer = setTimeout(poll, 1200);
        }
      }
    };

    timer = setTimeout(poll, 600);

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [activeJobId, revision.id]);

  const handleTriggerGeneration = async () => {
    setIsGenerating(true);
    setTriggerError(null);
    try {
      const job = await apiClient.triggerGeneration(revision.id, ["ALL"]);
      setArtifacts([]);
      setCurrentJob(job);
    } catch (err: any) {
      setTriggerError(err?.message || "Gagal memicu pembuatan dokumen.");
    } finally {
      setIsGenerating(false);
    }
  };

  // Poll Google Drive upload progress while archiveRecord.status === "SYNCING"
  const isDriveSyncing = archiveRecord?.status === "SYNCING";
  useEffect(() => {
    if (!isDriveSyncing) {
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const pollDrive = async () => {
      try {
        const [updatedArchive, updatedArtifacts] = await Promise.all([
          apiClient.getRevisionArchive(revision.id),
          apiClient.getArtifacts(revision.id).catch(() => null),
        ]);
        if (cancelled) return;

        if (updatedArtifacts) {
          setArtifacts(updatedArtifacts);
        }
        setArchiveRecord(updatedArchive);

        if (updatedArchive && updatedArchive.status === "SYNCING") {
          timer = setTimeout(pollDrive, 600);
        }
      } catch {
        if (!cancelled) {
          timer = setTimeout(pollDrive, 1000);
        }
      }
    };

    timer = setTimeout(pollDrive, 600);

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [isDriveSyncing, revision.id]);

  const handleTriggerDriveUpload = async () => {
    setIsUploadingDrive(true);
    setDriveUploadError(null);
    try {
      const rec = await apiClient.triggerRevisionDriveUpload(revision.id);
      setArchiveRecord(rec);
    } catch (err: any) {
      setDriveUploadError(err?.message || "Gagal memulai unggah ke Google Drive.");
    } finally {
      setIsUploadingDrive(false);
    }
  };

  const handleDisconnectDriveOAuth = async () => {
    setIsDisconnectingOAuth(true);
    setDriveUploadError(null);
    try {
      await apiClient.disconnectDriveOAuth();
      const updated = await apiClient.getDriveHealth().catch(() => null);
      setDriveHealth(updated);
    } catch (err: any) {
      setDriveUploadError(err?.message || "Gagal memutus koneksi OAuth Google Drive.");
    } finally {
      setIsDisconnectingOAuth(false);
    }
  };

  const getArtifactForCode = (code: string, format: string) => {
    const fmt = format.toUpperCase();
    if (code === "XLSX") {
      return fmt === "XLSX"
        ? artifacts.find(
            (a) => (a.doc_code === "XLSX" || a.doc_code === "ALL") && a.format.toUpperCase() === "XLSX"
          )
        : undefined;
    }
    if (code === "MERGED_PDF") {
      return fmt === "PDF"
        ? artifacts.find(
            (a) => (a.doc_code === "MERGED_PDF" || a.doc_code === "ALL") && a.format.toUpperCase() === "PDF"
          )
        : undefined;
    }
    if (code === "ZIP") {
      return fmt === "ZIP"
        ? artifacts.find((a) => a.doc_code === "ZIP" && a.format.toUpperCase() === "ZIP")
        : undefined;
    }
    return artifacts.find((a) => a.doc_code === code && a.format.toUpperCase() === fmt);
  };

  // Ordered list of PDFs for the integrated PDF Viewer (Merged PDF first, then D01..D13)
  const pdfDocOrder = [
    ...DOC_REGISTRY.filter((d) => d.code === "MERGED_PDF"),
    ...DOC_REGISTRY.filter((d) => d.code.startsWith("D")),
  ];
  const availablePdfDocs = pdfDocOrder
    .map((doc) => ({ doc, artifact: getArtifactForCode(doc.code, "PDF") }))
    .filter((item): item is { doc: (typeof DOC_REGISTRY)[number]; artifact: Artifact } =>
      Boolean(item.artifact)
    );

  const activePdfIndex = availablePdfDocs.findIndex((item) => item.doc.code === selectedPdfCode);
  const activePdfEntry =
    activePdfIndex >= 0
      ? availablePdfDocs[activePdfIndex]
      : availablePdfDocs.length > 0
      ? availablePdfDocs[0]
      : null;

  const handleOpenPdfInViewer = (code: string) => {
    setSelectedPdfCode(code);
    pdfViewerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleStepPdf = (delta: number) => {
    if (availablePdfDocs.length === 0) return;
    const currentIdx = activePdfIndex >= 0 ? activePdfIndex : 0;
    const nextIdx = (currentIdx + delta + availablePdfDocs.length) % availablePdfDocs.length;
    setSelectedPdfCode(availablePdfDocs[nextIdx].doc.code);
  };

  // Real-time artifact & row counts
  const xlsxCount = artifacts.filter((a) => a.format.toUpperCase() === "XLSX").length;
  const docxCount = artifacts.filter((a) => a.format.toUpperCase() === "DOCX").length;
  const pdfCount = artifacts.filter((a) => a.format.toUpperCase() === "PDF").length;
  const zipCount = artifacts.filter((a) => a.format.toUpperCase() === "ZIP").length;
  const totalArtifactsCount = xlsxCount + docxCount + pdfCount + zipCount;

  const readyRowsCount = DOC_REGISTRY.filter((doc) => {
    if (doc.code === "XLSX") return Boolean(getArtifactForCode("XLSX", "XLSX"));
    if (doc.code === "MERGED_PDF") return Boolean(getArtifactForCode("MERGED_PDF", "PDF"));
    if (doc.code === "ZIP") return Boolean(getArtifactForCode("ZIP", "ZIP"));
    return Boolean(getArtifactForCode(doc.code, "DOCX") && getArtifactForCode(doc.code, "PDF"));
  }).length;

  const isJobQueued = currentJob?.status === "QUEUED";
  const isJobRunning = currentJob?.status === "RUNNING";
  const isJobActive = isJobQueued || isJobRunning;
  const isJobFailed = currentJob?.status === "FAILED";
  const jobPct = currentJob?.progress_percent ?? 0;

  const effectiveProgress = isJobActive
    ? Math.min(99, Math.max(jobPct, Math.round((totalArtifactsCount / 29) * 95)))
    : totalArtifactsCount >= 29 || (currentJob?.status === "SUCCEEDED" && totalArtifactsCount > 0)
    ? 100
    : totalArtifactsCount > 0
    ? Math.round((totalArtifactsCount / 29) * 100)
    : 0;

  // 5-stage pipeline state
  const step1Done =
    totalArtifactsCount > 0 ||
    currentJob?.status === "SUCCEEDED" ||
    ((isJobActive || isJobFailed) && jobPct >= 12);
  const step1Active = isJobActive && !step1Done;
  const step1Failed = isJobFailed && !step1Done;

  const step2Done = xlsxCount >= 1;
  const step2Active = isJobActive && !step2Done && jobPct >= 12 && jobPct < 25;
  const step2Failed = isJobFailed && !step2Done && jobPct >= 12 && jobPct < 25;

  const step3Done = docxCount >= 13;
  const step3Active =
    isJobActive && !step3Done && ((jobPct >= 25 && jobPct < 50) || (docxCount > 0 && docxCount < 13));
  const step3Failed =
    isJobFailed && !step3Done && ((jobPct >= 25 && jobPct < 50) || (docxCount > 0 && docxCount < 13));

  const step4Done = pdfCount >= 14;
  const step4Active =
    isJobActive && !step4Done && ((jobPct >= 50 && jobPct < 90) || (pdfCount > 0 && pdfCount < 14));
  const step4Failed =
    isJobFailed && !step4Done && ((jobPct >= 50 && jobPct < 90) || (pdfCount > 0 && pdfCount < 14));

  const step5Done = zipCount >= 1;
  const step5Active = isJobActive && !step5Done && jobPct >= 90;
  const step5Failed = isJobFailed && !step5Done && jobPct >= 90;

  const resolveStepStatus = (done: boolean, active: boolean, failed: boolean): StepStatus => {
    if (done) return "done";
    if (failed) return "failed";
    if (active) return "active";
    return "pending";
  };

  const pipelineSteps: PipelineStep[] = [
    {
      key: "context",
      title: "1. Konteks & Data",
      subtitle: "Snapshot & Baris",
      countLabel: step1Done ? "Siap" : step1Active ? "Menyiapkan..." : "Menunggu",
      miniProgress: step1Done ? 100 : step1Active ? 50 : 0,
      status: resolveStepStatus(step1Done, step1Active, step1Failed),
      icon: Cpu,
    },
    {
      key: "xlsx",
      title: "2. Buku Kerja Excel",
      subtitle: "00_PAKET_PENGADAAN",
      countLabel: `${Math.min(xlsxCount, 1)}/1 XLSX`,
      miniProgress: Math.min(100, Math.round((xlsxCount / 1) * 100)),
      status: resolveStepStatus(step2Done, step2Active, step2Failed),
      icon: FileSpreadsheet,
    },
    {
      key: "docx",
      title: "3. Dokumen Word",
      subtitle: "13 Berkas D01–D13",
      countLabel: `${Math.min(docxCount, 13)}/13 DOCX`,
      miniProgress: Math.min(100, Math.round((docxCount / 13) * 100)),
      status: resolveStepStatus(step3Done, step3Active, step3Failed),
      icon: FileText,
    },
    {
      key: "pdf",
      title: "4. Konversi & Bundel PDF",
      subtitle: "LibreOffice + Watermark",
      countLabel: `${Math.min(pdfCount, 14)}/14 PDF`,
      miniProgress: Math.min(100, Math.round((pdfCount / 14) * 100)),
      status: resolveStepStatus(step4Done, step4Active, step4Failed),
      icon: Layers,
    },
    {
      key: "zip",
      title: "5. Arsip ZIP & SHA-256",
      subtitle: "Manifest Integritas",
      countLabel: `${Math.min(zipCount, 1)}/1 ZIP`,
      miniProgress: Math.min(100, Math.round((zipCount / 1) * 100)),
      status: resolveStepStatus(step5Done, step5Active, step5Failed),
      icon: FileArchive,
    },
  ];

  // Overall status badge & stage message
  let statusBadgeText = "BELUM DIHASILKAN";
  let statusBadgeClass = "bg-muted text-muted-foreground border-border";
  let stageDescription =
    "Klik 'Hasilkan Seluruh Dokumen (Generate)' untuk membuat seluruh bundel dokumen SPJ.";
  let progressBarColor = "bg-muted-foreground/40";

  if (isJobQueued) {
    statusBadgeText = "DALAM ANTREAN";
    statusBadgeClass = "bg-blue-500/15 text-blue-600 dark:text-blue-300 border-blue-500/40";
    stageDescription = "Menunggu antrean pekerja latar belakang untuk memulai generator...";
    progressBarColor = "bg-primary";
  } else if (isJobRunning) {
    statusBadgeText = "SEDANG MEMPROSES";
    statusBadgeClass = "bg-primary/15 text-primary border-primary/40";
    progressBarColor = "bg-primary";
    if (step5Active) {
      stageDescription = "Mengemas arsip ZIP lengkap dan menghasilkan manifest integritas SHA-256...";
    } else if (step4Active) {
      stageDescription = `Mengonversi dokumen ke PDF via LibreOffice & menggabungkan bundel (${Math.min(pdfCount, 14)}/14 PDF)...`;
    } else if (step3Active) {
      stageDescription = `Merender template Word resmi D01–D13 (${Math.min(docxCount, 13)}/13 DOCX)...`;
    } else if (step2Active) {
      stageDescription = "Membuat buku kerja Excel konsolidasi (00_PAKET_PENGADAAN.xlsx)...";
    } else {
      stageDescription = "Menyiapkan konteks transaksi, snapshot & membersihkan berkas lama...";
    }
  } else if (isJobFailed) {
    statusBadgeText = "GAGAL";
    statusBadgeClass = "bg-red-500/15 text-red-600 dark:text-red-300 border-red-500/40";
    stageDescription = "Proses pembuatan dokumen terhenti karena galat pada generator.";
    progressBarColor = "bg-red-500";
  } else if (totalArtifactsCount >= 29) {
    statusBadgeText = "SELESAI • LENGKAP";
    statusBadgeClass = "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border-emerald-500/40";
    stageDescription =
      "Seluruh 29 berkas SPJ (1 XLSX, 13 DOCX, 14 PDF, 1 ZIP + Manifest) siap diunduh.";
    progressBarColor = "bg-emerald-500";
  } else if (totalArtifactsCount > 0) {
    statusBadgeText = "TERSEDIA SEBAGIAN";
    statusBadgeClass = "bg-amber-500/15 text-amber-600 dark:text-amber-300 border-amber-500/40";
    stageDescription = `${totalArtifactsCount} dari 29 berkas telah dihasilkan. Jalankan ulang generator untuk melengkapi paket.`;
    progressBarColor = "bg-amber-500";
  }

  return (
    <div className="p-6 max-w-5xl space-y-6 text-xs font-sans">
      {/* Top Action Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            Registri 13 Dokumen Pengadaan &amp; SPJ (D01-D13)
          </h3>
          <p className="text-xs text-muted-foreground font-mono mt-0.5">
            Format: XlsxWriter • DocxTemplate • LibreOffice Headless PDF • ZIP Manifest
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadState}
            disabled={isLoading}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition disabled:opacity-50"
            title="Segarkan daftar berkas dan status proses"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          </button>

          {canGenerateDocuments && (
            <button
              type="button"
              onClick={handleTriggerGeneration}
              disabled={isGenerating || isJobActive}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary text-primary-foreground font-semibold text-xs hover:opacity-90 transition shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isGenerating || isJobActive ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Printer className="w-3.5 h-3.5" />
              )}
              <span>
                {isJobActive
                  ? `Memproses Dokumen (${effectiveProgress}%)...`
                  : isGenerating
                  ? "Memulai Antrean..."
                  : "Hasilkan Seluruh Dokumen (Generate)"}
              </span>
            </button>
          )}
        </div>
      </div>

      {/* Watermark Notice Banner for Drafts */}
      {isDraft && (
        <div className="border border-amber-500/40 bg-amber-500/10 p-3 rounded-lg flex items-center justify-between text-amber-700 dark:text-amber-300 font-mono text-xs shadow-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-500 dark:text-amber-400 flex-shrink-0" />
            <span>
              STATUS REVISI MASIH DRAF: Dokumen Word &amp; PDF dicetak dengan tanda air watermark &quot;DRAFT / TIDAK RESMI&quot;.
            </span>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/40 text-amber-700 dark:text-amber-300 font-bold">
            WATERMARK AKTIF
          </span>
        </div>
      )}

      {/* Trigger Error Banner */}
      {triggerError && (
        <div className="border border-red-500/40 bg-red-500/10 p-3 rounded-lg flex items-center justify-between text-red-700 dark:text-red-300 font-mono text-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
            <span>Gagal memicu generator: {triggerError}</span>
          </div>
          <button
            type="button"
            onClick={() => setTriggerError(null)}
            className="p-1 rounded hover:bg-red-500/20"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Process View & Real-Time Progress Bar Card */}
      <div className="border border-border rounded-lg bg-card p-4 space-y-4 shadow-xs">
        {/* Header Row */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              {isJobActive ? (
                <Loader2 className="w-4 h-4 text-primary animate-spin flex-shrink-0" />
              ) : isJobFailed ? (
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
              ) : totalArtifactsCount >= 29 ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
              ) : (
                <Clock className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              )}
              <h4 className="text-xs font-bold uppercase tracking-wider font-mono text-foreground">
                Status Pemrosesan &amp; Generator Dokumen
              </h4>
              <span
                className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${statusBadgeClass}`}
              >
                {statusBadgeText}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">{stageDescription}</p>
          </div>

          <div className="text-right font-mono">
            <div className="text-lg font-bold tabular-nums text-foreground leading-none">
              {effectiveProgress}%
            </div>
            <div className="text-[11px] text-muted-foreground mt-1">
              {Math.min(totalArtifactsCount, 29)} / 29 Berkas • {readyRowsCount} / {DOC_REGISTRY.length} Dokumen
            </div>
          </div>
        </div>

        {/* Main Progress Bar */}
        <div className="space-y-1.5">
          <div
            className="h-2.5 w-full rounded-full bg-muted overflow-hidden border border-border/60"
            role="progressbar"
            aria-valuenow={effectiveProgress}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className={`h-full transition-all duration-300 ease-out rounded-full ${progressBarColor} ${
                isJobActive ? "animate-pulse" : ""
              }`}
              style={{ width: `${effectiveProgress}%` }}
            />
          </div>
          {currentJob && (
            <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-muted-foreground">
              <span>Job ID: {currentJob.id}</span>
              <span>
                Status Backend: {currentJob.status} ({currentJob.progress_percent}%)
                {currentJob.completed_at
                  ? ` • Selesai: ${new Date(currentJob.completed_at).toLocaleTimeString("id-ID")}`
                  : currentJob.started_at
                  ? ` • Mulai: ${new Date(currentJob.started_at).toLocaleTimeString("id-ID")}`
                  : ""}
              </span>
            </div>
          )}
        </div>

        {/* 5-Stage Pipeline Stepper */}
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
          {pipelineSteps.map((step) => {
            const StepIcon = step.icon;
            const isDone = step.status === "done";
            const isActive = step.status === "active";
            const isFailed = step.status === "failed";

            const cardBorder = isDone
              ? "border-emerald-500/40 bg-emerald-500/5"
              : isActive
              ? "border-primary/60 bg-primary/10 ring-1 ring-primary/20"
              : isFailed
              ? "border-red-500/50 bg-red-500/10"
              : "border-border bg-muted/25";

            const miniBarColor = isDone
              ? "bg-emerald-500"
              : isActive
              ? "bg-primary"
              : isFailed
              ? "bg-red-500"
              : "bg-muted-foreground/30";

            return (
              <div
                key={step.key}
                className={`rounded-md border p-2.5 flex flex-col justify-between gap-2 transition-colors ${cardBorder}`}
              >
                <div className="flex items-start justify-between gap-1.5">
                  <div className="min-w-0">
                    <div className="font-mono font-bold text-[11px] text-foreground truncate">
                      {step.title}
                    </div>
                    <div className="text-[10px] text-muted-foreground truncate">
                      {step.subtitle}
                    </div>
                  </div>
                  {isDone ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                  ) : isActive ? (
                    <Loader2 className="w-3.5 h-3.5 text-primary animate-spin flex-shrink-0 mt-0.5" />
                  ) : isFailed ? (
                    <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0 mt-0.5" />
                  ) : (
                    <StepIcon className="w-3.5 h-3.5 text-muted-foreground/60 flex-shrink-0 mt-0.5" />
                  )}
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[10px] font-mono">
                    <span
                      className={
                        isDone
                          ? "text-emerald-600 dark:text-emerald-300 font-semibold"
                          : isActive
                          ? "text-primary font-semibold"
                          : isFailed
                          ? "text-red-600 dark:text-red-300 font-semibold"
                          : "text-muted-foreground"
                      }
                    >
                      {step.countLabel}
                    </span>
                    <span className="text-muted-foreground tabular-nums">
                      {step.miniProgress}%
                    </span>
                  </div>
                  <div className="h-1 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 rounded-full ${miniBarColor}`}
                      style={{ width: `${step.miniProgress}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Job Failure Details & Retry */}
        {isJobFailed && (
          <div className="rounded-md border border-red-500/40 bg-red-500/10 p-3 flex flex-wrap items-center justify-between gap-3 text-red-700 dark:text-red-300 font-mono text-[11px]">
            <div className="flex items-start gap-2 min-w-0 flex-1">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <div className="space-y-0.5 min-w-0">
                <div className="font-bold">Pembuatan Dokumen Gagal</div>
                <div className="text-[10px] break-words">
                  {currentJob?.error_message || "Terjadi kesalahan internal saat menghasilkan dokumen."}
                </div>
              </div>
            </div>
            {canGenerateDocuments && (
              <button
                type="button"
                onClick={handleTriggerGeneration}
                disabled={isGenerating || isJobActive}
                className="px-2.5 py-1 rounded bg-red-600 hover:bg-red-500 text-white font-semibold text-[11px] transition flex items-center gap-1.5 flex-shrink-0"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Coba Lagi</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Google Drive Integration & Upload Progress Card */}
      {(() => {
        const drivePct = archiveRecord?.progress_percent ?? 0;
        const driveUploaded = archiveRecord?.uploaded_files ?? 0;
        const driveTotal = archiveRecord?.total_files || totalArtifactsCount;
        const driveStatus = archiveRecord?.status;
        const isDriveSynced = driveStatus === "SYNCED";
        const isDriveFailed = driveStatus === "FAILED";
        const isDriveSuperseded = driveStatus === "SUPERSEDED";

        const dStep1Done = isDriveSyncing ? drivePct >= 10 : isDriveSynced;
        const dStep1Active = isDriveSyncing && !dStep1Done;
        const dStep2Done = isDriveSyncing ? drivePct >= 20 : isDriveSynced;
        const dStep2Active = isDriveSyncing && dStep1Done && !dStep2Done;
        const dStep3Done = isDriveSyncing ? drivePct >= 98 : isDriveSynced;
        const dStep3Active = isDriveSyncing && dStep2Done && !dStep3Done;
        const dStep4Done = isDriveSynced;
        const dStep4Active = isDriveSyncing && dStep3Done && !dStep4Done;

        const driveSteps = [
          { key: "auth", label: "1. Autentikasi API", done: dStep1Done, active: dStep1Active, failed: isDriveFailed && drivePct < 10 },
          { key: "folders", label: "2. Folder Lv1–Lv4", done: dStep2Done, active: dStep2Active, failed: isDriveFailed && drivePct >= 10 && drivePct < 20 },
          { key: "upload", label: `3. Unggah & Timpa (${driveUploaded}/${driveTotal})`, done: dStep3Done, active: dStep3Active, failed: isDriveFailed && drivePct >= 20 && drivePct < 98 },
          { key: "done", label: "4. Selesai & Tautan Drive", done: dStep4Done, active: dStep4Active, failed: isDriveFailed && drivePct >= 98 },
        ];

        const uploadButtonLabel = isDriveSyncing
          ? `Mengunggah ke Drive (${drivePct}%)...`
          : isUploadingDrive
          ? "Memulai Unggah..."
          : isDriveSynced || revision.revision_number > 1
          ? `Timpa / Perbarui di Google Drive (Rev-${revision.revision_number})`
          : "Unggah Paket ke Google Drive";

        const isLiveDrive = driveHealth?.mode === "live";
        const canUploadBinary = !isLiveDrive || Boolean(driveHealth?.can_upload_binary);
        const oauthLoginUrl =
          typeof window !== "undefined"
            ? `${window.location.protocol}//${window.location.hostname}:8000/api/v1/archive/oauth/login`
            : "http://localhost:8000/api/v1/archive/oauth/login";

        return (
          <div className="border border-border rounded-lg bg-card p-4 space-y-4 shadow-xs">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1 min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  {isDriveSyncing ? (
                    <Loader2 className="w-4 h-4 text-sky-500 animate-spin flex-shrink-0" />
                  ) : isDriveSynced ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                  ) : isDriveFailed ? (
                    <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                  ) : !isApprovedForDrive ? (
                    <Lock className="w-4 h-4 text-amber-500 flex-shrink-0" />
                  ) : (
                    <Cloud className="w-4 h-4 text-sky-500 flex-shrink-0" />
                  )}
                  <h4 className="text-xs font-bold uppercase tracking-wider font-mono text-foreground">
                    Integrasi Penyimpanan Google Drive
                  </h4>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                      isDriveSyncing
                        ? "bg-sky-500/15 text-sky-600 dark:text-sky-300 border-sky-500/40"
                        : isDriveSynced
                        ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border-emerald-500/40"
                        : isDriveFailed
                        ? "bg-red-500/15 text-red-600 dark:text-red-300 border-red-500/40"
                        : isDriveSuperseded
                        ? "bg-amber-500/15 text-amber-600 dark:text-amber-300 border-amber-500/40"
                        : "bg-muted text-muted-foreground border-border"
                    }`}
                  >
                    {isDriveSyncing
                      ? "MENGUNGGAH KE DRIVE"
                      : isDriveSynced
                      ? "TERSIMPAN DI DRIVE"
                      : isDriveFailed
                      ? "GAGAL UNGGAH"
                      : isDriveSuperseded
                      ? "DIGANTIKAN REVISI BARU"
                      : isApprovedForDrive
                      ? "SIAP DIUNGGAH"
                      : "MENUNGGU APPROVAL"}
                  </span>
                  {driveHealth && (
                    <span
                      className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border ${
                        !isLiveDrive
                          ? "bg-muted text-muted-foreground border-border"
                          : canUploadBinary
                          ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30"
                          : "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30"
                      }`}
                    >
                      {!isLiveDrive
                        ? "Simulasi Lokal"
                        : driveHealth.oauth_connected
                        ? `OAuth 2.0: ${driveHealth.connected_email || "Terhubung"}`
                        : driveHealth.is_shared_drive
                        ? "Shared Drive"
                        : "Service Account (Kuota 0 B)"}
                    </span>
                  )}
                </div>

                {/* 5-Level Folder Structure Preview */}
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono text-muted-foreground pt-1">
                  <span className="px-1.5 py-0.5 rounded bg-muted border border-border text-foreground font-semibold">
                    Lv1: {schoolName}
                  </span>
                  <span>→</span>
                  <span className="px-1.5 py-0.5 rounded bg-muted border border-border text-foreground font-semibold">
                    Lv2: {fiscalYear}
                  </span>
                  <span>→</span>
                  <span className="px-1.5 py-0.5 rounded bg-muted border border-border text-foreground font-semibold">
                    Lv3: Triwulan {quarterNum}
                  </span>
                  <span>→</span>
                  <span className="px-1.5 py-0.5 rounded bg-muted border border-border text-foreground font-semibold">
                    Lv4: {drivePackageFolderName}
                  </span>
                  <span>→</span>
                  <span className="px-1.5 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-600 dark:text-sky-300 font-semibold">
                    Lv5: Berkas Paket SPJ
                  </span>
                </div>

                <p className="text-[11px] text-muted-foreground pt-0.5">
                  Dokumen hasil generate disimpan lokal terlebih dahulu. Jika terdapat revisi atau unggah ulang, berkas lama di folder <span className="font-mono text-foreground">{drivePackageFolderName}</span> akan ditimpa (overwrite) secara otomatis.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 flex-shrink-0">
                {isLiveDrive && driveHealth?.oauth_connected && canTriggerDriveUpload && (
                  <button
                    type="button"
                    onClick={handleDisconnectDriveOAuth}
                    disabled={isDisconnectingOAuth || isDriveSyncing}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded border border-border bg-muted/60 hover:bg-muted text-muted-foreground hover:text-foreground font-semibold text-xs transition disabled:opacity-50"
                    title="Putuskan sesi OAuth 2.0 Google Drive"
                  >
                    {isDisconnectingOAuth ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Unlink className="w-3.5 h-3.5" />
                    )}
                    <span>Putuskan OAuth</span>
                  </button>
                )}

                {isLiveDrive && !canUploadBinary && driveHealth?.oauth_client_configured && canTriggerDriveUpload && (
                  <a
                    href={oauthLoginUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-amber-500/40 bg-amber-500/15 hover:bg-amber-500/25 text-amber-700 dark:text-amber-300 font-semibold text-xs transition"
                  >
                    <Link2 className="w-3.5 h-3.5" />
                    <span>Hubungkan Akun Google (OAuth 2.0)</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}

                {isDriveSynced && archiveRecord?.drive_folder_url && (
                  <a
                    href={archiveRecord.drive_folder_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-emerald-500/40 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-700 dark:text-emerald-300 font-semibold text-xs transition"
                  >
                    <FolderOpen className="w-3.5 h-3.5" />
                    <span>Buka Folder Google Drive</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}

                {isApprovedForDrive && canTriggerDriveUpload && (
                  <button
                    type="button"
                    onClick={handleTriggerDriveUpload}
                    disabled={
                      isUploadingDrive ||
                      isDriveSyncing ||
                      isJobActive ||
                      totalArtifactsCount === 0 ||
                      !canUploadBinary
                    }
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    title={
                      !canUploadBinary
                        ? "Hubungkan akun Google OAuth 2.0 terlebih dahulu agar berkas tidak 0 byte"
                        : totalArtifactsCount === 0
                        ? "Klik 'Hasilkan Seluruh Dokumen (Generate)' terlebih dahulu sebelum mengunggah ke Drive"
                        : "Unggah seluruh berkas paket ke Google Drive"
                    }
                  >
                    {isUploadingDrive || isDriveSyncing ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CloudUpload className="w-3.5 h-3.5" />
                    )}
                    <span>{uploadButtonLabel}</span>
                  </button>
                )}
              </div>
            </div>

            {/* OAuth 2.0 / Storage Quota requirement notice */}
            {isLiveDrive && !canUploadBinary && (
              <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-2.5 flex items-start gap-2 text-amber-800 dark:text-amber-300 font-mono text-[11px]">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div>
                    <strong>Kuota Service Account = 0 Byte pada My Drive Pribadi:</strong>{" "}
                    Google melarang Service Account mengunggah isi berkas ke folder Google Drive pribadi (hasilnya akan gagal atau 0 byte).
                  </div>
                  {driveHealth?.oauth_client_configured ? (
                    <div>
                      Klik tombol <strong>Hubungkan Akun Google (OAuth 2.0)</strong> di kanan atas untuk login dengan akun pemilik folder Google Drive (<span className="underline">pastikan redirect URI terpasang</span>), lalu kembali ke tab ini.
                    </div>
                  ) : (
                    <div>
                      Simpan OAuth 2.0 Client ID JSON (tipe Web application, Redirect URI{" "}
                      <code>http://localhost:8000/api/v1/archive/oauth/callback</code>) ke{" "}
                      <code>backend/credentials/gdrive-oauth-client.json</code> agar tombol koneksi muncul otomatis.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Gate notices */}
            {!isApprovedForDrive && (
              <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-2.5 flex items-center gap-2 text-amber-700 dark:text-amber-300 font-mono text-[11px]">
                <Lock className="w-3.5 h-3.5 flex-shrink-0" />
                <span>
                  Terkunci: Paket pengadaan harus berstatus <strong>Disetujui (APPROVED)</strong> oleh Direktur Keuangan sebelum Admin / SysAdmin dapat mengunggah ke Google Drive.
                </span>
              </div>
            )}

            {isApprovedForDrive && !canTriggerDriveUpload && (
              <div className="rounded-md border border-border bg-muted/40 p-2.5 flex items-center gap-2 text-muted-foreground font-mono text-[11px]">
                <ShieldCheck className="w-3.5 h-3.5 flex-shrink-0" />
                <span>
                  Hanya peran <strong>Admin (ADMINISTRATION)</strong> atau <strong>SysAdmin (SYSTEM_ADMINISTRATOR)</strong> yang dapat memicu unggah ke Google Drive.
                </span>
              </div>
            )}

            {isApprovedForDrive && canTriggerDriveUpload && totalArtifactsCount === 0 && (
              <div className="rounded-md border border-border bg-muted/30 p-2.5 flex items-center gap-2 text-muted-foreground font-mono text-[11px]">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>
                  Klik <strong>Hasilkan Seluruh Dokumen (Generate)</strong> di atas terlebih dahulu agar berkas lokal tersedia untuk diunggah ke Google Drive.
                </span>
              </div>
            )}

            {(driveUploadError || (isDriveFailed && archiveRecord?.last_error)) && (
              <div className="rounded-md border border-red-500/40 bg-red-500/10 p-2.5 flex items-start justify-between gap-2 text-red-700 dark:text-red-300 font-mono text-[11px]">
                <div className="flex items-start gap-2 min-w-0">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                  <span className="break-words">
                    {driveUploadError || archiveRecord?.last_error}
                  </span>
                </div>
                {driveUploadError && (
                  <button
                    type="button"
                    onClick={() => setDriveUploadError(null)}
                    className="p-0.5 rounded hover:bg-red-500/20"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            )}

            {/* Progress Report Section (shown once upload started or synced/failed) */}
            {archiveRecord && (archiveRecord.status !== "PENDING" || archiveRecord.attempt_count > 0) && (
              <div className="space-y-3 pt-1 border-t border-border/70">
                <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-[11px]">
                  <span className="text-muted-foreground truncate">
                    {archiveRecord.current_step || "Menunggu proses unggah..."}
                  </span>
                  <span className="font-bold text-foreground tabular-nums">
                    {drivePct}% • {driveUploaded} / {driveTotal} Berkas
                  </span>
                </div>

                <div
                  className="h-2 w-full rounded-full bg-muted overflow-hidden border border-border/60"
                  role="progressbar"
                  aria-valuenow={drivePct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className={`h-full transition-all duration-300 ease-out rounded-full ${
                      isDriveSynced
                        ? "bg-emerald-500"
                        : isDriveFailed
                        ? "bg-red-500"
                        : "bg-sky-500 animate-pulse"
                    }`}
                    style={{ width: `${drivePct}%` }}
                  />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {driveSteps.map((st) => (
                    <div
                      key={st.key}
                      className={`rounded border px-2.5 py-1.5 font-mono text-[10px] flex items-center justify-between gap-1.5 ${
                        st.done
                          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                          : st.active
                          ? "border-sky-500/50 bg-sky-500/10 text-sky-700 dark:text-sky-300 font-semibold"
                          : st.failed
                          ? "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300"
                          : "border-border bg-muted/20 text-muted-foreground"
                      }`}
                    >
                      <span className="truncate">{st.label}</span>
                      {st.done ? (
                        <CheckCircle2 className="w-3 h-3 flex-shrink-0" />
                      ) : st.active ? (
                        <Loader2 className="w-3 h-3 animate-spin flex-shrink-0" />
                      ) : st.failed ? (
                        <AlertCircle className="w-3 h-3 flex-shrink-0" />
                      ) : (
                        <Clock className="w-3 h-3 flex-shrink-0 opacity-50" />
                      )}
                    </div>
                  ))}
                </div>

                {archiveRecord.synced_at && (
                  <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-muted-foreground">
                    <span>Path Drive: {archiveRecord.folder_path}</span>
                    <span>
                      Terakhir Disinkronkan:{" "}
                      {new Date(archiveRecord.synced_at).toLocaleString("id-ID")}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })()}

      {/* 13-Document Registry Table */}
      <div className="border border-border rounded-lg bg-card overflow-hidden">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-muted/90 border-b border-border text-[11px] uppercase font-mono font-bold tracking-wider text-foreground">
              <th className="px-3 py-2.5 w-24">Kode</th>
              <th className="px-3 py-2.5 min-w-[240px]">Nama Dokumen Resmi</th>
              <th className="px-3 py-2.5 w-28">Tahap Harga</th>
              <th className="px-3 py-2.5 w-36">Status Berkas</th>
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

              const isSingleFormatRow =
                doc.code === "XLSX" || doc.code === "MERGED_PDF" || doc.code === "ZIP";

              const renderStatusBadge = () => {
                if (!isSingleFormatRow) {
                  if (docxArt && pdfArt) {
                    return (
                      <span className="text-emerald-600 dark:text-emerald-300 font-bold text-[10px] inline-flex items-center gap-1">
                        ● Tersedia
                      </span>
                    );
                  }
                  if (docxArt && !pdfArt && isJobActive) {
                    return (
                      <span className="text-sky-600 dark:text-sky-300 font-semibold text-[10px] inline-flex items-center gap-1">
                        <Loader2 className="w-3 h-3 animate-spin" /> Konversi PDF...
                      </span>
                    );
                  }
                  if ((docxArt || pdfArt) && !isJobActive) {
                    return (
                      <span className="text-amber-600 dark:text-amber-300 font-bold text-[10px] inline-flex items-center gap-1">
                        ◐ Sebagian ({docxArt ? "DOCX" : "PDF"})
                      </span>
                    );
                  }
                  if (isJobActive) {
                    if (jobPct >= 12 && jobPct < 50) {
                      return (
                        <span className="text-primary font-semibold text-[10px] inline-flex items-center gap-1">
                          <Loader2 className="w-3 h-3 animate-spin" /> Merender DOCX...
                        </span>
                      );
                    }
                    return (
                      <span className="text-muted-foreground text-[10px] inline-flex items-center gap-1">
                        ⏳ Dalam Antrean
                      </span>
                    );
                  }
                  if (isJobFailed) {
                    return (
                      <span className="text-red-600 dark:text-red-300 font-bold text-[10px] inline-flex items-center gap-1">
                        ✕ Gagal
                      </span>
                    );
                  }
                  return <span className="text-muted-foreground text-[10px]">○ Belum Dibuat</span>;
                }

                const hasSingleArtifact =
                  (doc.code === "XLSX" && Boolean(xlsxArt)) ||
                  (doc.code === "MERGED_PDF" && Boolean(pdfArt)) ||
                  (doc.code === "ZIP" && Boolean(zipArt));

                if (hasSingleArtifact) {
                  return (
                    <span className="text-emerald-600 dark:text-emerald-300 font-bold text-[10px] inline-flex items-center gap-1">
                      ● Tersedia
                    </span>
                  );
                }
                if (isJobActive) {
                  const isRowStageActive =
                    (doc.code === "XLSX" && jobPct >= 12 && jobPct < 25) ||
                    (doc.code === "MERGED_PDF" && jobPct >= 50 && jobPct < 90) ||
                    (doc.code === "ZIP" && jobPct >= 90);

                  if (isRowStageActive) {
                    return (
                      <span className="text-primary font-semibold text-[10px] inline-flex items-center gap-1">
                        <Loader2 className="w-3 h-3 animate-spin" /> Sedang Diproses...
                      </span>
                    );
                  }
                  return (
                    <span className="text-muted-foreground text-[10px] inline-flex items-center gap-1">
                      ⏳ Dalam Antrean
                    </span>
                  );
                }
                if (isJobFailed) {
                  return (
                    <span className="text-red-600 dark:text-red-300 font-bold text-[10px] inline-flex items-center gap-1">
                      ✕ Gagal
                    </span>
                  );
                }
                return <span className="text-muted-foreground text-[10px]">○ Belum Dibuat</span>;
              };

              return (
                <tr key={doc.code} className="hover:bg-muted/30 transition-colors">
                  <td className="px-3 py-2 font-bold text-foreground">{doc.code}</td>
                  <td className="px-3 py-2 font-sans font-medium text-foreground">
                    {doc.name}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground text-[10px]">{doc.stage}</td>
                  <td className="px-3 py-2">{renderStatusBadge()}</td>
                  <td className="px-3 py-2 text-center">
                    <div className="flex items-center justify-center gap-1.5">
                      {docxArt && (
                        <a
                          href={`/api/v1/artifacts/${docxArt.id}/download`}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2 py-0.5 rounded bg-blue-500/15 hover:bg-blue-500/25 text-blue-600 dark:text-blue-300 border border-blue-500/30 text-[10px] font-bold transition"
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
                          className="px-2 py-0.5 rounded bg-red-500/15 hover:bg-red-500/25 text-red-600 dark:text-red-300 border border-red-500/30 text-[10px] font-bold transition"
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
                          className="px-2 py-0.5 rounded bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30 text-[10px] font-bold transition"
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
                          className="px-2 py-0.5 rounded bg-purple-500/15 hover:bg-purple-500/25 text-purple-600 dark:text-purple-300 border border-purple-500/30 text-[10px] font-bold transition"
                          title="Unduh ZIP Manifest"
                        >
                          ZIP
                        </a>
                      )}
                      {(() => {
                        const driveUrl =
                          pdfArt?.drive_web_view_link ||
                          docxArt?.drive_web_view_link ||
                          xlsxArt?.drive_web_view_link ||
                          zipArt?.drive_web_view_link;
                        if (!driveUrl) return null;
                        return (
                          <a
                            href={driveUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-sky-500/15 hover:bg-sky-500/25 text-sky-600 dark:text-sky-300 border border-sky-500/30 text-[10px] font-bold transition"
                            title="Buka berkas di Google Drive"
                          >
                            <span>Drive</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        );
                      })()}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-center">
                    {pdfArt && (
                      <button
                        type="button"
                        onClick={() => handleOpenPdfInViewer(doc.code)}
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] transition ${
                          activePdfEntry?.doc.code === doc.code
                            ? "bg-primary/15 text-primary border border-primary/40 font-semibold"
                            : "hover:bg-muted text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        <Eye className="w-3 h-3" />
                        <span>{activePdfEntry?.doc.code === doc.code ? "Aktif" : "Lihat"}</span>
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Integrated PDF Viewer Panel */}
      <div
        ref={pdfViewerRef}
        className="border border-border rounded-lg bg-card overflow-hidden shadow-xs"
      >
        <div className="px-4 py-2.5 border-b border-border bg-muted/40 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="w-4 h-4 text-red-500 flex-shrink-0" />
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider font-mono text-foreground">
                  PDF Viewer Dokumen SPJ
                </span>
                {isDraft && (
                  <span className="text-[10px] text-amber-600 dark:text-amber-300 px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/40 font-mono font-bold">
                    DRAFT WATERMARK
                  </span>
                )}
              </div>
              {activePdfEntry && (
                <div className="text-[11px] text-muted-foreground font-mono truncate">
                  {activePdfEntry.doc.code === "MERGED_PDF"
                    ? "Bundel Lengkap"
                    : activePdfEntry.doc.code}{" "}
                  • {activePdfEntry.doc.name} ({activePdfEntry.artifact.filename})
                </div>
              )}
            </div>
          </div>

          {activePdfEntry && (
            <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
              <button
                type="button"
                onClick={() => handleStepPdf(-1)}
                disabled={availablePdfDocs.length <= 1}
                className="p-1.5 rounded border border-border bg-background hover:bg-muted text-foreground disabled:opacity-40 transition"
                title="Dokumen PDF sebelumnya"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>

              <select
                value={activePdfEntry.doc.code}
                onChange={(e) => setSelectedPdfCode(e.target.value)}
                className="px-2 py-1 rounded border border-border bg-background text-foreground text-[11px] max-w-[230px]"
                aria-label="Pilih dokumen PDF"
              >
                {availablePdfDocs.map(({ doc }) => (
                  <option key={doc.code} value={doc.code}>
                    {doc.code === "MERGED_PDF" ? "GABUNGAN" : doc.code} — {doc.name}
                  </option>
                ))}
              </select>

              <button
                type="button"
                onClick={() => handleStepPdf(1)}
                disabled={availablePdfDocs.length <= 1}
                className="p-1.5 rounded border border-border bg-background hover:bg-muted text-foreground disabled:opacity-40 transition"
                title="Dokumen PDF berikutnya"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>

              <a
                href={`/api/v1/artifacts/${activePdfEntry.artifact.id}/download?inline=true`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-border bg-background hover:bg-muted text-foreground transition"
                title="Buka PDF di tab baru"
              >
                <ExternalLink className="w-3 h-3" />
                <span>Tab Baru</span>
              </a>

              <a
                href={`/api/v1/artifacts/${activePdfEntry.artifact.id}/download`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-border bg-background hover:bg-muted text-foreground transition"
                title="Unduh berkas PDF"
              >
                <Download className="w-3 h-3" />
                <span>Unduh</span>
              </a>

              <button
                type="button"
                onClick={() => setIsPdfFullscreen(true)}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-primary text-primary-foreground font-semibold hover:opacity-90 transition"
                title="Perbesar PDF Viewer"
              >
                <Maximize2 className="w-3 h-3" />
                <span>Layar Penuh</span>
              </button>
            </div>
          )}
        </div>

        {/* Quick-switch Document Pills */}
        {availablePdfDocs.length > 0 && (
          <div className="px-4 py-2 border-b border-border bg-muted/20 flex items-center gap-1.5 overflow-x-auto font-mono text-[10px]">
            {availablePdfDocs.map(({ doc }) => {
              const isSelected = activePdfEntry?.doc.code === doc.code;
              return (
                <button
                  key={doc.code}
                  type="button"
                  onClick={() => setSelectedPdfCode(doc.code)}
                  className={`px-2 py-1 rounded border whitespace-nowrap transition ${
                    isSelected
                      ? "bg-primary text-primary-foreground border-primary font-bold"
                      : "bg-background text-muted-foreground border-border hover:text-foreground hover:bg-muted"
                  }`}
                >
                  {doc.code === "MERGED_PDF" ? "00_GABUNGAN" : doc.code}
                </button>
              );
            })}
          </div>
        )}

        {/* PDF Canvas */}
        {activePdfEntry ? (
          <div className="bg-zinc-900 relative">
            <iframe
              key={activePdfEntry.artifact.id}
              src={`/api/v1/artifacts/${activePdfEntry.artifact.id}/download?inline=true#view=FitH`}
              title={activePdfEntry.artifact.filename}
              className="w-full h-[680px] border-0"
            />
          </div>
        ) : (
          <div className="p-10 text-center text-muted-foreground space-y-2 bg-muted/10">
            <FileText className="w-8 h-8 mx-auto text-muted-foreground/50" />
            <div className="font-mono font-semibold text-foreground text-xs">
              Belum Ada Berkas PDF Tersedia
            </div>
            <p className="text-[11px] max-w-md mx-auto">
              Klik <span className="font-semibold text-foreground">Hasilkan Seluruh Dokumen (Generate)</span> di atas untuk membuat dokumen Word &amp; PDF agar dapat langsung dilihat di PDF Viewer ini.
            </p>
          </div>
        )}
      </div>

      {/* Fullscreen PDF Modal Viewer */}
      {isPdfFullscreen && activePdfEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4">
          <div className="bg-card border border-border w-full max-w-6xl h-[90vh] rounded-lg shadow-2xl flex flex-col overflow-hidden">
            <div className="px-4 py-2.5 border-b border-border flex flex-wrap items-center justify-between gap-2 bg-muted/40 font-mono text-xs">
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="w-4 h-4 text-red-400 flex-shrink-0" />
                <span className="font-semibold text-foreground truncate">
                  {activePdfEntry.doc.code === "MERGED_PDF"
                    ? "Bundel Lengkap"
                    : activePdfEntry.doc.code}{" "}
                  — {activePdfEntry.doc.name}
                </span>
                {isDraft && (
                  <span className="text-[10px] text-amber-600 dark:text-amber-300 px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/40 font-bold">
                    DRAFT WATERMARK
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => handleStepPdf(-1)}
                  disabled={availablePdfDocs.length <= 1}
                  className="p-1.5 rounded border border-border bg-background hover:bg-muted text-foreground disabled:opacity-40"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <select
                  value={activePdfEntry.doc.code}
                  onChange={(e) => setSelectedPdfCode(e.target.value)}
                  className="px-2 py-1 rounded border border-border bg-background text-foreground text-[11px] max-w-[240px]"
                >
                  {availablePdfDocs.map(({ doc }) => (
                    <option key={doc.code} value={doc.code}>
                      {doc.code === "MERGED_PDF" ? "GABUNGAN" : doc.code} — {doc.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => handleStepPdf(1)}
                  disabled={availablePdfDocs.length <= 1}
                  className="p-1.5 rounded border border-border bg-background hover:bg-muted text-foreground disabled:opacity-40"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
                <a
                  href={`/api/v1/artifacts/${activePdfEntry.artifact.id}/download?inline=true`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-border bg-background hover:bg-muted text-foreground text-[11px]"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span>Tab Baru</span>
                </a>
                <button
                  type="button"
                  onClick={() => setIsPdfFullscreen(false)}
                  className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
                  title="Tutup Layar Penuh"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="flex-1 bg-zinc-900 relative">
              <iframe
                key={`fs-${activePdfEntry.artifact.id}`}
                src={`/api/v1/artifacts/${activePdfEntry.artifact.id}/download?inline=true#view=FitH`}
                title={activePdfEntry.artifact.filename}
                className="w-full h-full border-0"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
