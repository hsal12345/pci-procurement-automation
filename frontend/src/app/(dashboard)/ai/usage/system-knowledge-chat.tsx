"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import {
  SystemKnowledgeChatMessage,
  SystemKnowledgeInfoResponse,
  AIRuntimeConfig,
} from "@/types/ai";
import {
  Bot,
  User,
  Send,
  Compass,
  ArrowRight,
  BookOpen,
  FileText,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  HelpCircle,
  ShieldCheck,
  Loader2,
  HardDrive,
  Cloud,
} from "lucide-react";

interface SystemKnowledgeChatTabProps {
  runtimeConfig?: AIRuntimeConfig;
}

const STARTER_PROMPTS = [
  {
    icon: "🧭",
    label: "Panduan Navigasi Menu",
    prompt: "Tolong jelaskan seluruh menu dan rute navigasi yang tersedia di sistem ini.",
  },
  {
    icon: "📦",
    label: "Langkah Buat Paket",
    prompt: "Bagaimana langkah demi langkah membuat paket pengadaan baru dari nol?",
  },
  {
    icon: "📥",
    label: "Cara Impor Excel KK09",
    prompt: "Bagaimana cara mengimpor berkas Excel transaksi pengadaan (seperti 4 PCI KK09.xlsx)?",
  },
  {
    icon: "🛡️",
    label: "Alur Approval Direktur",
    prompt: "Bagaimana alur persetujuan atau pengembalian dokumen oleh Direktur Keuangan?",
  },
  {
    icon: "📄",
    label: "13 Dokumen SPJ (D01-D13)",
    prompt: "Jelaskan fungsi dari 13 dokumen SPJ dari D01 sampai D13 dan urutan kronologinya.",
  },
  {
    icon: "👥",
    label: "Peran Pengguna (RBAC)",
    prompt: "Apa perbedaan peran dan wewenang Staf Administrasi, Logistik, Direktur Keuangan, dan Sysadmin?",
  },
];

export function SystemKnowledgeChatTab({ runtimeConfig }: SystemKnowledgeChatTabProps) {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Query system knowledge file metadata and full text
  const { data: knowledgeInfo, isLoading: isKnowledgeLoading } = useQuery<SystemKnowledgeInfoResponse>({
    queryKey: ["system_knowledge_info"],
    queryFn: () => apiClient.getSystemKnowledgeInfo(),
    staleTime: 60 * 1000,
  });

  const [messages, setMessages] = useState<SystemKnowledgeChatMessage[]>([
    {
      role: "assistant",
      content:
        "### 👋 Selamat Datang di System Knowledge Chat\n\n" +
        "Saya adalah **Asisten Pengetahuan & Panduan Navigasi Resmi** untuk **Sistem Otomasi Pengadaan & SPJ CV Pustaka Cemerlang Indonesia**.\n\n" +
        "Saya telah memuat konteks penuh dari berkas **`system_knowledge.md`** dan siap membantu Anda:\n" +
        "- 🧭 **Navigasi Sistem**: Menjelaskan rute menu, tombol, dan tab di aplikasi.\n" +
        "- 📋 **Alur Kerja SPJ**: Tata cara pembuatan paket, impor Excel, dan ekspor 13 dokumen (D01-D13).\n" +
        "- ⚖️ **Aturan Bisnis**: Penjelasan validasi (BR01-BR15), kronologi tanggal, dan kalkulasi pajak.\n" +
        "- 🛡️ **Persetujuan Direktur**: Panduan approval atau return bagi Direktur Keuangan.\n\n" +
        "> *Catatan: Asisten ini khusus melayani pertanyaan seputar sistem ini dan panduan navigasi operasional.*",
      suggested_routes: [
        {
          title: "Paket Pengadaan",
          path: "/packages",
          description: "Pusat transaksi pengadaan barang dan pembuatan draf",
        },
        {
          title: "Impor Spreadsheet",
          path: "/imports",
          description: "Unggah berkas Excel dan pratinjau pemetaan kolom",
        },
        {
          title: "Master Sekolah",
          path: "/schools",
          description: "Pengelolaan data SD dan pejabat penandatangan",
        },
      ],
      suggested_questions: [
        "Bagaimana cara membuat paket pengadaan baru?",
        "Bagaimana cara mengimpor berkas Excel transaksi?",
        "Apa fungsi 13 dokumen SPJ dari D01 sampai D13?",
        "Bagaimana alur persetujuan Direktur Keuangan?",
      ],
    },
  ]);

  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [showMarkdownViewer, setShowMarkdownViewer] = useState(false);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || isSending) return;

    setInput("");
    const userMsg: SystemKnowledgeChatMessage = {
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsSending(true);

    try {
      const historyPayload = messages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await apiClient.sendSystemKnowledgeChat({
        message: query,
        history: historyPayload,
      });

      const assistantMsg: SystemKnowledgeChatMessage = {
        role: "assistant",
        content: res.reply,
        suggested_routes: res.suggested_routes,
        suggested_questions: res.suggested_questions,
        timestamp: new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: SystemKnowledgeChatMessage = {
        role: "assistant",
        content:
          "⚠️ **Gagal menghubungi layanan asisten**: " +
          (err?.message || "Terjadi kesalahan saat memproses respon pengetahuan sistem. Silakan coba kembali."),
        suggested_routes: [
          {
            title: "Paket Pengadaan",
            path: "/packages",
            description: "Kembali ke daftar paket pengadaan",
          },
        ],
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSending(false);
    }
  };

  const handleClearChat = () => {
    setMessages([
      {
        role: "assistant",
        content:
          "### 🔄 Percakapan Telah Direset\n\n" +
          "Silakan ajukan pertanyaan baru mengenai navigasi menu, alur pembuatan paket, impor Excel, atau aturan dokumen SPJ CV Pustaka Cemerlang Indonesia.",
        suggested_routes: [
          {
            title: "Paket Pengadaan",
            path: "/packages",
            description: "Daftar transaksi pengadaan aktif",
          },
        ],
        suggested_questions: [
          "Bagaimana langkah demi langkah membuat paket baru?",
          "Di mana letak menu untuk mengimpor berkas Excel?",
        ],
      },
    ]);
  };

  const activeMode = runtimeConfig?.runtime_mode || "local";
  const activeProvider = runtimeConfig?.provider || "mock";
  const activeModel = runtimeConfig?.model || "mock-rule-engine";

  return (
    <div className="space-y-4">
      {/* Top Knowledge Context & Status Bar */}
      <div className="border border-border rounded-xl bg-card p-4 shadow-sm space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-foreground">
                  System Knowlage Chat &amp; Navigation Assistant
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Konteks Aktif
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Asisten kecerdasan buatan khusus panduan navigasi dan pemahaman sistem berbasis berkas pengetahuan Markdown resmi.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Active Runtime Badge */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border bg-muted/40 text-[11px] font-mono">
              {activeMode === "api" ? (
                <Cloud className="w-3.5 h-3.5 text-emerald-500" />
              ) : (
                <HardDrive className="w-3.5 h-3.5 text-sky-500" />
              )}
              <span className="font-semibold">{activeProvider.toUpperCase()}</span>
              <span className="text-muted-foreground text-[10px]">({activeModel})</span>
            </div>

            {/* Toggle Knowledge File Viewer */}
            <button
              type="button"
              onClick={() => setShowMarkdownViewer(!showMarkdownViewer)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-md border border-border hover:bg-muted font-medium text-[11px] text-foreground transition"
              title="Lihat teks berkas system_knowledge.md yang dimuat oleh LLM"
            >
              <FileText className="w-3.5 h-3.5 text-primary" />
              <span>{showMarkdownViewer ? "Tutup Dokumen .md" : "Lihat Dokumen .md"}</span>
              {showMarkdownViewer ? (
                <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
              )}
            </button>

            {/* Clear Chat Button */}
            <button
              type="button"
              onClick={handleClearChat}
              className="p-1.5 text-muted-foreground hover:text-foreground rounded-md border border-border hover:bg-muted"
              title="Bersihkan Percakapan"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Collapsible System Knowledge .md Document Viewer */}
        {showMarkdownViewer && (
          <div className="border border-border/80 rounded-lg bg-muted/20 p-3 space-y-2 text-xs animate-in fade-in-50 duration-200">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <div className="flex items-center gap-2 text-[11px] font-mono text-foreground font-semibold">
                <BookOpen className="w-4 h-4 text-primary" />
                <span>Konteks Dimuat: {knowledgeInfo?.filename || "system_knowledge.md"}</span>
                <span className="text-muted-foreground font-normal">
                  ({knowledgeInfo?.size_bytes ? (knowledgeInfo.size_bytes / 1024).toFixed(1) : "22.1"} KB •{" "}
                  {knowledgeInfo?.sections?.length || 9} Seksi Topik)
                </span>
              </div>
              <span className="text-[10px] text-muted-foreground font-mono">
                Terakhir Diperbarui:{" "}
                {knowledgeInfo?.last_updated ? knowledgeInfo.last_updated.replace("T", " ").slice(0, 19) : "Baru saja"}
              </span>
            </div>

            {/* Section Badges */}
            {knowledgeInfo?.sections && knowledgeInfo.sections.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap py-1">
                <span className="text-[10px] font-mono text-muted-foreground uppercase">Topik Pengetahuan:</span>
                {knowledgeInfo.sections.map((sec, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 rounded text-[10px] bg-background border border-border text-foreground font-medium truncate max-w-[260px]"
                    title={sec}
                  >
                    {sec}
                  </span>
                ))}
              </div>
            )}

            {/* Raw Markdown Text Display */}
            <div className="relative">
              <pre className="max-h-60 overflow-y-auto p-3 rounded bg-card border border-border font-mono text-[10px] leading-relaxed text-foreground whitespace-pre-wrap select-text">
                {isKnowledgeLoading ? "Memuat berkas konteks pengetahuan..." : knowledgeInfo?.content}
              </pre>
            </div>
            <p className="text-[10px] text-muted-foreground italic">
              ℹ️ Teks di atas adalah basis pengetahuan yang disuntikkan secara dinamis ke prompt LLM agar seluruh jawaban akurat terhadap sistem PCI.
            </p>
          </div>
        )}

        {/* Quick Starter Question Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-1 scrollbar-none">
          <span className="text-[10px] font-mono text-muted-foreground uppercase flex-shrink-0">
            Panduan Kilat:
          </span>
          {STARTER_PROMPTS.map((starter, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSendMessage(starter.prompt)}
              disabled={isSending}
              className="flex-shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-full border border-border bg-background hover:bg-muted text-[11px] font-medium text-foreground transition hover:border-primary/50 disabled:opacity-50"
            >
              <span>{starter.icon}</span>
              <span>{starter.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Thread Display */}
      <div className="border border-border rounded-xl bg-card shadow-sm flex flex-col h-[560px] overflow-hidden">
        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
          {messages.map((msg, index) => {
            const isUser = msg.role === "user";

            return (
              <div
                key={index}
                className={`flex gap-3 max-w-[92%] sm:max-w-[85%] ${
                  isUser ? "ml-auto flex-row-reverse" : "mr-auto"
                }`}
              >
                {/* Avatar */}
                <div
                  className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs shadow-xs ${
                    isUser
                      ? "bg-primary text-primary-foreground font-semibold"
                      : "bg-primary/10 text-primary border border-primary/20"
                  }`}
                >
                  {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-4 h-4" />}
                </div>

                {/* Message Bubble */}
                <div className="space-y-2">
                  <div
                    className={`p-3.5 rounded-xl border leading-relaxed ${
                      isUser
                        ? "bg-primary text-primary-foreground border-primary rounded-tr-xs"
                        : "bg-muted/30 border-border text-foreground rounded-tl-xs"
                    }`}
                  >
                    {/* Message Text with Simple Markdown Formatting */}
                    <div className="space-y-2">
                      {msg.content.split("\n\n").map((para, pIdx) => {
                        const trimmed = para.trim();
                        if (!trimmed) return null;

                        // Markdown Headings
                        if (trimmed.startsWith("### ")) {
                          return (
                            <h4
                              key={pIdx}
                              className={`font-bold text-xs mt-2 mb-1 ${
                                isUser ? "text-primary-foreground" : "text-foreground"
                              }`}
                            >
                              {trimmed.replace("### ", "")}
                            </h4>
                          );
                        }
                        if (trimmed.startsWith("## ")) {
                          return (
                            <h3
                              key={pIdx}
                              className={`font-bold text-sm mt-2 mb-1 ${
                                isUser ? "text-primary-foreground" : "text-foreground"
                              }`}
                            >
                              {trimmed.replace("## ", "")}
                            </h3>
                          );
                        }

                        // Blockquotes
                        if (trimmed.startsWith("> ")) {
                          return (
                            <div
                              key={pIdx}
                              className={`p-2 rounded border-l-2 text-[11px] italic my-1 ${
                                isUser
                                  ? "border-primary-foreground/40 bg-primary-foreground/10"
                                  : "border-primary bg-primary/5 text-muted-foreground"
                              }`}
                            >
                              {trimmed.replace(/^>\s*/, "")}
                            </div>
                          );
                        }

                        // Bullet list
                        if (trimmed.includes("\n- ") || trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
                          const lines = trimmed.split("\n");
                          return (
                            <ul key={pIdx} className="space-y-1 list-disc list-inside text-[11px] my-1">
                              {lines.map((line, lIdx) => {
                                const clean = line.replace(/^[\s*-]+/, "").trim();
                                if (!clean) return null;
                                return (
                                  <li key={lIdx} dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(clean) }} />
                                );
                              })}
                            </ul>
                          );
                        }

                        // Numbered list
                        if (/^\d+\.\s/.test(trimmed)) {
                          const lines = trimmed.split("\n");
                          return (
                            <ol key={pIdx} className="space-y-1 list-decimal list-inside text-[11px] my-1">
                              {lines.map((line, lIdx) => {
                                const clean = line.replace(/^\d+\.\s*/, "").trim();
                                if (!clean) return null;
                                return (
                                  <li key={lIdx} dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(clean) }} />
                                );
                              })}
                            </ol>
                          );
                        }

                        // Normal paragraph
                        return (
                          <p
                            key={pIdx}
                            className="text-[11px]"
                            dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(trimmed) }}
                          />
                        );
                      })}
                    </div>

                    {msg.timestamp && (
                      <div
                        className={`text-[9px] font-mono mt-1 text-right ${
                          isUser ? "text-primary-foreground/70" : "text-muted-foreground"
                        }`}
                      >
                        {msg.timestamp}
                      </div>
                    )}
                  </div>

                  {/* Suggested Navigation Route Cards */}
                  {!isUser && msg.suggested_routes && msg.suggested_routes.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-semibold">
                        <Compass className="w-3 h-3 text-primary" />
                        <span>Rekomendasi Rute Navigasi:</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {msg.suggested_routes.map((route, rIdx) => (
                          <div
                            key={rIdx}
                            onClick={() => router.push(route.path)}
                            className="p-2.5 rounded-lg border border-border bg-card hover:border-primary/60 hover:bg-muted/30 cursor-pointer transition group shadow-2xs"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-foreground text-[11px] group-hover:text-primary transition-colors flex items-center gap-1">
                                {route.title}
                              </span>
                              <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                                {route.path}
                              </span>
                            </div>
                            {route.description && (
                              <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">
                                {route.description}
                              </p>
                            )}
                            <div className="flex items-center gap-1 text-[10px] text-primary font-medium mt-1">
                              <span>Buka Menu</span>
                              <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Suggested Questions Pills */}
                  {!isUser && msg.suggested_questions && msg.suggested_questions.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap pt-1">
                      <span className="text-[10px] font-mono text-muted-foreground uppercase flex items-center gap-1">
                        <HelpCircle className="w-3 h-3 text-amber-500" />
                        Pertanyaan Lanjutan:
                      </span>
                      {msg.suggested_questions.map((q, qIdx) => (
                        <button
                          key={qIdx}
                          type="button"
                          onClick={() => handleSendMessage(q)}
                          disabled={isSending}
                          className="px-2.5 py-1 rounded-md text-[10px] border border-border bg-background hover:bg-muted text-foreground font-medium transition hover:border-primary/50 text-left disabled:opacity-50"
                        >
                          💬 {q}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Loading Indicator */}
          {isSending && (
            <div className="flex gap-3 max-w-[80%] mr-auto">
              <div className="w-7 h-7 rounded-full bg-primary/10 text-primary border border-primary/20 flex-shrink-0 flex items-center justify-center">
                <Bot className="w-4 h-4 animate-bounce" />
              </div>
              <div className="p-3.5 rounded-xl border border-border bg-muted/30 text-foreground text-xs flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                <span className="text-[11px] text-muted-foreground font-medium">
                  Memeriksa dokumen pengetahuan sistem dan merumuskan panduan navigasi...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input Bar */}
        <div className="p-3 border-t border-border bg-background/80 space-y-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Tanyakan navigasi menu, cara buat paket, impor Excel, atau alur persetujuan..."
                disabled={isSending}
                className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
              />
            </div>
            <button
              type="submit"
              disabled={isSending || !input.trim()}
              className="px-4 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-xs flex items-center gap-1.5 hover:opacity-90 transition disabled:opacity-50 shadow-xs flex-shrink-0"
            >
              {isSending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              <span>Kirim</span>
            </button>
          </form>

          {/* Guardrail Disclaimer */}
          <div className="flex items-center justify-between text-[10px] text-muted-foreground px-1">
            <span className="flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-emerald-500" />
              Asisten terikat batasan ketat: hanya menjawab panduan navigasi &amp; sistem CV Pustaka Cemerlang Indonesia.
            </span>
            <span className="font-mono">PRD FR05 &amp; Seksi 11</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Utility to format bold, inline code, and URLs safely into HTML
function formatInlineMarkdown(text: string): string {
  const formatted = text
    // Escape angle brackets
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    // Bold: **text**
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    // Italics: *text*
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    // Inline code: `text`
    .replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded bg-muted/60 font-mono text-[10px] border border-border/50 text-foreground">$1</code>');

  return formatted;
}
