"use client";

import React, { useState, useEffect } from "react";
import { PackageRevision } from "@/types/package";
import { apiClient } from "@/lib/api-client";
import { formatDateIndo } from "@/lib/formatters";
import { AuditDiffPanel, downloadAuditCsv } from "@/components/audit/audit-diff-viewer";
import { History, ChevronRight, ChevronDown, Clock, Download, Search } from "lucide-react";

interface TabAuditProps {
  packageId: string;
  revision: PackageRevision;
}

export function TabAudit({ packageId, revision }: TabAuditProps) {
  const [events, setEvents] = useState<any[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [actionFilter, setActionFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    async function loadEvents() {
      setIsLoading(true);
      try {
        let data = await apiClient.getPackageAudit(packageId);
        if (!data || data.length === 0) {
          data = await apiClient.getAuditEvents({ entity_id: revision.id, limit: 100 });
        }
        setEvents(data || []);
      } catch {
        setEvents([]);
      } finally {
        setIsLoading(false);
      }
    }
    loadEvents();
  }, [packageId, revision.id]);

  const distinctActions = Array.from(new Set(events.map((e) => e.action).filter(Boolean)));
  const filteredEvents = events.filter((ev) => {
    if (actionFilter !== "ALL" && ev.action !== actionFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        (ev.reason || "").toLowerCase().includes(q) ||
        (ev.actor || "").toLowerCase().includes(q) ||
        (ev.action || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="p-6 max-w-5xl space-y-5 text-xs font-sans">
      <div className="flex flex-wrap items-center justify-between border-b border-border pb-3 gap-2">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-primary" />
          <h3 className="font-semibold text-foreground text-sm">
            Riwayat Jejak Audit &amp; Perubahan Status (Audit Trail)
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-muted-foreground uppercase">
            Permanen &amp; Tak Dapat Dihapus
          </span>
          {filteredEvents.length > 0 && (
            <button
              type="button"
              onClick={() => downloadAuditCsv(filteredEvents, `audit_paket_${packageId.slice(0, 8)}`)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-border bg-card hover:bg-muted text-foreground text-[11px] font-medium"
            >
              <Download className="w-3 h-3 text-primary" />
              <span>Unduh CSV (UC-09)</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      {events.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari aktor, catatan, aksi..."
              className="w-full pl-8 pr-2.5 py-1 bg-background border border-border rounded text-xs"
            />
          </div>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-2.5 py-1 bg-background border border-border rounded text-xs font-mono"
          >
            <option value="ALL">Semua Aksi ({events.length})</option>
            {distinctActions.map((act) => (
              <option key={act} value={act}>
                {act}
              </option>
            ))}
          </select>
        </div>
      )}

      {isLoading ? (
        <div className="p-8 text-center text-muted-foreground font-mono">
          Memuat riwayat jejak audit...
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="p-8 text-center text-muted-foreground font-mono">
          <Clock className="w-6 h-6 text-muted-foreground mx-auto mb-2 opacity-60" />
          <p className="text-xs">
            Belum ada jejak audit tercatat sesuai kriteria filter ini.
          </p>
        </div>
      ) : (
        <div className="border border-border rounded-lg bg-card overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-muted/40 border-b border-border text-[10px] uppercase font-mono font-semibold tracking-wider text-muted-foreground">
                <th className="px-3 py-2 w-44">Waktu (WIB)</th>
                <th className="px-3 py-2 w-32">Aksi / Peristiwa</th>
                <th className="px-3 py-2 w-36">Pengguna (Aktor)</th>
                <th className="px-3 py-2 min-w-[200px]">Alasan / Catatan</th>
                <th className="px-3 py-2 w-16 text-center">Diff</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 font-mono text-[11px]">
              {filteredEvents.map((ev, idx) => {
                const rowId = ev.id || String(idx);
                const isExpanded = expandedId === rowId || (expandedId === null && idx === 0 && Boolean(ev.before_state || ev.after_state));

                return (
                  <React.Fragment key={rowId}>
                    <tr className="hover:bg-muted/20 transition-colors">
                      <td className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                        {formatDateIndo(ev.timestamp)}
                      </td>
                      <td className="px-3 py-2 font-bold text-foreground whitespace-nowrap">
                        <span className="px-1.5 py-0.5 rounded bg-muted border border-border text-[10px]">
                          {ev.action}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-foreground whitespace-nowrap">
                        {ev.actor || "Sistem"}
                      </td>
                      <td className="px-3 py-2 font-sans text-muted-foreground">
                        {ev.reason || "-"}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {(ev.before_state || ev.after_state) && (
                          <button
                            type="button"
                            onClick={() => setExpandedId(expandedId === rowId ? "__NONE__" : rowId)}
                            className="p-1 text-muted-foreground hover:text-foreground rounded"
                            title="Tampilkan / Sembunyikan Before & After State"
                          >
                            {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                          </button>
                        )}
                      </td>
                    </tr>
                    {isExpanded && (ev.before_state || ev.after_state) && (
                      <tr>
                        <td colSpan={5} className="p-0">
                          <AuditDiffPanel beforeState={ev.before_state} afterState={ev.after_state} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
