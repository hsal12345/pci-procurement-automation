"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { formatDateIndo } from "@/lib/formatters";
import {
  AuditDiffPanel,
  downloadAuditCsv,
  downloadAuditJson,
} from "@/components/audit/audit-diff-viewer";
import {
  History,
  Search,
  RefreshCw,
  Download,
  ChevronRight,
  ChevronDown,
  ShieldCheck,
  Clock,
} from "lucide-react";

export default function AuditPortalPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [entityName, setEntityName] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: events = [], isLoading, refetch } = useQuery<any[]>({
    queryKey: ["portal-audit-events", searchQuery, entityName, actionFilter, dateFrom, dateTo],
    queryFn: () =>
      apiClient.getAuditEvents({
        q: searchQuery.trim() || undefined,
        entity_name: entityName || undefined,
        action: actionFilter || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: 300,
      }),
  });

  const handleResetFilters = () => {
    setSearchQuery("");
    setEntityName("");
    setActionFilter("");
    setDateFrom("");
    setDateTo("");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Top Bar */}
      <div className="h-12 border-b border-border px-4 flex items-center justify-between gap-4 bg-card/60">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-primary" />
          <h1 className="text-sm font-semibold tracking-tight text-foreground">
            Portal Laporan Jejak Audit Sistem (FR-09 &amp; UC-09)
          </h1>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-semibold">
            {events.length} Rekaman
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition"
            title="Muat Ulang"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            disabled={events.length === 0}
            onClick={() => downloadAuditCsv(events, "portal_audit_pci")}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border border-border bg-card hover:bg-muted text-foreground transition disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5 text-primary" />
            <span>Unduh CSV</span>
          </button>
          <button
            type="button"
            disabled={events.length === 0}
            onClick={() => downloadAuditJson(events, "portal_audit_pci")}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border border-border bg-card hover:bg-muted text-foreground transition disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5 text-emerald-400" />
            <span>Unduh JSON</span>
          </button>
        </div>
      </div>

      {/* Criteria Search Bar (UC-09) */}
      <div className="border-b border-border px-4 py-3 bg-muted/20 flex flex-wrap items-end gap-3 text-xs">
        <div className="flex-1 min-w-[200px] max-w-xs space-y-1">
          <label className="block font-mono text-[10px] uppercase text-muted-foreground">
            Kata Kunci / Sekolah / Aktor
          </label>
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari nama sekolah, aktor, catatan..."
              className="w-full pl-8 pr-2.5 py-1.5 bg-background border border-border rounded text-xs"
            />
          </div>
        </div>

        <div className="w-40 space-y-1">
          <label className="block font-mono text-[10px] uppercase text-muted-foreground">Entitas</label>
          <select
            value={entityName}
            onChange={(e) => setEntityName(e.target.value)}
            className="w-full px-2 py-1.5 bg-background border border-border rounded text-xs font-mono"
          >
            <option value="">Semua Entitas</option>
            <option value="Package">Package</option>
            <option value="PackageRevision">PackageRevision</option>
            <option value="LogisticsRecord">LogisticsRecord</option>
            <option value="LogisticsEvidence">LogisticsEvidence</option>
            <option value="School">School</option>
            <option value="Item">Item</option>
            <option value="BudgetClassification">BudgetClassification</option>
            <option value="TemplateRegistry">TemplateRegistry</option>
            <option value="PackageProfile">PackageProfile</option>
          </select>
        </div>

        <div className="w-40 space-y-1">
          <label className="block font-mono text-[10px] uppercase text-muted-foreground">Jenis Tindakan</label>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="w-full px-2 py-1.5 bg-background border border-border rounded text-xs font-mono"
          >
            <option value="">Semua Aksi</option>
            <option value="CREATE">CREATE</option>
            <option value="UPDATE">UPDATE</option>
            <option value="UPDATE_PRICE">UPDATE_PRICE</option>
            <option value="DEACTIVATE">DEACTIVATE</option>
            <option value="SUBMIT">SUBMIT</option>
            <option value="APPROVE">APPROVE</option>
            <option value="RETURN">RETURN</option>
            <option value="ISSUE">ISSUE</option>
            <option value="UPDATE_LOGISTICS">UPDATE_LOGISTICS</option>
            <option value="UPLOAD_TEMPLATE">UPLOAD_TEMPLATE</option>
            <option value="DISPUTE">DISPUTE</option>
          </select>
        </div>

        <div className="w-36 space-y-1">
          <label className="block font-mono text-[10px] uppercase text-muted-foreground">Dari Tanggal</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="w-full px-2 py-1.5 bg-background border border-border rounded text-xs font-mono"
          />
        </div>

        <div className="w-36 space-y-1">
          <label className="block font-mono text-[10px] uppercase text-muted-foreground">Sampai Tanggal</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="w-full px-2 py-1.5 bg-background border border-border rounded text-xs font-mono"
          />
        </div>

        <button
          type="button"
          onClick={handleResetFilters}
          className="px-3 py-1.5 rounded border border-border bg-card hover:bg-muted text-muted-foreground hover:text-foreground text-xs"
        >
          Reset
        </button>
      </div>

      {/* Compliance Banner */}
      <div className="px-4 py-2 border-b border-border bg-primary/5 flex items-center gap-2 text-[11px] text-muted-foreground">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
        <span>
          Jejak audit bersifat <strong>append-only (kekal)</strong> untuk kebutuhan pengawasan kepatuhan Direktur Keuangan &amp; Administrator Sistem. Klik ikon panah untuk membandingkan <code className="text-foreground">before_state</code> dan <code className="text-foreground">after_state</code>.
        </span>
      </div>

      {/* Audit Table */}
      <div className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <div className="p-10 text-center text-muted-foreground font-mono text-xs">
            Memuat log jejak audit...
          </div>
        ) : events.length === 0 ? (
          <div className="p-10 text-center text-muted-foreground font-mono text-xs space-y-2">
            <Clock className="w-6 h-6 mx-auto opacity-60" />
            <p>Tidak ditemukan catatan jejak audit yang cocok dengan kriteria pencarian.</p>
          </div>
        ) : (
          <div className="border border-border rounded-lg bg-card overflow-hidden shadow-xs">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-muted/60 border-b border-border text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  <th className="px-3 py-2.5 w-44">Waktu (WIB)</th>
                  <th className="px-3 py-2.5 w-36">Entitas</th>
                  <th className="px-3 py-2.5 w-32">Aksi</th>
                  <th className="px-3 py-2.5 w-40">Aktor</th>
                  <th className="px-3 py-2.5 min-w-[220px]">Alasan / Konteks Perubahan</th>
                  <th className="px-3 py-2.5 w-16 text-center">Diff</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70 font-mono text-[11px]">
                {events.map((ev, idx) => {
                  const rowId = ev.id || String(idx);
                  const isExpanded = expandedId === rowId;
                  const hasDiff = Boolean(ev.before_state || ev.after_state);

                  return (
                    <React.Fragment key={rowId}>
                      <tr className="hover:bg-muted/20 transition">
                        <td className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                          {formatDateIndo(ev.timestamp)}
                        </td>
                        <td className="px-3 py-2">
                          <div className="font-semibold text-primary">{ev.entity_name}</div>
                          <div className="text-[10px] text-muted-foreground truncate max-w-[130px]" title={ev.entity_id}>
                            {ev.entity_id}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <span className="px-1.5 py-0.5 rounded bg-muted border border-border text-[10px] font-bold text-foreground">
                            {ev.action}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-foreground">{ev.actor || "Sistem"}</td>
                        <td className="px-3 py-2 font-sans text-muted-foreground">{ev.reason || "-"}</td>
                        <td className="px-3 py-2 text-center">
                          {hasDiff ? (
                            <button
                              type="button"
                              onClick={() => setExpandedId(isExpanded ? null : rowId)}
                              className="p-1 rounded hover:bg-muted text-foreground"
                              title="Tampilkan / Sembunyikan Before & After State"
                            >
                              {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                            </button>
                          ) : (
                            <span className="text-muted-foreground/40">-</span>
                          )}
                        </td>
                      </tr>
                      {isExpanded && hasDiff && (
                        <tr>
                          <td colSpan={6} className="p-0">
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
    </div>
  );
}
