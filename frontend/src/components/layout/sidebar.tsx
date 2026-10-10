"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getCurrentRole } from "@/lib/api-client";
import { UserRole } from "@/types/package";
import { RoleSwitcher } from "./role-switcher";
import {
  FolderKanban,
  FileSpreadsheet,
  CheckSquare,
  ShieldCheck,
  Archive,
  Cpu,
  Building2,
  Landmark,
  SlidersHorizontal,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const [role, setRole] = useState<UserRole>("ADMINISTRATION");

  useEffect(() => {
    setRole(getCurrentRole());
    const handleRoleChanged = () => setRole(getCurrentRole());
    window.addEventListener("pci_role_changed", handleRoleChanged);
    return () => window.removeEventListener("pci_role_changed", handleRoleChanged);
  }, []);

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
  ];

  return (
    <aside className="w-56 flex-shrink-0 flex flex-col justify-between border-r border-border bg-card select-none h-screen sticky top-0 shadow-sm">
      <div>
        {/* Brand Header */}
        <div className="h-12 px-3 border-b border-border flex items-center gap-2.5">
          <div className="w-6 h-6 rounded bg-primary text-primary-foreground flex items-center justify-center font-bold text-xs shadow-sm shadow-primary/20">
            PCI
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-xs font-semibold text-foreground tracking-tight truncate">PCI Procurement</span>
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
            <span
              className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                role === "FINANCE_DIRECTOR"
                  ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                  : role === "LOGISTICS"
                  ? "bg-blue-500/15 text-blue-300 border border-blue-500/30"
                  : role === "SYSTEM_ADMINISTRATOR"
                  ? "bg-red-500/15 text-red-300 border border-red-500/30"
                  : "bg-primary/15 text-primary border border-primary/30"
              }`}
            >
              {role === "ADMINISTRATION"
                ? "ADMIN"
                : role === "FINANCE_DIRECTOR"
                ? "DIREKTUR"
                : role === "LOGISTICS"
                ? "LOGISTIK"
                : "SYSADMIN"}
            </span>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="p-2 space-y-1">
          {navItems.map((item) => {
            const isAllowed = item.roles.includes(role);
            const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));

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
                  <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
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

      {/* Dev Role Switcher */}
      <RoleSwitcher />
    </aside>
  );
}
