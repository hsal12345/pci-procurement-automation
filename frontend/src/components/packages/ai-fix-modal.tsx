"use client";

import { useState, useEffect } from "react";
import { PackageRevision } from "@/types/package";
import {
  AIFixApplyResponse,
  AIFixChangeItem,
  AIFixRecommendationResponse,
} from "@/types/ai";
import { apiClient } from "@/lib/api-client";
import {
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Loader2,
  Sparkles,
  Trash2,
  Wand2,
  X,
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  Check,
  ShieldCheck,
  Bot,
} from "lucide-react";

interface AIFixModalProps {
  isOpen: boolean;
  revision: PackageRevision;
  blockCount: number;
  warningCount: number;
  aiFindingsCount: number;
  onClose: () => void;
  onApplied: (result: AIFixApplyResponse) => Promise<void>;
  onScrapped: () => void;
}

type ModalPhase = "confirm" | "reasoning" | "review";

const LIVE_REASONING_STAGES = [
  {
    title: "Pemindaian Temuan Validasi & Anomali Teks",
    detail: "Mengumpulkan seluruh pelanggaran aturan bisnis (BR01–BR15) dan inkonsistensi semantik.",
  },
  {
    title: "Audit Identitas, Pejabat Penandatangan & Pajak",
    detail: "Mengecek kelengkapan snapshot sekolah, penyedia, pejabat wajib (BR09), dan tarif pajak (BR06).",
  },
  {
    title: "Rekonstruksi Kronologi Tanggal & Penomoran 13 Dokumen",
    detail: "Menyelaraskan urutan hari kerja D01–D13 (BR07/BR12) serta keunikan nomor dokumen (BR02/BR08).",
  },
  {
    title: "Rekonsiliasi Teks Barang, Harga & Aritmatika Total",
    detail: "Menyelaraskan deskripsi item lintas dokumen (BR11) serta menghitung ulang total & terbilang (BR05).",
  },
];

const TAB_LABELS: Record<string, string> = {
  identity: "1. Identitas",
  items: "2. Barang & Harga",
  dates: "3. Tanggal & Nomor",
  logistics: "4. Pengiriman",
};

export function AIFixModal({
  isOpen,
  revision,
  blockCount,
  warningCount,
  aiFindingsCount,
  onClose,
  onApplied,
  onScrapped,
}: AIFixModalProps) {
  const [phase, setPhase] = useState<ModalPhase>("confirm");
  const [liveStageIdx, setLiveStageIdx] = useState(0);
  const [recommendation, setRecommendation] = useState<AIFixRecommendationResponse | null>(null);
  const [selectedIds, setSelectedIds] = useState<Record<string, boolean>>({});
  const [showReasoningInReview, setShowReasoningInReview] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isApplying, setIsApplying] = useState(false);

  // Reset modal state whenever opened
  useEffect(() => {
    if (isOpen) {
      setPhase("confirm");
      setLiveStageIdx(0);
      setRecommendation(null);
      setSelectedIds({});
      setShowReasoningInReview(true);
      setErrorMsg(null);
      setIsApplying(false);
    }
  }, [isOpen]);

  // Animate reasoning stages while AI works
  useEffect(() => {
    if (!isOpen || phase !== "reasoning") return;
    const timer = setInterval(() => {
      setLiveStageIdx((prev) =>
        prev < LIVE_REASONING_STAGES.length - 1 ? prev + 1 : prev
      );
    }, 650);
    return () => clearInterval(timer);
  }, [isOpen, phase]);

  if (!isOpen) return null;

  const handleStartAIWork = async () => {
    setPhase("reasoning");
    setLiveStageIdx(0);
    setErrorMsg(null);
    try {
      const resp = await apiClient.getAIFixRecommendations(revision.id);
      if (resp.status === "FAILED" || resp.status === "DISABLED" || resp.status === "BUDGET_EXCEEDED") {
        setErrorMsg(resp.summary || "Layanan AI Auto-Fix tidak tersedia saat ini.");
        return;
      }

      // Briefly show completed reasoning state so the user clearly sees the steps finish
      setLiveStageIdx(LIVE_REASONING_STAGES.length);
      setRecommendation(resp);

      const initSelected: Record<string, boolean> = {};
      for (const ch of resp.changes || []) {
        initSelected[ch.fix_id] = true;
      }
      setSelectedIds(initSelected);

      setTimeout(() => {
        setPhase("review");
      }, 450);
    } catch (err: any) {
      setErrorMsg(err?.message || String(err) || "Gagal menjalankan AI Fix Recommendation.");
    }
  };

  const changes: AIFixChangeItem[] = recommendation?.changes || [];
  const selectedChanges = changes.filter((c) => selectedIds[c.fix_id]);
  const allSelected = changes.length > 0 && selectedChanges.length === changes.length;

  const toggleAll = () => {
    const nextState: Record<string, boolean> = {};
    for (const c of changes) {
      nextState[c.fix_id] = !allSelected;
    }
    setSelectedIds(nextState);
  };

  const toggleItem = (fixId: string) => {
    setSelectedIds((prev) => ({ ...prev, [fixId]: !prev[fixId] }));
  };

  const handleScrap = () => {
    onScrapped();
    onClose();
  };

  const handleApply = async () => {
    if (selectedChanges.length === 0) return;
    setIsApplying(true);
    setErrorMsg(null);
    try {
      const result = await apiClient.applyAIFixes(
        revision.id,
        revision.version,
        selectedChanges
      );
      await onApplied(result);
      onClose();
    } catch (err: any) {
      setErrorMsg(err?.message || String(err) || "Gagal menerapkan perubahan AI.");
    } finally {
      setIsApplying(false);
    }
  };

  const currentStepNumber = phase === "confirm" ? 1 : phase === "reasoning" ? 2 : 3;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
      <div className="bg-card border border-border w-full max-w-4xl max-h-[90vh] rounded-xl shadow-2xl overflow-hidden flex flex-col font-sans">
        {/* Modal Header */}
        <div className="px-5 py-3.5 border-b border-border bg-gradient-to-r from-violet-500/15 via-primary/10 to-amber-500/10 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-violet-500/20 border border-violet-500/40 flex items-center justify-center">
              <Wand2 className="w-4 h-4 text-violet-300" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
                AI Fix Recommendation — Perbaikan Otomatis Cerdas
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Revisi #{revision.revision_number} • Analisis menyeluruh BR01–BR15 &amp; Semantik AI
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={phase === "reasoning" && !errorMsg ? undefined : onClose}
            disabled={phase === "reasoning" && !errorMsg}
            className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60 transition disabled:opacity-40"
            title="Tutup"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 4-Step Progress Strip */}
        <div className="px-5 py-2.5 bg-muted/40 border-b border-border grid grid-cols-4 gap-2 text-[10px] font-mono">
          {[
            { num: 1, label: "1. Konfirmasi" },
            { num: 2, label: "2. Penalaran AI" },
            { num: 3, label: "3. Tinjau Perubahan" },
            { num: 4, label: "4. Buang / Terapkan" },
          ].map((s) => {
            const isActive = currentStepNumber === s.num || (phase === "review" && s.num === 4);
            const isDone = currentStepNumber > s.num;
            return (
              <div
                key={s.num}
                className={`px-2.5 py-1.5 rounded border flex items-center gap-1.5 transition ${
                  isDone
                    ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300 font-semibold"
                    : isActive
                    ? "bg-violet-500/15 border-violet-500/40 text-violet-200 font-bold"
                    : "bg-card/50 border-border text-muted-foreground"
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                ) : (
                  <span className="w-3.5 h-3.5 rounded-full bg-current/15 flex items-center justify-center text-[9px] shrink-0">
                    {s.num}
                  </span>
                )}
                <span className="truncate">{s.label}</span>
              </div>
            );
          })}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
          {/* PHASE 1: CONFIRMATION */}
          {phase === "confirm" && (
            <div className="space-y-4">
              <div className="p-4 rounded-lg border border-violet-500/30 bg-violet-500/10 space-y-2">
                <div className="flex items-center gap-2 text-violet-200 font-semibold font-mono text-xs">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  <span>Konfirmasi Memulai AI Fix Recommendation</span>
                </div>
                <p className="text-muted-foreground leading-relaxed">
                  Kecerdasan buatan akan memindai seluruh data paket pengadaan (Identitas, Pejabat, Pajak,
                  Barang &amp; Harga, Kronologi Tanggal, serta Nomor 13 Dokumen) untuk merumuskan perbaikan otomatis.
                </p>
                <p className="text-[11px] text-emerald-300/90 font-medium">
                  Catatan Aman: Data paket Anda belum akan diubah pada tahap ini. Anda akan meninjau
                  seluruh nilai usulan terlebih dahulu dan bebas memilih untuk menerapkan atau membuang (scrap) rekomendasi.
                </p>
              </div>

              {/* Current Diagnostic Summary */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-lg border border-red-500/30 bg-red-500/10">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase text-red-300 font-bold">
                    <AlertOctagon className="w-3.5 h-3.5" />
                    <span>Blokir (BLOCK)</span>
                  </div>
                  <div className="text-xl font-mono font-bold text-red-200 mt-1">{blockCount}</div>
                </div>
                <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/10">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase text-amber-300 font-bold">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Peringatan</span>
                  </div>
                  <div className="text-xl font-mono font-bold text-amber-200 mt-1">{warningCount}</div>
                </div>
                <div className="p-3 rounded-lg border border-sky-500/30 bg-sky-500/10">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase text-sky-300 font-bold">
                    <Bot className="w-3.5 h-3.5" />
                    <span>Anomali Semantik</span>
                  </div>
                  <div className="text-xl font-mono font-bold text-sky-200 mt-1">{aiFindingsCount}</div>
                </div>
              </div>
            </div>
          )}

          {/* PHASE 2: REASONING STEPS & AI WORKS */}
          {phase === "reasoning" && (
            <div className="space-y-4 py-2">
              <div className="flex items-center gap-3 p-3.5 rounded-lg border border-violet-500/30 bg-violet-500/10">
                {errorMsg ? (
                  <AlertOctagon className="w-5 h-5 text-red-400 shrink-0" />
                ) : (
                  <Loader2 className="w-5 h-5 text-violet-300 animate-spin shrink-0" />
                )}
                <div>
                  <h4 className="font-mono font-bold text-foreground text-xs">
                    {errorMsg
                      ? "Analisis AI Terhenti"
                      : "AI Sedang Melakukan Penalaran & Menyusun Rekomendasi Perbaikan..."}
                  </h4>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {errorMsg || "Menjalankan pemeriksaan lintas dokumen, kronologi tanggal, kalkulasi pajak, dan rekonsiliasi teks."}
                  </p>
                </div>
              </div>

              <div className="space-y-2.5">
                {LIVE_REASONING_STAGES.map((stage, idx) => {
                  const isDone = !errorMsg && (liveStageIdx > idx || recommendation !== null);
                  const isCurrent = !errorMsg && liveStageIdx === idx && recommendation === null;

                  return (
                    <div
                      key={stage.title}
                      className={`p-3 rounded-lg border flex items-start gap-3 transition-all ${
                        isDone
                          ? "bg-emerald-500/10 border-emerald-500/30"
                          : isCurrent
                          ? "bg-violet-500/10 border-violet-500/40"
                          : "bg-muted/20 border-border opacity-50"
                      }`}
                    >
                      <div className="mt-0.5 shrink-0">
                        {isDone ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : isCurrent ? (
                          <Loader2 className="w-4 h-4 text-violet-300 animate-spin" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border border-muted-foreground/40" />
                        )}
                      </div>
                      <div className="space-y-0.5">
                        <div className="font-mono font-semibold text-foreground text-[11px]">
                          Langkah {idx + 1}: {stage.title}
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                          {stage.detail}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* PHASE 3: REVIEWING THE CHANGES */}
          {phase === "review" && recommendation && (
            <div className="space-y-4">
              {errorMsg && (
                <div className="p-3 rounded-lg border border-red-500/40 bg-red-500/10 text-red-200 text-xs">
                  {errorMsg}
                </div>
              )}

              {/* Summary & Provider */}
              <div className="p-3.5 rounded-lg border border-border bg-muted/40 flex flex-wrap items-center justify-between gap-2">
                <div className="space-y-1 flex-1 min-w-[240px]">
                  <div className="flex items-center gap-2 font-mono text-[11px] font-bold text-foreground">
                    <Brain className="w-3.5 h-3.5 text-amber-400" />
                    <span>Ringkasan Penalaran AI</span>
                    <span className="px-2 py-0.5 rounded bg-muted border border-border text-[10px] font-normal text-muted-foreground">
                      {recommendation.provider} / {recommendation.model}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {recommendation.summary}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => setShowReasoningInReview((v) => !v)}
                  className="flex items-center gap-1 px-2.5 py-1 rounded border border-border bg-card hover:bg-muted text-[11px] font-mono text-foreground transition"
                >
                  <span>{showReasoningInReview ? "Sembunyikan Langkah" : "Lihat Langkah Penalaran"}</span>
                  {showReasoningInReview ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              </div>

              {/* Collapsible AI Reasoning Steps */}
              {showReasoningInReview && recommendation.reasoning_steps.length > 0 && (
                <div className="p-3 rounded-lg border border-border bg-card/60 space-y-2">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-bold block">
                    Jejak Langkah Penalaran AI:
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {recommendation.reasoning_steps.map((step) => (
                      <div
                        key={step.step_number}
                        className="p-2.5 rounded border border-border/70 bg-muted/30 flex items-start gap-2"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                        <div>
                          <div className="font-mono font-semibold text-[11px] text-foreground">
                            {step.step_number}. {step.title}
                          </div>
                          <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">
                            {step.detail}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Proposed Changes List */}
              {changes.length === 0 ? (
                <div className="p-8 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-center space-y-2">
                  <ShieldCheck className="w-8 h-8 text-emerald-400 mx-auto" />
                  <h4 className="font-mono font-bold text-sm text-emerald-200">
                    Tidak Ada Perubahan yang Diperlukan
                  </h4>
                  <p className="text-xs text-emerald-300/80 max-w-md mx-auto">
                    Seluruh identitas, pejabat, tanggal dokumen, penomoran, harga, dan teks barang sudah bersih dan valid.
                  </p>
                </div>
              ) : (
                <div className="space-y-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2 px-1">
                    <div className="font-mono text-[11px] font-bold uppercase tracking-wider text-foreground">
                      Daftar Usulan Perubahan ({selectedChanges.length} dari {changes.length} dipilih)
                    </div>
                    <button
                      type="button"
                      onClick={toggleAll}
                      className="text-[11px] font-mono text-primary hover:underline"
                    >
                      {allSelected ? "Hapus Semua Pilihan" : "Pilih Semua Perubahan"}
                    </button>
                  </div>

                  <div className="space-y-2">
                    {changes.map((ch) => {
                      const isChecked = Boolean(selectedIds[ch.fix_id]);
                      return (
                        <div
                          key={ch.fix_id}
                          onClick={() => toggleItem(ch.fix_id)}
                          className={`p-3.5 rounded-lg border cursor-pointer transition-all space-y-2.5 ${
                            isChecked
                              ? "border-violet-500/40 bg-violet-500/5"
                              : "border-border bg-card/40 opacity-60"
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleItem(ch.fix_id);
                                }}
                                className={`w-4 h-4 rounded border flex items-center justify-center transition ${
                                  isChecked
                                    ? "bg-violet-500 border-violet-400 text-white"
                                    : "border-muted-foreground/50 bg-background"
                                }`}
                              >
                                {isChecked && <Check className="w-3 h-3" />}
                              </button>
                              <span className="font-semibold text-foreground text-xs">
                                {ch.field_label}
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5 font-mono text-[10px]">
                              <span className="px-2 py-0.5 rounded bg-primary/15 text-primary border border-primary/30 font-bold">
                                {ch.rule_code}
                              </span>
                              <span className="px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                                {TAB_LABELS[ch.target_tab] || ch.target_tab}
                              </span>
                            </div>
                          </div>

                          {/* Before -> After Diff */}
                          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] items-center gap-2 text-[11px] font-mono">
                            <div className="p-2 rounded bg-red-500/10 border border-red-500/25 text-red-200 break-words">
                              <span className="text-[9px] uppercase text-red-300/80 block mb-0.5">
                                Nilai Saat Ini
                              </span>
                              <span className="line-through opacity-85">{ch.current_value_display}</span>
                            </div>
                            <ArrowRight className="w-4 h-4 text-muted-foreground mx-auto hidden md:block" />
                            <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-200 break-words">
                              <span className="text-[9px] uppercase text-emerald-300/80 block mb-0.5">
                                Nilai Rekomendasi AI (Akan Diisi)
                              </span>
                              <span className="font-bold">{ch.proposed_value_display}</span>
                            </div>
                          </div>

                          {/* Reasoning */}
                          <p className="text-[11px] text-muted-foreground pl-2 border-l-2 border-violet-500/40 leading-relaxed">
                            {ch.reasoning}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3.5 border-t border-border bg-muted/30 flex flex-wrap items-center justify-between gap-2">
          {phase === "confirm" && (
            <>
              <span className="text-[11px] text-muted-foreground font-mono">
                Langkah 1 dari 4 — Konfirmasi Eksekusi AI
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-3.5 py-1.5 rounded border border-border bg-card hover:bg-muted text-foreground text-xs transition"
                >
                  Batal
                </button>
                <button
                  type="button"
                  onClick={handleStartAIWork}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs transition shadow-xs"
                >
                  <Wand2 className="w-3.5 h-3.5" />
                  <span>Konfirmasi &amp; Jalankan AI</span>
                </button>
              </div>
            </>
          )}

          {phase === "reasoning" && (
            <>
              <span className="text-[11px] text-muted-foreground font-mono">
                Langkah 2 dari 4 — Penalaran &amp; Analisis AI
              </span>
              <div className="flex items-center gap-2">
                {errorMsg && (
                  <>
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-3.5 py-1.5 rounded border border-border bg-card hover:bg-muted text-foreground text-xs transition"
                    >
                      Tutup
                    </button>
                    <button
                      type="button"
                      onClick={handleStartAIWork}
                      className="px-3.5 py-1.5 rounded bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs transition"
                    >
                      Coba Lagi
                    </button>
                  </>
                )}
              </div>
            </>
          )}

          {phase === "review" && (
            <>
              <span className="text-[11px] text-muted-foreground font-mono">
                Langkah 3 &amp; 4 — Tinjau lalu Buang (Scrap) atau Terapkan Perubahan
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleScrap}
                  disabled={isApplying}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded border border-red-500/40 bg-red-500/10 hover:bg-red-500/20 text-red-200 font-medium text-xs transition disabled:opacity-50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Buang / Scrap Rekomendasi</span>
                </button>

                {changes.length > 0 && (
                  <button
                    type="button"
                    onClick={handleApply}
                    disabled={isApplying || selectedChanges.length === 0}
                    className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition shadow-xs disabled:opacity-50"
                  >
                    {isApplying ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    )}
                    <span>
                      {isApplying
                        ? "Menerapkan..."
                        : `Terapkan Perubahan (${selectedChanges.length})`}
                    </span>
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
