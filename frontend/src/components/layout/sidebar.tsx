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
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [role, setRole] = useState<UserRole>("ADMINISTRATION");
  const [user, setUser] = useState<AuthUser | null>(null);

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
    window.addEventListener("pci_role_changed", syncState);
    window.addEventListener("pci_auth_changed", syncState);
    return () => {
      window.removeEventListener("pci_role_changed", syncState);
      window.removeEventListener("pci_auth_changed", syncState);
    };
  }, []);

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
      ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
      : role === "LOGISTICS"
      ? "bg-blue-500/15 text-blue-300 border border-blue-500/30"
      : role === "SYSTEM_ADMINISTRATOR"
      ? "bg-red-500/15 text-red-300 border border-red-500/30"
      : "bg-primary/15 text-primary border border-primary/30";

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
      <aside className="w-56 flex-shrink-0 flex flex-col justify-between border-r border-border bg-card select-none h-screen sticky top-0 shadow-sm">
        <div>
          {/* Brand Header */}
          <div className="h-12 px-3 border-b border-border flex items-center gap-2.5">
            <div className="w-6 h-6 rounded bg-primary text-primary-foreground flex items-center justify-center font-bold text-xs shadow-sm shadow-primary/20">
              PCI
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-semibold text-foreground tracking-tight truncate">
                PCI Procurement
              </span>
              <span className="text-[10px] text-muted-foreground font-mono truncate">
                CV Pustaka Cemerlang
              </span>
            </div>
          </div>

          {/* Active Role Status Badge */}
          <div className="px-3 py-2 border-b border-border bg-muted/30">
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
          <nav className="p-2 space-y-1">
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
                  className={`flex items-center justify-between px-2.5 py-2 text-xs rounded transition-all ${
                    isActive
                      ? "bg-primary/15 text-primary font-semibold border-l-2 border-primary shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Icon
                      className={`w-3.5 h-3.5 flex-shrink-0 ${
                        isActive ? "text-primary" : "text-muted-foreground"
                      }`}
                    />
                    <span className="truncate">{item.name}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Authenticated User Footer */}
        <div className="border-t border-border bg-muted/20 p-3 space-y-2.5 text-xs">
          {user && (
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-7 h-7 rounded-full bg-primary/20 border border-primary/40 text-primary flex items-center justify-center font-bold text-xs flex-shrink-0">
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold text-foreground truncate">
                  {user.full_name}
                </div>
                <div className="text-[10px] font-mono text-muted-foreground truncate">
                  @{user.username} • {user.email}
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-1.5 pt-0.5">
            <button
              type="button"
              onClick={() => {
                setPwdError("");
                setPwdSuccess("");
                setIsPwdModalOpen(true);
              }}
              className="flex items-center justify-center gap-1 px-2 py-1.5 rounded border border-border bg-background hover:bg-muted text-muted-foreground hover:text-foreground text-[11px] font-medium transition"
              title="Ubah Kata Sandi"
            >
              <KeyRound className="w-3 h-3" />
              <span>Ubah Sandi</span>
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center justify-center gap-1 px-2 py-1.5 rounded border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-red-300 text-[11px] font-semibold transition"
              title="Keluar dari Sistem"
            >
              <LogOut className="w-3 h-3" />
              <span>Keluar</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Change Password Modal */}
      {isPwdModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4 font-sans">
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
                <div className="p-2.5 rounded border border-red-500/40 bg-red-500/10 text-red-200 flex items-center gap-2 font-mono text-[11px]">
                  <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
                  <span>{pwdError}</span>
                </div>
              )}
              {pwdSuccess && (
                <div className="p-2.5 rounded border border-emerald-500/40 bg-emerald-500/10 text-emerald-200 flex items-center gap-2 font-mono text-[11px]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
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
                  className="px-3 py-1.5 rounded bg-primary text-primary-foreground font-semibold text-xs hover:opacity-90 flex items-center gap-1.5 disabled:opacity-50"
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
