"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  apiClient,
  AuthUser,
  clearAuthSession,
  getAuthToken,
  getCurrentUser,
  setAuthSession,
} from "@/lib/api-client";
import { UserRole } from "@/types/package";
import { ShieldAlert, Loader2, ArrowLeft } from "lucide-react";

const ROUTE_ROLE_MATRIX: Array<{ prefix: string; roles: UserRole[] }> = [
  {
    prefix: "/users",
    roles: ["SYSTEM_ADMINISTRATOR"],
  },
  {
    prefix: "/imports",
    roles: ["ADMINISTRATION", "SYSTEM_ADMINISTRATOR"],
  },
  {
    prefix: "/schools",
    roles: ["ADMINISTRATION", "FINANCE_DIRECTOR", "SYSTEM_ADMINISTRATOR"],
  },
  {
    prefix: "/companies",
    roles: ["ADMINISTRATION", "FINANCE_DIRECTOR", "SYSTEM_ADMINISTRATOR"],
  },
  {
    prefix: "/ai/usage",
    roles: ["ADMINISTRATION", "FINANCE_DIRECTOR", "SYSTEM_ADMINISTRATOR"],
  },
  {
    prefix: "/packages",
    roles: ["ADMINISTRATION", "LOGISTICS", "FINANCE_DIRECTOR", "SYSTEM_ADMINISTRATOR"],
  },
];

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let active = true;

    async function verifyAuth() {
      const token = getAuthToken();
      if (!token) {
        router.replace("/login");
        return;
      }

      const cached = getCurrentUser();
      if (cached && active) {
        setUser(cached);
        setChecking(false);
      }

      try {
        const freshUser = await apiClient.getMe();
        if (active) {
          setAuthSession(token, freshUser);
          setUser(freshUser);
          setChecking(false);
        }
      } catch {
        if (active) {
          clearAuthSession();
          router.replace("/login");
        }
      }
    }

    verifyAuth();

    const handleAuthChange = () => {
      const current = getCurrentUser();
      setUser(current);
      if (!getAuthToken()) {
        router.replace("/login");
      }
    };

    window.addEventListener("pci_auth_changed", handleAuthChange);
    return () => {
      active = false;
      window.removeEventListener("pci_auth_changed", handleAuthChange);
    };
  }, [router]);

  if (checking) {
    return (
      <div className="flex-1 min-h-screen flex flex-col items-center justify-center bg-background text-muted-foreground gap-2 font-mono text-xs">
        <Loader2 className="w-5 h-5 animate-spin text-primary" />
        <span>Memverifikasi sesi &amp; hak akses RBAC...</span>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  // Check route-level RBAC permission
  const matchedRule = ROUTE_ROLE_MATRIX.find((r) => pathname.startsWith(r.prefix));
  if (matchedRule && !matchedRule.roles.includes(user.role)) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center font-sans">
        <div className="max-w-md border border-red-500/30 bg-red-500/10 rounded-xl p-6 space-y-4">
          <div className="w-10 h-10 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center mx-auto">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <h2 className="text-sm font-bold text-foreground uppercase font-mono">
              403 • Akses Ditolak (RBAC)
            </h2>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Akun Anda (<span className="text-foreground font-semibold">{user.full_name}</span>) memiliki peran{" "}
              <span className="font-mono text-red-300 font-semibold">{user.role}</span> yang tidak diizinkan mengakses halaman{" "}
              <code className="font-mono text-foreground">{pathname}</code>.
            </p>
          </div>
          <button
            type="button"
            onClick={() => router.push("/packages")}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Kembali ke Paket Pengadaan</span>
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

