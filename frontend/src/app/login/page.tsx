"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiClient, getAuthToken, setAuthSession } from "@/lib/api-client";
import {
  ShieldCheck,
  Lock,
  User,
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
  KeyRound,
  ArrowRight,
  Sun,
  Moon,
} from "lucide-react";

const DEMO_ACCOUNTS = [
  {
    username: "sysadmin",
    label: "System Admin",
    roleBadge: "SYSADMIN",
    desc: "Akses penuh & Manajemen Pengguna",
    color: "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300 hover:bg-rose-500/20",
  },
  {
    username: "admin",
    label: "Staf Administrasi",
    roleBadge: "ADMIN",
    desc: "Impor Excel, Paket, Master & Dokumen",
    color: "border-primary/30 bg-primary/10 text-primary hover:bg-primary/20",
  },
  {
    username: "direktur",
    label: "Direktur Keuangan",
    roleBadge: "DIREKTUR",
    desc: "Review, Persetujuan & Penerbitan SPJ",
    color: "border-secondary/40 bg-secondary/10 text-secondary hover:bg-secondary/20",
  },
  {
    username: "logistik",
    label: "Petugas Logistik",
    roleBadge: "LOGISTIK",
    desc: "Pengiriman, Pemeriksaan & Bukti BAST",
    color: "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300 hover:bg-sky-500/20",
  },
];

export default function LoginPage() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      router.replace("/packages");
    }
    try {
      const isDark = document.documentElement.classList.contains("dark");
      setTheme(isDark ? "dark" : "light");
    } catch (e) {}
  }, [router]);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    try {
      localStorage.setItem("pci_theme", nextTheme);
      if (nextTheme === "dark") {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
    } catch (e) {}
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!identifier.trim() || !password) {
      setError("Masukkan username/email dan kata sandi Anda.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await apiClient.login(identifier.trim(), password);
      setAuthSession(res.access_token, res.user);
      router.replace("/packages");
    } catch (err: any) {
      setError(err.message || "Gagal masuk. Periksa kembali kredensial Anda.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = (username: string) => {
    setIdentifier(username);
    setPassword("Admin123!");
    setError("");
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col justify-center items-center p-4 font-sans relative overflow-hidden">
      {/* Top Brand Accent Bar (PCI Blue & Orange Gradient Stripe) */}
      <div className="fixed top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary via-primary/80 to-secondary z-50" />

      {/* Theme Toggle Top Right */}
      <div className="absolute top-4 right-4 z-20">
        <button
          type="button"
          onClick={toggleTheme}
          className="p-2 rounded-lg border border-border bg-card/80 hover:bg-muted text-foreground transition shadow-xs flex items-center gap-1.5 text-xs"
          title={theme === "dark" ? "Beralih ke Mode Terang (Sesuai Website)" : "Beralih ke Mode Gelap"}
        >
          {theme === "dark" ? (
            <>
              <Sun className="w-4 h-4 text-secondary" />
              <span className="text-[11px] font-medium hidden sm:inline">Mode Terang</span>
            </>
          ) : (
            <>
              <Moon className="w-4 h-4 text-primary" />
              <span className="text-[11px] font-medium hidden sm:inline">Mode Gelap</span>
            </>
          )}
        </button>
      </div>

      <div className="w-full max-w-md space-y-5 z-10">
        {/* Brand Header with Extracted Official Logo */}
        <div className="flex flex-col items-center text-center space-y-3">
          <div className="p-3 px-5 rounded-2xl bg-white dark:bg-card border border-border shadow-md flex items-center justify-center">
            <img
              src="/images/pci-logo.png"
              alt="CV Pustaka Cemerlang"
              className="h-12 w-auto object-contain dark:hidden"
            />
            <img
              src="/images/pci-logo-white.png"
              alt="CV Pustaka Cemerlang"
              className="h-12 w-auto object-contain hidden dark:block"
            />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              PCI Procurement &amp; SPJ System
            </h1>
            <p className="text-xs text-muted-foreground font-sans mt-0.5">
              CV Pustaka Cemerlang Indonesia &bull; Sistem Otomasi Pengadaan &amp; Dokumen SPJ
            </p>
          </div>
        </div>

        {/* Login Card */}
        <div className="border border-border rounded-xl bg-card shadow-lg overflow-hidden">
          <div className="px-5 py-3.5 border-b border-border bg-muted/40 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-primary" />
              <span className="text-xs font-bold uppercase tracking-wider font-mono text-foreground">
                Autentikasi Pengguna (RBAC)
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/30 font-semibold">
              INTERNAL ONLY
            </span>
          </div>

          <form onSubmit={handleSubmit} className="p-5 space-y-4">
            {error && (
              <div className="p-3 rounded-lg border border-destructive/40 bg-destructive/10 text-destructive text-xs flex items-start gap-2 font-mono">
                <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-foreground">
                Username atau Email
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="contoh: sysadmin atau admin@pci.co.id"
                  autoComplete="username"
                  className="w-full pl-9 pr-3 py-2 bg-background border border-border rounded-lg text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono transition"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-foreground">
                Kata Sandi
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Masukkan kata sandi akun"
                  autoComplete="current-password"
                  className="w-full pl-9 pr-9 py-2 bg-background border border-border rounded-lg text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 rounded-lg bg-primary text-primary-foreground font-semibold text-xs hover:opacity-95 transition flex items-center justify-center gap-2 shadow-md shadow-primary/20 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Memverifikasi Kredensial...</span>
                </>
              ) : (
                <>
                  <span>Masuk ke Sistem</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>

            <div className="pt-2 border-t border-border/60 text-[11px] text-muted-foreground text-center leading-relaxed">
              Pendaftaran mandiri dinonaktifkan demi keamanan. Penambahan akun dan pengaturan hak akses (RBAC) hanya dapat dilakukan oleh{" "}
              <span className="text-foreground font-semibold">Administrator Sistem</span>.
            </div>
          </form>
        </div>

        {/* Quick Fill Role Accounts Card */}
        <div className="border border-border/80 rounded-xl bg-card p-4 space-y-2.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-1.5 font-semibold">
              <KeyRound className="w-3.5 h-3.5 text-secondary" />
              Akun Bawaan per Peran RBAC (Klik untuk isi cepat)
            </span>
            <span className="text-[10px] font-mono text-muted-foreground">
              Sandi: <code className="text-foreground font-bold">Admin123!</code>
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.username}
                type="button"
                onClick={() => handleQuickFill(acc.username)}
                className={`p-2.5 rounded-lg border text-left transition flex flex-col justify-between gap-1 shadow-2xs hover:shadow-xs ${acc.color}`}
              >
                <div className="flex items-center justify-between w-full">
                  <span className="font-mono font-bold text-[11px]">@{acc.username}</span>
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-black/10 dark:bg-black/30 font-bold">
                    {acc.roleBadge}
                  </span>
                </div>
                <span className="text-[10px] opacity-90 font-sans leading-tight">
                  {acc.desc}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
