"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import {
  AIUsageResponse,
  AIRuntimeConfig,
  AIRuntimeConfigUpdate,
  AITestConnectionResponse,
  AIUsageLogItem,
  AIPlaygroundTestResponse,
} from "@/types/ai";
import {
  Cpu,
  DollarSign,
  Database,
  ShieldAlert,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Server,
  Cloud,
  HardDrive,
  Activity,
  Play,
  Settings,
  History,
  FileCheck2,
  Zap,
  Eye,
  EyeOff,
  Clock,
  ArrowRight,
  ShieldCheck,
  HelpCircle,
  Bot,
} from "lucide-react";
import { SystemKnowledgeChatTab } from "./system-knowledge-chat";

export default function AIUsageDashboard() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"runtime" | "playground" | "logs" | "audit" | "knowledge_chat">("runtime");

  // Telemetry logs filters
  const [logStatusFilter, setLogStatusFilter] = useState<string>("ALL");
  const [logTaskFilter, setLogTaskFilter] = useState<string>("ALL");

  // Show/hide API key
  const [showApiKey, setShowApiKey] = useState(false);

  // Connection test state
  const [isTestingConn, setIsTestingConn] = useState(false);
  const [connTestResult, setConnTestResult] = useState<AITestConnectionResponse | null>(null);

  // Playground test state
  const [playgroundType, setPlaygroundType] = useState<"DISCREPANCY" | "MAPPING">("DISCREPANCY");
  const [playgroundTextA, setPlaygroundTextA] = useState("Pembersih Porselen Botol 1 Liter");
  const [playgroundTextB, setPlaygroundTextB] = useState("Porstex Pembersih Keramik 1000ml");
  const [playgroundHeaders, setPlaygroundHeaders] = useState("No, Nama Barang, Spesifikasi, Kuantitas, Satuan, Harga Satuan, Total");
  const [isRunningPlayground, setIsRunningPlayground] = useState(false);
  const [playgroundResult, setPlaygroundResult] = useState<AIPlaygroundTestResponse | null>(null);

  // Feedback message
  const [actionMessage, setActionMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Queries
  const { data: usage, isLoading: isUsageLoading, refetch: refetchUsage } = useQuery<AIUsageResponse>({
    queryKey: ["ai_usage"],
    queryFn: () => apiClient.getAIUsage(),
  });

  const { data: config, isLoading: isConfigLoading, refetch: refetchConfig } = useQuery<AIRuntimeConfig>({
    queryKey: ["ai_runtime_config"],
    queryFn: () => apiClient.getAIRuntimeConfig(),
  });

  const { data: logs, isLoading: isLogsLoading, refetch: refetchLogs } = useQuery<AIUsageLogItem[]>({
    queryKey: ["ai_usage_logs", logStatusFilter, logTaskFilter],
    queryFn: () =>
      apiClient.getAIUsageLogs({
        limit: 50,
        status: logStatusFilter,
        task_type: logTaskFilter,
      }),
  });

  const { data: auditEvents, isLoading: isAuditLoading, refetch: refetchAudit } = useQuery<any[]>({
    queryKey: ["system_audit_events"],
    queryFn: () => apiClient.getAuditEvents({ limit: 50 }),
  });

  // Local form state initialized from config
  const [formMode, setFormMode] = useState<"api" | "local">("local");
  const [formProvider, setFormProvider] = useState<string>("mock");
  const [formBaseUrl, setFormBaseUrl] = useState<string>("");
  const [formApiKey, setFormApiKey] = useState<string>("");
  const [formModel, setFormModel] = useState<string>("");
  const [formTimeout, setFormTimeout] = useState<number>(30);
  const [formBudget, setFormBudget] = useState<number>(10.0);
  const [formAutoFallback, setFormAutoFallback] = useState<boolean>(true);
  const [formAiEnabled, setFormAiEnabled] = useState<boolean>(true);
  const [hasFormInitialized, setHasFormInitialized] = useState(false);

  // Sync form state when config loads for first time
  if (config && !hasFormInitialized) {
    setFormMode(config.runtime_mode);
    setFormProvider(config.provider);
    setFormBaseUrl(config.base_url);
    setFormModel(config.model);
    setFormTimeout(config.timeout_seconds);
    setFormBudget(config.monthly_budget_usd);
    setFormAutoFallback(config.auto_fallback_to_local);
    setFormAiEnabled(config.ai_enabled);
    setHasFormInitialized(true);
  }

  // Update Config Mutation
  const updateConfigMutation = useMutation({
    mutationFn: (data: AIRuntimeConfigUpdate) => apiClient.updateAIRuntimeConfig(data),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["ai_runtime_config"] });
      queryClient.invalidateQueries({ queryKey: ["ai_usage"] });
      queryClient.invalidateQueries({ queryKey: ["system_audit_events"] });
      setActionMessage({
        type: "success",
        text: `Konfigurasi berhasil disimpan. Runtime aktif: ${updated.runtime_mode.toUpperCase()} (${updated.provider.toUpperCase()} - ${updated.model}).`,
      });
      setTimeout(() => setActionMessage(null), 5000);
    },
    onError: (err: any) => {
      setActionMessage({
        type: "error",
        text: err?.message || "Gagal memperbarui konfigurasi AI runtime.",
      });
    },
  });

  // Handle mode toggle (API vs Local)
  const handleModeChange = (newMode: "api" | "local") => {
    setFormMode(newMode);
    if (newMode === "local") {
      setFormProvider("mock");
      setFormBaseUrl("local://deterministic-engine");
      setFormModel("mock-rule-engine");
    } else {
      setFormProvider("gemini");
      setFormBaseUrl("https://generativelanguage.googleapis.com/v1beta/openai");
      setFormModel("gemini-2.0-flash");
    }
  };

  // Handle provider preset selection
  const handleProviderChange = (newProvider: string) => {
    setFormProvider(newProvider);
    if (newProvider === "gemini") {
      setFormBaseUrl("https://generativelanguage.googleapis.com/v1beta/openai");
      setFormModel("gemini-2.0-flash");
    } else if (newProvider === "openrouter") {
      setFormBaseUrl("https://openrouter.ai/api/v1");
      setFormModel("google/gemini-2.0-flash-exp:free");
    } else if (newProvider === "openai") {
      setFormBaseUrl("https://api.openai.com/v1");
      setFormModel("gpt-4o-mini");
    } else if (newProvider === "ollama") {
      setFormBaseUrl("http://localhost:11434/v1");
      setFormModel("llama3.2");
    } else if (newProvider === "mock") {
      setFormBaseUrl("local://deterministic-engine");
      setFormModel("mock-rule-engine");
    }
  };

  // Run Connection Test
  const runConnectionTest = async () => {
    setIsTestingConn(true);
    setConnTestResult(null);
    try {
      const res = await apiClient.testAIConnection({
        runtime_mode: formMode,
        provider: formProvider,
        base_url: formBaseUrl,
        api_key: formApiKey || undefined,
        model: formModel,
        timeout_seconds: formTimeout,
      });
      setConnTestResult(res);
    } catch (err: any) {
      setConnTestResult({
        status: "ERROR",
        latency_ms: 0,
        runtime_mode: formMode,
        provider: formProvider,
        model: formModel,
        endpoint: formBaseUrl,
        message: err.message || "Gagal menghubungi service.",
      });
    } finally {
      setIsTestingConn(false);
    }
  };

  // Save Configuration
  const handleSaveConfig = () => {
    updateConfigMutation.mutate({
      runtime_mode: formMode,
      provider: formProvider,
      base_url: formBaseUrl,
      api_key: formApiKey || undefined,
      model: formModel,
      timeout_seconds: formTimeout,
      monthly_budget_usd: formBudget,
      auto_fallback_to_local: formAutoFallback,
      ai_enabled: formAiEnabled,
    });
  };

  // Run Playground Live Test
  const handlePlaygroundRun = async () => {
    setIsRunningPlayground(true);
    setPlaygroundResult(null);
    try {
      const res = await apiClient.runAIPlaygroundTest({
        test_type: playgroundType,
        text_a: playgroundTextA,
        text_b: playgroundTextB,
        sample_headers: playgroundHeaders.split(",").map((s) => s.trim()),
      });
      setPlaygroundResult(res);
      queryClient.invalidateQueries({ queryKey: ["ai_usage_logs"] });
      queryClient.invalidateQueries({ queryKey: ["ai_usage"] });
    } catch (err: any) {
      setActionMessage({
        type: "error",
        text: err.message || "Gagal menjalankan pengujian playground.",
      });
    } finally {
      setIsRunningPlayground(false);
    }
  };

  const currentMode = config?.runtime_mode || usage?.runtime_mode || "local";
  const currentProvider = config?.provider || usage?.provider || "mock";
  const isBudgetExceeded = usage?.is_budget_exceeded || false;
  const budgetCap = usage?.monthly_budget_usd ?? usage?.budget_cap_usd ?? 10.0;
  const currentCost = usage?.total_cost_usd ?? 0.0;
  const costPercent = budgetCap > 0 ? Math.min(100, (currentCost / budgetCap) * 100) : 0;

  return (
    <div className="p-6 max-w-6xl space-y-6 text-xs font-sans">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border pb-4 gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-primary/10 text-primary">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-base font-bold text-foreground">
                AI & Audit Usage Management
              </h1>
              <p className="text-[11px] text-muted-foreground">
                Tata Kelola Runtime AI (API vs Lokal), Audit Telemetri Token & Jejak Kepatuhan Dokumen (PRD FR05 & Seksi 11)
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Active Runtime Badge */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border bg-card shadow-sm">
            <span className="relative flex h-2 w-2">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  currentMode === "api" ? "bg-emerald-400" : "bg-sky-400"
                }`}
              />
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  currentMode === "api" ? "bg-emerald-500" : "bg-sky-500"
                }`}
              />
            </span>
            <span className="font-mono text-[11px] font-semibold text-foreground uppercase">
              {currentMode === "api" ? "API Cloud Runtime" : "Local Runtime"}
            </span>
            <span className="text-muted-foreground font-mono text-[10px]">
              ({currentProvider.toUpperCase()})
            </span>
          </div>

          <button
            type="button"
            onClick={runConnectionTest}
            disabled={isTestingConn}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border hover:bg-muted font-medium transition disabled:opacity-50"
            title="Uji Koneksi Runtime"
          >
            <Activity className={`w-3.5 h-3.5 ${isTestingConn ? "animate-spin text-primary" : "text-muted-foreground"}`} />
            <span>{isTestingConn ? "Menguji..." : "Tes Koneksi"}</span>
          </button>

          <button
            type="button"
            onClick={() => {
              refetchUsage();
              refetchConfig();
              refetchLogs();
              refetchAudit();
            }}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-md border border-border hover:bg-muted"
            title="Muat Ulang Data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Action Notification Alert */}
      {actionMessage && (
        <div
          className={`p-3 rounded-md border flex items-center justify-between text-xs animate-in fade-in-50 duration-200 ${
            actionMessage.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
              : "bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400"
          }`}
        >
          <div className="flex items-center gap-2">
            {actionMessage.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            )}
            <span>{actionMessage.text}</span>
          </div>
          <button
            type="button"
            onClick={() => setActionMessage(null)}
            className="text-xs hover:opacity-75 font-mono"
          >
            ✕
          </button>
        </div>
      )}

      {/* Connection Test Instant Diagnostic Result */}
      {connTestResult && (
        <div
          className={`p-3.5 rounded-lg border text-xs space-y-1.5 ${
            connTestResult.status === "ONLINE"
              ? "bg-emerald-500/5 border-emerald-500/30 text-emerald-800 dark:text-emerald-300"
              : connTestResult.status === "DEGRADED"
              ? "bg-amber-500/5 border-amber-500/30 text-amber-800 dark:text-amber-300"
              : "bg-rose-500/5 border-rose-500/30 text-rose-800 dark:text-rose-300"
          }`}
        >
          <div className="flex items-center justify-between font-medium">
            <div className="flex items-center gap-2">
              {connTestResult.status === "ONLINE" ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
              ) : connTestResult.status === "DEGRADED" ? (
                <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
              ) : (
                <XCircle className="w-4 h-4 text-rose-500 flex-shrink-0" />
              )}
              <span className="font-semibold">
                Hasil Uji Koneksi: {connTestResult.status} ({connTestResult.runtime_mode.toUpperCase()})
              </span>
            </div>
            <span className="font-mono text-[11px] bg-background/50 px-2 py-0.5 rounded border border-current/20">
              {connTestResult.latency_ms} ms
            </span>
          </div>
          <p className="text-[11px] opacity-90 pl-6">{connTestResult.message}</p>
        </div>
      )}

      {/* 4 Summary Telemetry Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Runtime & Provider */}
        <div className="border border-border rounded-lg bg-card p-4 space-y-1.5 shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[10px] font-mono uppercase tracking-wider">Runtime Aktif</span>
            {currentMode === "api" ? (
              <Cloud className="w-4 h-4 text-emerald-500" />
            ) : (
              <HardDrive className="w-4 h-4 text-sky-500" />
            )}
          </div>
          <div className="text-sm font-bold font-mono text-foreground flex items-center gap-1.5">
            <span className="truncate">
              {currentMode === "api" ? "API RUNTIME (Cloud)" : "LOCAL RUNTIME"}
            </span>
          </div>
          <div className="text-[10px] text-muted-foreground font-mono flex items-center justify-between">
            <span>Provider: {currentProvider.toUpperCase()}</span>
            <span className="text-emerald-500 font-semibold">
              {config?.auto_fallback_to_local ? "Auto-Failover ON" : "Failover OFF"}
            </span>
          </div>
        </div>

        {/* Card 2: Token Consumption */}
        <div className="border border-border rounded-lg bg-card p-4 space-y-1.5 shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[10px] font-mono uppercase tracking-wider">Konsumsi Token Bulan Ini</span>
            <Sparkles className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-lg font-bold font-mono text-foreground tabular-nums">
            {(usage?.total_tokens || 0).toLocaleString()}
          </div>
          <div className="text-[10px] text-muted-foreground font-mono flex items-center justify-between">
            <span>P: {usage?.prompt_tokens ?? 0}</span>
            <span>C: {usage?.completion_tokens ?? 0}</span>
            <span>Req: {usage?.total_requests ?? 0}</span>
          </div>
        </div>

        {/* Card 3: Monthly Budget USD */}
        <div className="border border-border rounded-lg bg-card p-4 space-y-1.5 shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[10px] font-mono uppercase tracking-wider">Batas Anggaran Bulanan</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-lg font-bold font-mono text-foreground tabular-nums flex items-baseline gap-1">
            <span className="text-emerald-500">${currentCost.toFixed(4)}</span>
            <span className="text-muted-foreground text-xs font-normal">
              / ${budgetCap.toFixed(2)} USD
            </span>
          </div>
          {/* Progress bar */}
          <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                costPercent > 90 ? "bg-rose-500" : costPercent > 70 ? "bg-amber-500" : "bg-emerald-500"
              }`}
              style={{ width: `${costPercent}%` }}
            />
          </div>
          <div className="text-[10px] text-muted-foreground font-mono flex items-center justify-between">
            <span>Sisa: ${(usage?.remaining_budget_usd ?? budgetCap).toFixed(4)}</span>
            <span>{costPercent.toFixed(1)}%</span>
          </div>
        </div>

        {/* Card 4: Latency & Reliability */}
        <div className="border border-border rounded-lg bg-card p-4 space-y-1.5 shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[10px] font-mono uppercase tracking-wider">Rata-rata Latensi</span>
            <Activity className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-lg font-bold font-mono text-foreground tabular-nums flex items-baseline gap-1">
            <span>{usage?.average_latency_ms || 15}</span>
            <span className="text-xs text-muted-foreground font-normal">ms</span>
          </div>
          <div className="text-[10px] text-muted-foreground font-mono flex items-center justify-between">
            <span className="text-emerald-500">
              Sukses: {usage?.success_count ?? 0}
            </span>
            <span className="text-rose-500">
              Gagal: {usage?.failure_count ?? 0}
            </span>
          </div>
        </div>
      </div>

      {/* Main Tabs Navigation */}
      <div className="border-b border-border flex items-center gap-1">
        <button
          type="button"
          onClick={() => setActiveTab("runtime")}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium border-b-2 -mb-px text-xs transition ${
            activeTab === "runtime"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
          }`}
        >
          <Settings className="w-4 h-4" />
          <span>Pengaturan Runtime (API vs Local)</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("playground")}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium border-b-2 -mb-px text-xs transition ${
            activeTab === "playground"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
          }`}
        >
          <Play className="w-4 h-4" />
          <span>Uji Coba Interaktif (Playground)</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("logs")}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium border-b-2 -mb-px text-xs transition ${
            activeTab === "logs"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
          }`}
        >
          <History className="w-4 h-4" />
          <span>Log Telemetri AI</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("audit")}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium border-b-2 -mb-px text-xs transition ${
            activeTab === "audit"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
          }`}
        >
          <FileCheck2 className="w-4 h-4" />
          <span>Jejak Audit Sistem</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("knowledge_chat")}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium border-b-2 -mb-px text-xs transition ${
            activeTab === "knowledge_chat"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
          }`}
        >
          <Bot className="w-4 h-4" />
          <span>System Knowlage Chat</span>
          <span className="px-1.5 py-0.5 rounded-full text-[9px] bg-primary/10 text-primary font-mono font-bold">
            Baru
          </span>
        </button>
      </div>

      {/* TAB 1: RUNTIME CONFIGURATION */}
      {activeTab === "runtime" && (
        <div className="space-y-6">
          {/* Prominent Runtime Selector Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Option A: API Runtime */}
            <div
              onClick={() => handleModeChange("api")}
              className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                formMode === "api"
                  ? "border-emerald-500 bg-emerald-500/5 shadow-sm"
                  : "border-border hover:border-muted-foreground/30 bg-card"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-lg ${formMode === "api" ? "bg-emerald-500 text-white" : "bg-muted text-muted-foreground"}`}>
                    <Cloud className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-foreground">API Runtime (Cloud / Eksternal)</h3>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                        Rekomendasi
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Google Gemini, OpenRouter, atau OpenAI via Chat Completions API.
                    </p>
                  </div>
                </div>
                <input
                  type="radio"
                  name="runtime_mode"
                  checked={formMode === "api"}
                  onChange={() => handleModeChange("api")}
                  className="mt-1"
                />
              </div>

              <div className="mt-4 pt-3 border-t border-border/50 text-[11px] text-muted-foreground space-y-1">
                <div className="flex items-center gap-1.5 text-foreground/80">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Penalaran semantik mendalam untuk mendeteksi substitusi merek dagang.</span>
                </div>
                <div className="flex items-center gap-1.5 text-foreground/80">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Dibatasi batas anggaran bulanan ($10.00 USD) dengan auto-guard.</span>
                </div>
              </div>
            </div>

            {/* Option B: Local Runtime */}
            <div
              onClick={() => handleModeChange("local")}
              className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                formMode === "local"
                  ? "border-sky-500 bg-sky-500/5 shadow-sm"
                  : "border-border hover:border-muted-foreground/30 bg-card"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-lg ${formMode === "local" ? "bg-sky-500 text-white" : "bg-muted text-muted-foreground"}`}>
                    <HardDrive className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-foreground">Local Runtime (On-Premise / Luring)</h3>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-sky-500/15 text-sky-600 dark:text-sky-400 border border-sky-500/30">
                        100% Offline
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Ollama Local LLM (Llama 3.2, Mistral) atau Mesin Aturan Deterministik Lokal.
                    </p>
                  </div>
                </div>
                <input
                  type="radio"
                  name="runtime_mode"
                  checked={formMode === "local"}
                  onChange={() => handleModeChange("local")}
                  className="mt-1"
                />
              </div>

              <div className="mt-4 pt-3 border-t border-border/50 text-[11px] text-muted-foreground space-y-1">
                <div className="flex items-center gap-1.5 text-foreground/80">
                  <CheckCircle2 className="w-3.5 h-3.5 text-sky-500" />
                  <span>Bebas biaya token ($0.00 USD), data tetap aman di dalam server lokal.</span>
                </div>
                <div className="flex items-center gap-1.5 text-foreground/80">
                  <CheckCircle2 className="w-3.5 h-3.5 text-sky-500" />
                  <span>Respon sangat cepat (5-20ms) dan keandalan operasional tanpa internet.</span>
                </div>
              </div>
            </div>
          </div>

          {/* Form Settings Details */}
          <div className="border border-border rounded-xl bg-card p-5 space-y-5 shadow-sm">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                <h3 className="font-semibold text-foreground text-sm">
                  Parameter Konfigurasi {formMode === "api" ? "Cloud API" : "Local Runtime"}
                </h3>
              </div>
              <span className="text-[11px] text-muted-foreground font-mono">
                Status Penyimpanan: Terhubung & Persisten
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Provider Selection */}
              <div className="space-y-1.5">
                <label className="font-semibold text-foreground">
                  Penyedia AI (Provider)
                </label>
                {formMode === "api" ? (
                  <select
                    value={formProvider}
                    onChange={(e) => handleProviderChange(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-xs focus:ring-1 focus:ring-primary outline-none"
                  >
                    <option value="gemini">Google Gemini (Recommended / Default)</option>
                    <option value="openrouter">OpenRouter (Free Tier Models Available)</option>
                    <option value="openai">OpenAI (GPT-4o-mini / GPT-4o)</option>
                    <option value="custom">Custom OpenAI-Compatible API</option>
                  </select>
                ) : (
                  <select
                    value={formProvider}
                    onChange={(e) => handleProviderChange(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-xs focus:ring-1 focus:ring-primary outline-none"
                  >
                    <option value="mock">Mesin Aturan Deterministik Lokal (100% Offline & Instan)</option>
                    <option value="ollama">Ollama Local LLM (Llama 3.2, Mistral, Qwen)</option>
                    <option value="custom">Custom Local vLLM / LocalAI Endpoint</option>
                  </select>
                )}
                <p className="text-[10px] text-muted-foreground">
                  {formMode === "api"
                    ? "Gunakan endpoint OpenAI-compatible resmi dari penyedia cloud."
                    : "Pilih mesin aturan lokal untuk verifikasi cepat atau Ollama jika model terpasang."}
                </p>
              </div>

              {/* Model Name */}
              <div className="space-y-1.5">
                <label className="font-semibold text-foreground">
                  Nama Model (Model Identifier)
                </label>
                <input
                  type="text"
                  value={formModel}
                  onChange={(e) => setFormModel(e.target.value)}
                  placeholder="e.g. gemini-2.0-flash atau llama3.2"
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-xs font-mono focus:ring-1 focus:ring-primary outline-none"
                />
                {/* Model preset badges */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {formMode === "api" ? (
                    <>
                      <button
                        type="button"
                        onClick={() => setFormModel("gemini-2.0-flash")}
                        className="px-2 py-0.5 text-[10px] font-mono bg-muted hover:bg-primary/10 rounded border border-border"
                      >
                        gemini-2.0-flash
                      </button>
                      <button
                        type="button"
                        onClick={() => setFormModel("google/gemini-2.0-flash-exp:free")}
                        className="px-2 py-0.5 text-[10px] font-mono bg-muted hover:bg-primary/10 rounded border border-border"
                      >
                        gemini-2.0 (openrouter free)
                      </button>
                      <button
                        type="button"
                        onClick={() => setFormModel("gpt-4o-mini")}
                        className="px-2 py-0.5 text-[10px] font-mono bg-muted hover:bg-primary/10 rounded border border-border"
                      >
                        gpt-4o-mini
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => setFormModel("mock-rule-engine")}
                        className="px-2 py-0.5 text-[10px] font-mono bg-muted hover:bg-primary/10 rounded border border-border"
                      >
                        mock-rule-engine
                      </button>
                      <button
                        type="button"
                        onClick={() => setFormModel("llama3.2")}
                        className="px-2 py-0.5 text-[10px] font-mono bg-muted hover:bg-primary/10 rounded border border-border"
                      >
                        llama3.2
                      </button>
                      <button
                        type="button"
                        onClick={() => setFormModel("mistral")}
                        className="px-2 py-0.5 text-[10px] font-mono bg-muted hover:bg-primary/10 rounded border border-border"
                      >
                        mistral
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Base URL */}
              <div className="space-y-1.5 md:col-span-2">
                <label className="font-semibold text-foreground flex items-center justify-between">
                  <span>Base URL Endpoint</span>
                  {formMode === "local" && (
                    <span className="text-[10px] text-sky-500 font-mono">
                      Docker Note: Gunakan http://host.docker.internal:11434/v1 untuk Ollama host
                    </span>
                  )}
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={formBaseUrl}
                    onChange={(e) => setFormBaseUrl(e.target.value)}
                    placeholder="https://... atau http://localhost:11434/v1"
                    className="flex-1 px-3 py-2 bg-background border border-border rounded-md text-xs font-mono focus:ring-1 focus:ring-primary outline-none"
                  />
                  {formMode === "local" && (
                    <button
                      type="button"
                      onClick={() => setFormBaseUrl("http://host.docker.internal:11434/v1")}
                      className="px-2.5 py-1 text-[11px] bg-muted hover:bg-muted/80 rounded border border-border font-mono whitespace-nowrap"
                    >
                      Host Docker
                    </button>
                  )}
                </div>
              </div>

              {/* API Key (Only in API Mode) */}
              {formMode === "api" && (
                <div className="space-y-1.5 md:col-span-2">
                  <label className="font-semibold text-foreground flex items-center justify-between">
                    <span>API Key / Secret Token</span>
                    {config?.has_api_key && (
                      <span className="text-[10px] text-emerald-500 font-mono">
                        Tersimpan: {config.api_key_masked}
                      </span>
                    )}
                  </label>
                  <div className="relative">
                    <input
                      type={showApiKey ? "text" : "password"}
                      value={formApiKey}
                      onChange={(e) => setFormApiKey(e.target.value)}
                      placeholder={config?.has_api_key ? "Masukkan API Key baru untuk mengganti..." : "Masukkan API Key (e.g. AIzaSy... / sk-...)"}
                      className="w-full pr-10 px-3 py-2 bg-background border border-border rounded-md text-xs font-mono focus:ring-1 focus:ring-primary outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              )}

              {/* Timeout & Budget */}
              <div className="space-y-1.5">
                <label className="font-semibold text-foreground">
                  Batas Waktu Respon (Timeout Detik)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="5"
                    max="120"
                    value={formTimeout}
                    onChange={(e) => setFormTimeout(parseInt(e.target.value) || 30)}
                    className="w-24 px-3 py-2 bg-background border border-border rounded-md text-xs font-mono focus:ring-1 focus:ring-primary outline-none"
                  />
                  <span className="text-muted-foreground text-xs">detik</span>
                </div>
              </div>

              {formMode === "api" && (
                <div className="space-y-1.5">
                  <label className="font-semibold text-foreground">
                    Batas Anggaran Bulanan (USD)
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground font-mono">$</span>
                    <input
                      type="number"
                      step="0.5"
                      min="1"
                      max="500"
                      value={formBudget}
                      onChange={(e) => setFormBudget(parseFloat(e.target.value) || 10.0)}
                      className="w-28 px-3 py-2 bg-background border border-border rounded-md text-xs font-mono focus:ring-1 focus:ring-primary outline-none"
                    />
                    <span className="text-muted-foreground text-xs">USD / Bulan</span>
                  </div>
                </div>
              )}
            </div>

            {/* Checkbox Options */}
            <div className="pt-2 border-t border-border space-y-2">
              <label className="flex items-center gap-2 text-xs text-foreground cursor-pointer">
                <input
                  type="checkbox"
                  checked={formAutoFallback}
                  onChange={(e) => setFormAutoFallback(e.target.checked)}
                  className="rounded border-border text-primary focus:ring-primary"
                />
                <span className="font-semibold">
                  Auto-Fallback ke Local Engine saat terjadi kendala
                </span>
                <span className="text-muted-foreground text-[11px]">
                  (Menghindari blokir proses SPJ jika provider cloud offline atau kuota habis)
                </span>
              </label>

              <label className="flex items-center gap-2 text-xs text-foreground cursor-pointer">
                <input
                  type="checkbox"
                  checked={formAiEnabled}
                  onChange={(e) => setFormAiEnabled(e.target.checked)}
                  className="rounded border-border text-primary focus:ring-primary"
                />
                <span className="font-semibold">Aktifkan Bantuan Verifikasi AI</span>
              </label>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-between pt-4 border-t border-border">
              <button
                type="button"
                onClick={runConnectionTest}
                disabled={isTestingConn}
                className="flex items-center gap-2 px-4 py-2 rounded-md border border-border hover:bg-muted font-medium transition disabled:opacity-50"
              >
                <Activity className={`w-4 h-4 ${isTestingConn ? "animate-spin text-primary" : "text-muted-foreground"}`} />
                <span>{isTestingConn ? "Menguji Koneksi..." : "Tes Koneksi Sekarang"}</span>
              </button>

              <button
                type="button"
                onClick={handleSaveConfig}
                disabled={updateConfigMutation.isPending}
                className="flex items-center gap-2 px-5 py-2 rounded-md bg-primary text-primary-foreground font-semibold hover:opacity-90 transition disabled:opacity-50 shadow-sm"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>
                  {updateConfigMutation.isPending ? "Menyimpan..." : "Simpan & Terapkan Konfigurasi"}
                </span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: INTERACTIVE PLAYGROUND / LIVE TEST */}
      {activeTab === "playground" && (
        <div className="space-y-6">
          <div className="border border-border rounded-xl bg-card p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h3 className="font-semibold text-foreground text-sm flex items-center gap-2">
                  <Play className="w-4 h-4 text-primary" />
                  Uji Coba Langsung Runtime AI ({currentMode.toUpperCase()})
                </h3>
                <p className="text-[11px] text-muted-foreground">
                  Uji kemampuan deteksi semantik atau pemetaan tabel secara langsung tanpa harus mengunggah berkas Excel lengkap.
                </p>
              </div>

              <div className="flex items-center gap-1 bg-muted p-1 rounded-md border border-border">
                <button
                  type="button"
                  onClick={() => setPlaygroundType("DISCREPANCY")}
                  className={`px-3 py-1 rounded text-xs font-medium transition ${
                    playgroundType === "DISCREPANCY" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground"
                  }`}
                >
                  Deteksi Anomali Semantik
                </button>
                <button
                  type="button"
                  onClick={() => setPlaygroundType("MAPPING")}
                  className={`px-3 py-1 rounded text-xs font-medium transition ${
                    playgroundType === "MAPPING" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground"
                  }`}
                >
                  Pemetaan Kolom
                </button>
              </div>
            </div>

            {/* Test Scenario Form */}
            {playgroundType === "DISCREPANCY" ? (
              <div className="space-y-4">
                {/* Presets */}
                <div className="space-y-1.5">
                  <span className="text-[11px] font-semibold text-muted-foreground">
                    Contoh Kasus Uji Cepat:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setPlaygroundTextA("Pembersih Porselen Botol 1 Liter");
                        setPlaygroundTextB("Porstex Pembersih Keramik 1000ml");
                      }}
                      className="px-2.5 py-1 text-[11px] bg-muted hover:bg-primary/10 rounded border border-border text-foreground"
                    >
                      Substitusi Merek (Porstex vs Generik)
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setPlaygroundTextA("Buku Tulis Garis 38 Lembar Sinar Dunia");
                        setPlaygroundTextB("Buku Tulis Garis 58 Lembar Sinar Dunia");
                      }}
                      className="px-2.5 py-1 text-[11px] bg-muted hover:bg-primary/10 rounded border border-border text-foreground"
                    >
                      Kontradiksi Spesifikasi (38 vs 58 Lembar)
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setPlaygroundTextA("Kertas HVS A4 70gr (1 Rim)");
                        setPlaygroundTextB("Kertas HVS A4 70gr (500 Lembar)");
                      }}
                      className="px-2.5 py-1 text-[11px] bg-muted hover:bg-primary/10 rounded border border-border text-foreground"
                    >
                      Inkompatibilitas Satuan (Rim vs Lembar)
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="font-semibold text-foreground">
                      Deskripsi Dokumen Asal (misal: HPS / D01)
                    </label>
                    <textarea
                      rows={3}
                      value={playgroundTextA}
                      onChange={(e) => setPlaygroundTextA(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-md text-xs font-mono focus:ring-1 focus:ring-primary outline-none"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-semibold text-foreground">
                      Deskripsi Dokumen Pembanding (misal: Pesanan / Faktur D05-D06)
                    </label>
                    <textarea
                      rows={3}
                      value={playgroundTextB}
                      onChange={(e) => setPlaygroundTextB(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-md text-xs font-mono focus:ring-1 focus:ring-primary outline-none"
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <label className="font-semibold text-foreground">
                  Daftar Nama Kolom Header Spreadsheet (Pisahkan dengan koma)
                </label>
                <input
                  type="text"
                  value={playgroundHeaders}
                  onChange={(e) => setPlaygroundHeaders(e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-xs font-mono focus:ring-1 focus:ring-primary outline-none"
                />
              </div>
            )}

            {/* Run Button */}
            <div className="flex items-center justify-between pt-3 border-t border-border">
              <span className="text-[11px] text-muted-foreground font-mono">
                Target Eksekusi: {currentMode.toUpperCase()} ({currentProvider.toUpperCase()} / {config?.model})
              </span>

              <button
                type="button"
                onClick={handlePlaygroundRun}
                disabled={isRunningPlayground}
                className="flex items-center gap-2 px-5 py-2 rounded-md bg-primary text-primary-foreground font-semibold hover:opacity-90 transition disabled:opacity-50 shadow-sm"
              >
                <Play className={`w-4 h-4 ${isRunningPlayground ? "animate-spin" : ""}`} />
                <span>{isRunningPlayground ? "Mengevaluasi..." : "Jalankan Pengujian"}</span>
              </button>
            </div>
          </div>

          {/* Playground Result Display */}
          {playgroundResult && (
            <div className="border border-border rounded-xl bg-card p-5 space-y-4 shadow-sm animate-in fade-in-50 duration-200">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  <h4 className="font-bold text-foreground text-sm">
                    Hasil Analisis AI Playground
                  </h4>
                </div>

                <div className="flex items-center gap-3 text-[11px] font-mono">
                  <span className="bg-muted px-2 py-0.5 rounded border border-border">
                    {playgroundResult.runtime_mode.toUpperCase()} ({playgroundResult.provider})
                  </span>
                  <span className="text-emerald-500 font-semibold">
                    {playgroundResult.latency_ms} ms
                  </span>
                  <span>
                    Biaya: ${playgroundResult.cost_usd.toFixed(6)} USD
                  </span>
                </div>
              </div>

              {playgroundType === "DISCREPANCY" ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono px-2.5 py-1 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30 font-semibold text-xs">
                      {playgroundResult.output.discrepancy_type}
                    </span>
                    <span className="font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground text-[10px]">
                      Severity: {playgroundResult.output.severity}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-muted/40 border border-border space-y-1.5">
                    <span className="text-[10px] font-mono uppercase text-muted-foreground font-semibold">
                      Penjelasan Temuan Semantik:
                    </span>
                    <p className="text-xs text-foreground leading-relaxed">
                      {playgroundResult.output.explanation || playgroundResult.output.message}
                    </p>
                  </div>

                  <div className="p-3 rounded-lg bg-sky-500/5 border border-sky-500/20 space-y-1">
                    <span className="text-[10px] font-mono uppercase text-sky-600 dark:text-sky-400 font-semibold">
                      Rekomendasi Tindak Lanjut Administratif:
                    </span>
                    <p className="text-xs text-sky-950 dark:text-sky-200 leading-relaxed">
                      {playgroundResult.output.recommended_action}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="p-3 rounded-lg bg-muted/40 border border-border space-y-2">
                    <span className="text-[10px] font-mono uppercase text-muted-foreground font-semibold">
                      Hasil Deteksi Kolom Header:
                    </span>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {Object.entries(playgroundResult.output.column_mapping || {}).map(([key, colIdx]) => (
                        <div key={key} className="p-2 rounded bg-card border border-border font-mono text-[11px]">
                          <span className="text-muted-foreground block text-[10px]">{key}</span>
                          <span className="font-bold text-foreground">Kolom #{String(colIdx)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {playgroundResult.output.reasoning}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: AI TELEMETRY LOGS */}
      {activeTab === "logs" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold text-foreground text-sm flex items-center gap-2">
                <History className="w-4 h-4 text-primary" />
                Log Telemetri & Aktivitas Permintaan AI
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Daftar rekaman eksekusi pemanggilan AI dari tabel ai_usage_logs beserta metrik latensi dan biaya.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={logStatusFilter}
                onChange={(e) => setLogStatusFilter(e.target.value)}
                className="px-2.5 py-1.5 bg-background border border-border rounded-md text-xs font-mono"
              >
                <option value="ALL">Semua Status</option>
                <option value="SUCCESS">SUCCESS</option>
                <option value="FAILED">FAILED</option>
                <option value="TIMEOUT">TIMEOUT</option>
                <option value="BUDGET_EXCEEDED">BUDGET_EXCEEDED</option>
                <option value="FALLBACK">FALLBACK</option>
              </select>

              <select
                value={logTaskFilter}
                onChange={(e) => setLogTaskFilter(e.target.value)}
                className="px-2.5 py-1.5 bg-background border border-border rounded-md text-xs font-mono"
              >
                <option value="ALL">Semua Tipe Tugas</option>
                <option value="MAPPING_ASSISTANT">MAPPING_ASSISTANT</option>
                <option value="DISCREPANCY_AUDITOR">DISCREPANCY_AUDITOR</option>
                <option value="PLAYGROUND">PLAYGROUND</option>
              </select>
            </div>
          </div>

          <div className="border border-border rounded-xl bg-card overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/50 text-[10px] font-mono uppercase text-muted-foreground">
                    <th className="py-2.5 px-3">Waktu (UTC)</th>
                    <th className="py-2.5 px-3">Tugas</th>
                    <th className="py-2.5 px-3">Penyedia / Model</th>
                    <th className="py-2.5 px-3 text-right">Tokens (P/C/Tot)</th>
                    <th className="py-2.5 px-3 text-right">Biaya (USD)</th>
                    <th className="py-2.5 px-3 text-right">Latensi</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border font-mono text-[11px]">
                  {isLogsLoading ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground font-mono">
                        Memuat rekaman log telemetri...
                      </td>
                    </tr>
                  ) : !logs || logs.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground font-mono">
                        Belum ada rekaman aktivitas AI pada filter ini.
                      </td>
                    </tr>
                  ) : (
                    logs.map((log) => (
                      <tr key={log.id} className="hover:bg-muted/30 transition">
                        <td className="py-2.5 px-3 whitespace-nowrap text-muted-foreground">
                          {log.created_at ? log.created_at.replace("T", " ").slice(0, 19) : "-"}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-foreground">
                          {log.task_type}
                        </td>
                        <td className="py-2.5 px-3 text-muted-foreground">
                          <span className="text-foreground font-semibold">{log.provider.toUpperCase()}</span>
                          <span className="text-[10px] block opacity-75">{log.model}</span>
                        </td>
                        <td className="py-2.5 px-3 text-right tabular-nums">
                          {log.prompt_tokens} / {log.completion_tokens} /{" "}
                          <span className="font-semibold text-foreground">{log.total_tokens}</span>
                        </td>
                        <td className="py-2.5 px-3 text-right tabular-nums text-emerald-500 font-medium">
                          ${log.estimated_cost_usd.toFixed(6)}
                        </td>
                        <td className="py-2.5 px-3 text-right tabular-nums">
                          {log.latency_ms} ms
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                              log.status === "SUCCESS"
                                ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                                : log.status === "FALLBACK"
                                ? "bg-sky-500/15 text-sky-600 dark:text-sky-400 border border-sky-500/30"
                                : log.status === "TIMEOUT"
                                ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                                : "bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30"
                            }`}
                          >
                            {log.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: SYSTEM AUDIT TRAIL */}
      {activeTab === "audit" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-foreground text-sm flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-primary" />
                Jejak Audit Sistem & Tata Kelola
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Rekaman perubahan status, pergantian runtime konfigurasi, dan verifikasi kepatuhan dari tabel audit_events.
              </p>
            </div>
          </div>

          <div className="border border-border rounded-xl bg-card overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/50 text-[10px] font-mono uppercase text-muted-foreground">
                    <th className="py-2.5 px-3">Waktu</th>
                    <th className="py-2.5 px-3">Aksi</th>
                    <th className="py-2.5 px-3">Aktor</th>
                    <th className="py-2.5 px-3">Entitas</th>
                    <th className="py-2.5 px-3">Alasan / Catatan Perubahan</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-xs">
                  {isAuditLoading ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-muted-foreground font-mono">
                        Memuat rekam jejak audit...
                      </td>
                    </tr>
                  ) : !auditEvents || auditEvents.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-muted-foreground font-mono">
                        Belum ada catatan audit sistem.
                      </td>
                    </tr>
                  ) : (
                    auditEvents.map((ev: any) => (
                      <tr key={ev.id} className="hover:bg-muted/30 transition">
                        <td className="py-2.5 px-3 whitespace-nowrap text-muted-foreground font-mono text-[11px]">
                          {ev.timestamp ? ev.timestamp.replace("T", " ").slice(0, 19) : "-"}
                        </td>
                        <td className="py-2.5 px-3 font-mono font-semibold text-[11px] text-foreground">
                          {ev.action}
                        </td>
                        <td className="py-2.5 px-3 text-foreground font-medium">
                          {ev.actor}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-muted-foreground text-[11px]">
                          {ev.entity_name} ({ev.entity_id ? String(ev.entity_id).slice(0, 8) : "-"}...)
                        </td>
                        <td className="py-2.5 px-3 text-muted-foreground">
                          {ev.reason || "-"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: SYSTEM KNOWLEDGE CHAT (NAVIGATION & SYSTEM ASSISTANT) */}
      {activeTab === "knowledge_chat" && (
        <SystemKnowledgeChatTab runtimeConfig={config} />
      )}
    </div>
  );
}
