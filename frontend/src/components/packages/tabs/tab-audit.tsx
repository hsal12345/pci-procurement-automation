"use client";

import { useState, useEffect } from "react";
import { PackageRevision } from "@/types/package";
import { apiClient } from "@/lib/api-client";
import { formatDateIndo } from "@/lib/formatters";
import { History, ChevronRight, ChevronDown, UserCheck, Clock, Shield } from "lucide-react";

interface TabAuditProps {
  packageId: string;
  revision: PackageRevision;
}

export function TabAudit({ packageId, revision }: TabAuditProps) {
  const [events, setEvents] = useState<any[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    async function loadEvents() {
      setIsLoading(true);
      try {
        let data = await apiClient.getPackageAudit(packageId);
        if (!data || data.length === 0) {
          data = await apiClient.getAuditEvents({ entity_id: revision.id, limit: 50 });
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


  return (
    <div className="p-6 max-w-5xl space-y-6 text-xs font-sans">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-primary" />
          <h3 className="font-semibold text-foreground text-sm">
            Riwayat Jejak Audit & Perubahan Status (Audit Trail)
          </h3>
        </div>
        <span className="text-[10px] font-mono text-muted-foreground uppercase">
          Permanen & Tak Dapat Dihapus
        </span>
      </div>

      {events.length === 0 ? (
        <div className="p-8 text-center text-muted-foreground font-mono">
          <Clock className="w-6 h-6 text-muted-foreground mx-auto mb-2 opacity-60" />
          <p className="text-xs">
            Belum ada jejak audit tercatat untuk revisi ini.
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
              {events.map((ev, idx) => {
                const isExpanded = expandedId === ev.id || (!expandedId && idx === 0);

                return (
                  <tr key={ev.id || idx} className="hover:bg-muted/20 transition-colors">
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
                          onClick={() => setExpandedId(isExpanded ? null : ev.id)}
                          className="p-1 text-muted-foreground hover:text-foreground rounded"
                        >
                          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
