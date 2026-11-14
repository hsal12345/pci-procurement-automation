"use client";

import { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  FileText,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { ImportProgressState } from "@/types/imports";

interface ImportAIProgressPanelProps {
  progress: ImportProgressState;
  filename?: string;
  compactAfterComplete?: boolean;
}

const STAGES: Array<{
  id: string;
  title: string;
  shortLabel: string;
}> = [
  { id: "UPLOAD", title: "Unggah Berkas", shortLabel: "Unggah" },
  { id: "EXTRACT_VALIDATE", title: "Ekstraksi Tabel & Konteks (Kode)", shortLabel: "Ekstraksi" },
  { id: "PREPARE_CONTEXT", title: "Sanitasi PII & Pengemasan Konteks", shortLabel: "Konteks" },
  { id: "LLM_INFERENCE", title: "Pemetaan Kolom oleh LLM", shortLabel: "Pemetaan LLM" },
  { id: "FINALIZE", title: "Validasi Skema & Heuristik Akhir", shortLabel: "Finalisasi" },
];

export function ImportAIProgressPanel({
  progress,
  filename,
  compactAfterComplete = true,
}: ImportAIProgressPanelProps) {
  const [liveElapsedMs, setLiveElapsedMs] = useState<number>(progress.elapsed_ms || 0);
  const elapsedRef = useRef<number>(progress.elapsed_ms || 0);
  const [showLog, setShowLog] = useState<boolean>(true);
  const isTerminal = ["COMPLETED", "AMBIGUOUS", "FALLBACK", "FAILED"].includes(progress.status);

  useEffect(() => {
    elapsedRef.current = progress.elapsed_ms || 0;
    setLiveElapsedMs(progress.elapsed_ms || 0);
  }, [progress.elapsed_ms]);

  useEffect(() => {
    if (progress.status !== "RUNNING") return;
    const startedAt = Date.now() - elapsedRef.current;
    const id = setInterval(() => {
      setLiveElapsedMs(Math.max(0, Date.now() - startedAt));
    }, 200);
    return () => clearInterval(id);
  }, [progress.status, progress.stage]);

  useEffect(() => {
    if (compactAfterComplete && isTerminal) {
      setShowLog(false);
    }
  }, [compactAfterComplete, isTerminal]);

  const activeIdx = STAGES.findIndex((s) => s.id === progress.stage);
  const currentStageNum = activeIdx >= 0 ? activeIdx : 0;
  const elapsedSec = (liveElapsedMs / 1000).toFixed(1);
  const stats = progress.extracted_stats || {};

  const statusTone =
    progress.status === "COMPLETED"
      ? "border-emerald-500/40 bg-emerald-500/5"
      : progress.status === "AMBIGUOUS"
      ? "border-amber-500/40 bg-amber-500/5"
      : progress.status === "FALLBACK" || progress.status === "FAILED"
      ? "border-orange-500/40 bg-orange-500/5"
      : "border-primary/40 bg-primary/5";

  return (
    <div className={`rounded-lg border p-3.5 space-y-3 transition-colors ${statusTone}`}>
      {/* Header Row: Stage, Format, Model & Elapsed */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {progress.status === "RUNNING" ? (
            <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
          ) : progress.status === "COMPLETED" ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          )}
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold text-foreground">
                {progress.status === "RUNNING"
                  ? `Tahap ${currentStageNum + 1}/${STAGES.length}: ${progress.label}`
                  : progress.label}
              </span>
              {progress.source_format && (
                <span className="px-1.5 py-0.5 rounded bg-muted text-foreground font-mono text-[10px] border border-border">
                  {progress.source_format}
                </span>
              )}
              {progress.model && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-primary/15 text-primary font-mono text-[10px] border border-primary/30">
                  <Cpu className="w-3 h-3" />
                  <span>
                    {progress.provider || "ai"} / {progress.model}
                  </span>
                </span>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">{progress.detail}</p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 text-[11px] font-mono">
          <span className="text-muted-foreground">{elapsedSec}s</span>
          <span className="px-2 py-0.5 rounded bg-background border border-border font-semibold text-foreground tabular-nums">
            {progress.percent}%
          </span>
          <button
            type="button"
            onClick={() => setShowLog((v) => !v)}
            className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition"
            title={showLog ? "Ciutkan detail progres" : "Tampilkan detail progres"}
          >
            {showLog ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Deterministic Progress Bar */}
      <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            progress.status === "COMPLETED"
              ? "bg-emerald-500"
              : progress.status === "AMBIGUOUS"
              ? "bg-amber-500"
              : progress.status === "FALLBACK" || progress.status === "FAILED"
              ? "bg-orange-500"
              : "bg-primary"
          }`}
          style={{ width: `${Math.max(4, Math.min(100, progress.percent || 0))}%` }}
        />
      </div>

      {/* 5-Stage Stepper Pills */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5">
        {STAGES.map((st, idx) => {
          const isDone =
            (isTerminal && progress.percent >= 100 && idx <= currentStageNum) ||
            idx < currentStageNum ||
            (isTerminal && progress.status !== "FAILED" && idx < STAGES.length);
          const isActive = progress.status === "RUNNING" && idx === currentStageNum;
          return (
            <div
              key={st.id}
              className={`px-2 py-1.5 rounded border text-[10px] font-mono flex items-center gap-1.5 transition ${
                isActive
                  ? "border-primary bg-primary/15 text-primary font-semibold"
                  : isDone
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : "border-border/70 bg-background/50 text-muted-foreground"
              }`}
            >
              {isActive ? (
                <Loader2 className="w-3 h-3 animate-spin shrink-0" />
              ) : isDone ? (
                <CheckCircle2 className="w-3 h-3 shrink-0" />
              ) : (
                <span className="w-3 h-3 rounded-full border border-current inline-flex items-center justify-center text-[8px] shrink-0">
                  {idx + 1}
                </span>
              )}
              <span className="truncate">{st.shortLabel}</span>
            </div>
          );
        })}
      </div>

      {/* Collapsible Context & Activity Log Details */}
      {showLog && (
        <div className="space-y-2 pt-1 border-t border-border/60">
          {/* Pre-LLM Code Extraction Telemetry Badges */}
          {(filename || Object.keys(stats).length > 0) && (
            <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
              {filename && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-background border border-border text-muted-foreground">
                  <FileText className="w-3 h-3 text-primary" />
                  <span className="truncate max-w-[200px]">{filename}</span>
                </span>
              )}
              {typeof stats.pages_count === "number" && (
                <span className="px-2 py-0.5 rounded bg-background border border-border text-foreground">
                  {stats.pages_count} Halaman PDF
                </span>
              )}
              {typeof stats.sections_count === "number" && (
                <span className="px-2 py-0.5 rounded bg-background border border-border text-foreground">
                  {stats.sections_count} Tabel/Bagian
                </span>
              )}
              {typeof stats.candidate_lines_count === "number" && (
                <span className="px-2 py-0.5 rounded bg-background border border-border text-foreground">
                  {stats.candidate_lines_count} Baris Awal
                </span>
              )}
              {typeof stats.context_snippets_count === "number" && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-background border border-border text-emerald-300">
                  <ShieldCheck className="w-3 h-3" />
                  <span>{stats.context_snippets_count} Konteks Tersanitasi</span>
                </span>
              )}
            </div>
          )}

          {/* Live Event Feed */}
          {progress.events && progress.events.length > 0 && (
            <div className="bg-background/80 border border-border rounded p-2 max-h-32 overflow-y-auto space-y-1 font-mono text-[10px]">
              <div className="flex items-center gap-1 text-muted-foreground uppercase text-[9px] mb-1">
                <Activity className="w-3 h-3 text-primary" />
                <span>Log Progres Ekstraksi &amp; AI</span>
              </div>
              {progress.events.map((ev, idx) => (
                <div key={`${ev.timestamp}-${idx}`} className="flex items-start gap-2 text-muted-foreground">
                  <span className="text-[9px] text-primary/80 shrink-0 tabular-nums">
                    +{(ev.elapsed_ms / 1000).toFixed(1)}s
                  </span>
                  <span className="text-foreground/90 leading-snug">{ev.detail}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
