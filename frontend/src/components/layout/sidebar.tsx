"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  apiClient,
  AuthUser,
  clearAuthSession,
  getCurrentRole,
  getCurrentUser,
} from "@/lib/api-client";
import { UserRole } from "@/types/package";
import {
  FolderKanban,
  FileSpreadsheet,
  CheckSquare,
  ShieldCheck,
  Archive,
  Cpu,
  Building2,
  Landmark,
  Users,
  LogOut,
  KeyRound,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sun,
  Moon,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [role, setRole] = useState<UserRole>("ADMINISTRATION");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">("light");

  // Password Change Modal state
  const [isPwdModalOpen, setIsPwdModalOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwdError, setPwdError] = useState("");
  const [pwdSuccess, setPwdSuccess] = useState("");
  const [isUpdatingPwd, setIsUpdatingPwd] = useState(false);

  useEffect(() => {
    const syncState = () => {
      setRole(getCurrentRole());
      setUser(getCurrentUser());
    };
    syncState();

    try {
      const isDark = document.documentElement.classList.contains("dark");
      setTheme(isDark ? "dark" : "light");
    } catch (e) {}

    window.addEventListener("pci_role_changed", syncState);
    window.addEventListener("pci_auth_changed", syncState);
    return () => {
      window.removeEventListener("pci_role_changed", syncState);
      window.removeEventListener("pci_auth_changed", syncState);
    };
  }, []);

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

  const handleLogout = () => {
    clearAuthSession();
    router.replace("/login");
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdError("");
    setPwdSuccess("");

    if (!currentPassword || !newPassword) {
      setPwdError("Lengkapi kata sandi saat ini dan kata sandi baru.");
      return;
    }
    if (newPassword.length < 6) {
      setPwdError("Kata sandi baru minimal 6 karakter.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwdError("Konfirmasi kata sandi baru tidak cocok.");
      return;
    }

    setIsUpdatingPwd(true);
    try {
      await apiClient.changePassword(currentPassword, newPassword);
      setPwdSuccess("Kata sandi berhasil diperbarui.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => {
        setIsPwdModalOpen(false);
        setPwdSuccess("");
      }, 1200);
    } catch (err: any) {
      setPwdError(err.message || "Gagal memperbarui kata sandi.");
    } finally {
      setIsUpdatingPwd(false);
    }
  };

  const navItems = [
    {
      name: "Paket Pengadaan",
      href: "/packages",
      icon: FolderKanban,
      roles: ["ADMINISTRATION", "LOGISTICS", "FINANCE_DIRECTOR", "SYSTEM_ADMINISTRATOR"],
    },
    {
      name: "Master Sekolah",
      href: "/schools",
      icon: Building2,
      roles: ["ADMINISTRATION", "FINANCE_DIRECTOR", "SYSTEM_ADMINISTRATOR"],
    },
    {
      name: "Master Rekanan",
      href: "/companies",
      icon: Landmark,
      roles: ["ADMINISTRATION", "FINANCE_DIRECTOR", "SYSTEM_ADMINISTRATOR"],
    },
    {
      name: "Impor Spreadsheet",
      href: "/imports",
      icon: FileSpreadsheet,
      roles: ["ADMINISTRATION", "SYSTEM_ADMINISTRATOR"],
    },
    {
      name: "Pemeriksaan Sistem",
      href: "/packages?tab=inspection",
      icon: CheckSquare,
      roles: ["ADMINISTRATION", "FINANCE_DIRECTOR", "SYSTEM_ADMINISTRATOR"],
    },
    {
      name: "Persetujuan Direktur",
      href: "/packages?filter=under_review",
      icon: ShieldCheck,
      badge: role === "FINANCE_DIRECTOR" ? "Review" : undefined,
      roles: ["FINANCE_DIRECTOR", "SYSTEM_ADMINISTRATOR"],
    },
    {
      name: "Arsip & Generator",
      href: "/packages?tab=documents",
      icon: Archive,
      roles: ["ADMINISTRATION", "FINANCE_DIRECTOR", "LOGISTICS", "SYSTEM_ADMINISTRATOR"],
    },
    {
      name: "AI & Audit Usage",
      href: "/ai/usage",
      icon: Cpu,
      roles: ["ADMINISTRATION", "FINANCE_DIRECTOR", "SYSTEM_ADMINISTRATOR"],
    },
    {
      name: "Manajemen Pengguna",
      href: "/users",
      icon: Users,
      badge: "Admin",
      roles: ["SYSTEM_ADMINISTRATOR"],
    },
  ];

  const roleBadgeClass =
    role === "FINANCE_DIRECTOR"
      ? "bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30"
      : role === "LOGISTICS"
      ? "bg-sky-500/15 text-sky-700 dark:text-sky-300 border border-sky-500/30"
      : role === "SYSTEM_ADMINISTRATOR"
      ? "bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-500/30"
      : "bg-primary/10 text-primary border border-primary/30";

  const roleShortLabel =
    role === "ADMINISTRATION"
      ? "ADMIN"
      : role === "FINANCE_DIRECTOR"
      ? "DIREKTUR"
      : role === "LOGISTICS"
      ? "LOGISTIK"
      : "SYSADMIN";

  return (
    <>
      <aside className="w-60 flex-shrink-0 flex flex-col justify-between border-r border-border bg-card select-none h-screen sticky top-0 shadow-sm">
        <div>
          {/* Brand Header with Pustaka Cemerlang Logo */}
          <div className="h-16 px-3.5 border-b border-border flex items-center gap-3 relative bg-card">
            {/* Top signature brand stripe (3px PCI Blue) */}
            <div className="absolute top-0 left-0 right-0 h-[3px] bg-primary" />

            <Link href="/packages" className="flex items-center gap-2.5 min-w-0 hover:opacity-95 transition group">
              <div className="w-9 h-9 rounded-lg bg-white border border-border flex items-center justify-center p-1 shadow-xs flex-shrink-0">
                <img
                  src="/images/pci-icon.png"
                  alt="CV Pustaka Cemerlang Indonesia"
                  className="w-full h-full object-contain"
                />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-bold text-foreground tracking-tight truncate group-hover:text-primary transition-colors">
                  Pustaka Cemerlang
                </span>
                <span className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase truncate">
                  Procurement &amp; SPJ
                </span>
              </div>
            </Link>
          </div>

          {/* Active Role Status Badge */}
          <div className="px-3.5 py-2 border-b border-border bg-muted/40">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono font-medium">
                Peran Aktif:
              </span>
              <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${roleBadgeClass}`}>
                {roleShortLabel}
              </span>
            </div>
          </div>

          {/* Navigation Menu */}
          <nav className="p-2.5 space-y-1">
            {navItems.map((item) => {
              const isAllowed = item.roles.includes(role);
              const baseHref = item.href.split("?")[0];
              const isActive =
                pathname === item.href ||
                (baseHref !== "/packages" && pathname.startsWith(baseHref)) ||
                (item.href === "/packages" && pathname === "/packages");

              if (!isAllowed) return null;

              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center justify-between px-3 py-2 text-xs rounded-md transition-all ${
                    isActive
                      ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/70"
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Icon
                      className={`w-3.5 h-3.5 flex-shrink-0 ${
                        isActive ? "text-primary-foreground" : "text-muted-foreground"
                      }`}
                    />
                    <span className="truncate">{item.name}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-bold ${
                        isActive
                          ? "bg-white/20 text-white"
                          : "bg-secondary text-secondary-foreground"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Authenticated User Footer */}
        <div className="border-t border-border bg-muted/30 p-3 space-y-2.5 text-xs">
          {user && (
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-7 h-7 rounded-full bg-primary/15 border border-primary/30 text-primary flex items-center justify-center font-bold text-xs flex-shrink-0">
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold text-foreground truncate">
                  {user.full_name}
                </div>
                <div className="text-[10px] font-mono text-muted-foreground truncate">
                  @{user.username}
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center gap-1.5 pt-0.5">
            <button
              type="button"
              onClick={toggleTheme}
              className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded border border-border bg-card hover:bg-muted text-foreground text-[11px] font-medium transition shadow-xs"
              title={theme === "dark" ? "Beralih ke Mode Terang (Resmi)" : "Beralih ke Mode Gelap"}
            >
              {theme === "dark" ? (
                <>
                  <Sun className="w-3.5 h-3.5 text-secondary" />
                  <span>Terang</span>
                </>
              ) : (
                <>
                  <Moon className="w-3.5 h-3.5 text-primary" />
                  <span>Gelap</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => {
                setPwdError("");
                setPwdSuccess("");
                setIsPwdModalOpen(true);
              }}
              className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded border border-border bg-card hover:bg-muted text-foreground text-[11px] font-medium transition shadow-xs"
              title="Ubah Kata Sandi"
            >
              <KeyRound className="w-3 h-3 text-muted-foreground" />
              <span>Sandi</span>
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center justify-center px-2.5 py-1.5 rounded border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-red-600 dark:text-red-300 text-[11px] font-semibold transition"
              title="Keluar dari Sistem"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Change Password Modal */}
      {isPwdModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 font-sans">
          <div className="bg-card border border-border w-full max-w-sm rounded-xl shadow-2xl overflow-hidden">
            <div className="px-4 py-3 border-b border-border bg-muted/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-primary" />
                <span className="text-xs font-bold uppercase font-mono text-foreground">
                  Ubah Kata Sandi Akun
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsPwdModalOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handlePasswordChange} className="p-4 space-y-3 text-xs">
              {pwdError && (
                <div className="p-2.5 rounded border border-destructive/40 bg-destructive/10 text-destructive flex items-center gap-2 font-mono text-[11px]">
                  <AlertCircle className="w-3.5 h-3.5 text-destructive flex-shrink-0" />
                  <span>{pwdError}</span>
                </div>
              )}
              {pwdSuccess && (
                <div className="p-2.5 rounded border border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-200 flex items-center gap-2 font-mono text-[11px]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                  <span>{pwdSuccess}</span>
                </div>
              )}

              <div className="space-y-1">
                <label className="block font-medium text-foreground">Kata Sandi Saat Ini</label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-border bg-background text-foreground font-mono text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="space-y-1">
                <label className="block font-medium text-foreground">Kata Sandi Baru (Min. 6 Karakter)</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-border bg-background text-foreground font-mono text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="space-y-1">
                <label className="block font-medium text-foreground">Konfirmasi Kata Sandi Baru</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-border bg-background text-foreground font-mono text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsPwdModalOpen(false)}
                  className="px-3 py-1.5 rounded border border-border bg-card hover:bg-muted text-muted-foreground text-xs"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isUpdatingPwd}
                  className="px-3 py-1.5 rounded bg-primary text-primary-foreground font-semibold text-xs hover:opacity-90 flex items-center gap-1.5 disabled:opacity-50 transition"
                >
                  {isUpdatingPwd && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Simpan Kata Sandi</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
