"use client";

import { useEffect, useState } from "react";
import { UserRole } from "@/types/package";
import { getCurrentRole, setCurrentRole, getCurrentActorName, setCurrentActorName } from "@/lib/api-client";
import { Shield, UserCheck } from "lucide-react";

export function RoleSwitcher() {
  const [mounted, setMounted] = useState(false);
  const [role, setRole] = useState<UserRole>("ADMINISTRATION");
  const [actorName, setActorName] = useState<string>("Staf Administrasi");

  useEffect(() => {
    setMounted(true);
    setRole(getCurrentRole());
    setActorName(getCurrentActorName());

    const handleRoleChanged = () => {
      setRole(getCurrentRole());
      setActorName(getCurrentActorName());
    };
    window.addEventListener("pci_role_changed", handleRoleChanged);
    return () => window.removeEventListener("pci_role_changed", handleRoleChanged);
  }, []);

  // Strict Dev-Only Security Isolation (AT17 Protection)
  if (process.env.NODE_ENV !== "development") {
    return null;
  }

  if (!mounted) return null;

  const handleRoleChange = (newRole: UserRole) => {
    let name = "Staf Administrasi";
    if (newRole === "LOGISTICS") name = "Petugas Logistik";
    if (newRole === "FINANCE_DIRECTOR") name = "Direktur Keuangan";
    if (newRole === "SYSTEM_ADMINISTRATOR") name = "Administrator Sistem";

    setRole(newRole);
    setActorName(name);
    setCurrentRole(newRole);
    setCurrentActorName(name);
  };

  return (
    <div className="border-t border-border/80 bg-muted/20 px-3 py-2 text-xs">
      <div className="flex items-center justify-between gap-1 mb-1.5 text-muted-foreground">
        <span className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-amber-400">
          <Shield className="w-3 h-3" /> Dev RBAC Sim
        </span>
        <span className="text-[10px] truncate font-mono text-muted-foreground">{actorName}</span>
      </div>
      <div className="grid grid-cols-2 gap-1 font-mono">
        <button
          type="button"
          onClick={() => handleRoleChange("ADMINISTRATION")}
          className={`px-1.5 py-0.5 text-[10px] rounded text-left transition ${
            role === "ADMINISTRATION"
              ? "bg-primary text-primary-foreground font-semibold"
              : "bg-muted/40 hover:bg-muted text-muted-foreground"
          }`}
        >
          ADMIN
        </button>
        <button
          type="button"
          onClick={() => handleRoleChange("LOGISTICS")}
          className={`px-1.5 py-0.5 text-[10px] rounded text-left transition ${
            role === "LOGISTICS"
              ? "bg-primary text-primary-foreground font-semibold"
              : "bg-muted/40 hover:bg-muted text-muted-foreground"
          }`}
        >
          LOGISTIK
        </button>
        <button
          type="button"
          onClick={() => handleRoleChange("FINANCE_DIRECTOR")}
          className={`px-1.5 py-0.5 text-[10px] rounded text-left transition ${
            role === "FINANCE_DIRECTOR"
              ? "bg-amber-500 text-black font-semibold"
              : "bg-muted/40 hover:bg-muted text-muted-foreground"
          }`}
        >
          DIREKTUR
        </button>
        <button
          type="button"
          onClick={() => handleRoleChange("SYSTEM_ADMINISTRATOR")}
          className={`px-1.5 py-0.5 text-[10px] rounded text-left transition ${
            role === "SYSTEM_ADMINISTRATOR"
              ? "bg-red-500 text-white font-semibold"
              : "bg-muted/40 hover:bg-muted text-muted-foreground"
          }`}
        >
          SYSADMIN
        </button>
      </div>
    </div>
  );
}
