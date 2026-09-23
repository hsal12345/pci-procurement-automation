"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { AIUsageResponse } from "@/types/ai";
import { Cpu, DollarSign, Database, ShieldAlert, Sparkles, RefreshCw, CheckCircle2 } from "lucide-react";

export default function AIUsageDashboard() {
  const { data: usage, isLoading, error, refetch } = useQuery<AIUsageResponse>({
    queryKey: ["ai_usage"],
    queryFn: () => apiClient.getAIUsage(),
  });

  return (
    <div className="p-6 max-w-4xl space-y-6 text-xs font-sans">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-primary" />
          <h1 className="text-base font-semibold text-foreground">
            Dasbor Konsumsi Token & Anggaran AI Bulanan (PRD Section 13)
          </h1>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-muted-foreground font-mono">
          Memuat data penggunaan kuota AI...
        </div>
      ) : error || !usage ? (
        <div className="p-6 border border-border rounded bg-muted/20 text-muted-foreground font-mono">
          Data penggunaan AI belum tercatat atau layanan berjalan dalam mode luring (Mock).
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="border border-border rounded-lg bg-card p-4 space-y-1">
            <span className="text-[10px] font-mono text-muted-foreground uppercase">
              Model & Penyedia Aktif
            </span>
            <div className="text-sm font-bold font-mono text-foreground flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>{(usage.provider || "MOCK").toUpperCase()}</span>
            </div>
            <span className="text-[10px] text-muted-foreground font-mono">
              Bulan: {usage.current_month || usage.year_month || "-"}
            </span>
          </div>

          <div className="border border-border rounded-lg bg-card p-4 space-y-1">
            <span className="text-[10px] font-mono text-muted-foreground uppercase">
              Total Token Dikonsumsi
            </span>
            <div className="text-lg font-bold font-mono text-foreground tabular-nums">
              {(usage.total_tokens || 0).toLocaleString()}
            </div>
            <span className="text-[10px] text-muted-foreground font-mono">
              Prompt: {usage.prompt_tokens ?? usage.total_prompt_tokens ?? 0} • Completion: {usage.completion_tokens ?? usage.total_completion_tokens ?? 0}
            </span>
          </div>

          <div className="border border-border rounded-lg bg-card p-4 space-y-1">
            <span className="text-[10px] font-mono text-muted-foreground uppercase">
              Batas Anggaran Bulanan
            </span>
            <div className="text-lg font-bold font-mono text-emerald-400 tabular-nums">
              ${(usage.total_cost_usd || 0).toFixed(4)} / ${(usage.monthly_budget_usd ?? usage.budget_cap_usd ?? 10).toFixed(2)}
            </div>
            <span className="text-[10px] text-muted-foreground font-mono">
              Sisa Kuota: ${(usage.remaining_budget_usd ?? usage.budget_remaining_usd ?? 10).toFixed(4)} USD
            </span>
          </div>
        </div>

      )}
    </div>
  );
}
