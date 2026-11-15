"use client";

import React from "react";

interface AuditDiffPanelProps {
  beforeState?: Record<string, any> | null;
  afterState?: Record<string, any> | null;
}

/**
 * Shared side-by-side Before/After state diff viewer for UC-09 & FR-09.
 */
export function AuditDiffPanel({ beforeState, afterState }: AuditDiffPanelProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 bg-muted/30 border-t border-border/60 text-[11px] font-mono">
      <div className="border border-border rounded bg-background/70 p-2.5 space-y-1">
        <div className="text-[10px] uppercase font-bold text-amber-400 tracking-wider">
          Nilai Sebelum (Before State)
        </div>
        {beforeState && Object.keys(beforeState).length > 0 ? (
          <pre className="whitespace-pre-wrap break-all text-muted-foreground leading-relaxed max-h-56 overflow-y-auto">
            {JSON.stringify(beforeState, null, 2)}
          </pre>
        ) : (
          <span className="text-muted-foreground/70 italic">(Tidak ada state sebelumnya / entitas baru)</span>
        )}
      </div>

      <div className="border border-border rounded bg-background/70 p-2.5 space-y-1">
        <div className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider">
          Nilai Sesudah (After State)
        </div>
        {afterState && Object.keys(afterState).length > 0 ? (
          <pre className="whitespace-pre-wrap break-all text-foreground leading-relaxed max-h-56 overflow-y-auto">
            {JSON.stringify(afterState, null, 2)}
          </pre>
        ) : (
          <span className="text-muted-foreground/70 italic">(Tidak ada perubahan tercatat / dihapus)</span>
        )}
      </div>
    </div>
  );
}

function escapeCsvCell(value: any): string {
  const s = value == null ? "" : String(value);
  return `"${s.replace(/"/g, '""')}"`;
}

export function downloadAuditCsv(events: any[], filenamePrefix = "audit_trail_pci"): void {
  const headers = ["Timestamp", "Entitas", "ID Entitas", "Aksi", "Aktor", "Alasan", "Before State", "After State"];
  const rows = events.map((ev) => [
    ev.timestamp || "",
    ev.entity_name || "",
    ev.entity_id || "",
    ev.action || "",
    ev.actor || "",
    ev.reason || "",
    ev.before_state ? JSON.stringify(ev.before_state) : "",
    ev.after_state ? JSON.stringify(ev.after_state) : "",
  ]);
  const csv = [headers.map(escapeCsvCell).join(","), ...rows.map((r) => r.map(escapeCsvCell).join(","))].join("\r\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filenamePrefix}_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function downloadAuditJson(events: any[], filenamePrefix = "audit_trail_pci"): void {
  const blob = new Blob([JSON.stringify(events, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filenamePrefix}_${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
