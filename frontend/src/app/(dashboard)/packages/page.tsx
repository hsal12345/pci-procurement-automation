"use client";

import { useQuery } from "@tanstack/react-query";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import { formatIDR, formatShortDateIndo } from "@/lib/formatters";
import { PackageItem } from "@/types/package";
import {
  FolderKanban,
  Search,
  ArrowUpRight,
  RefreshCw,
  AlertCircle,
  FileSpreadsheet,
  CheckSquare,
  Archive,
  ShieldCheck,
  X,
  Trash2,
  Loader2,
  Plus,
} from "lucide-react";
import { ImportModal } from "@/components/imports/import-modal";
import { CreatePackageModal } from "@/components/packages/create-package-modal";

export default function PackagesPageWrapper() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-48 text-muted-foreground text-xs font-mono">
        Memuat daftar transaksi...
      </div>
    }>
      <PackagesListPage />
    </Suspense>
  );
}

function PackagesListPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const filterParam = searchParams.get("filter")?.toLowerCase() || "";
  const tabParam = searchParams.get("tab")?.toLowerCase() || "";

  const { data: packages = [], isLoading, error, refetch } = useQuery<PackageItem[]>({
    queryKey: ["packages"],
    queryFn: () => apiClient.getPackages(),
  });

  const handleDeletePackage = async (e: React.MouseEvent, pkg: PackageItem) => {
    e.stopPropagation();
    e.preventDefault();
    const pkgCode = pkg.package_code || pkg.package_number;
    if (
      !confirm(
        `Apakah Anda yakin ingin menghapus permanen draf paket pengadaan ${pkgCode}? Seluruh revisi dan rincian barang akan dihapus.`
      )
    ) {
      return;
    }
    setDeletingId(pkg.id);
    try {
      await apiClient.deletePackage(pkg.id);
      await refetch();
    } catch (err: any) {
      alert(`Gagal menghapus draf paket: ${err.message || err}`);
    } finally {
      setDeletingId(null);
    }
  };

  // Sync status filter from URL parameter
  useEffect(() => {
    if (filterParam === "under_review") {
      setStatusFilter("UNDER_REVIEW");
    } else if (filterParam === "draft") {
      setStatusFilter("DRAFT");
    } else if (filterParam === "approved") {
      setStatusFilter("APPROVED");
    } else if (filterParam === "issued") {
      setStatusFilter("ISSUED");
    } else if (filterParam === "cancelled") {
      setStatusFilter("CANCELLED");
    }
  }, [filterParam]);

  // Target tab for deep links
  const targetTab =
    tabParam ||
    (filterParam === "inspection"
      ? "inspection"
      : filterParam === "document" || filterParam === "documents"
      ? "documents"
      : "");

  const latestPackage = packages.length > 0 ? packages[0] : null;

  const filteredPackages = packages.filter((pkg) => {
    const currentRev = pkg.revisions?.[pkg.revisions.length - 1];
    const schoolName = currentRev?.school_snapshot?.name || "";
    const packageCode = pkg.package_code || pkg.package_number || "";
    const matchesSearch =
      packageCode.toLowerCase().includes(search.toLowerCase()) ||
      schoolName.toLowerCase().includes(search.toLowerCase());

    if (!matchesSearch) return false;
    if (statusFilter === "ALL") return true;
    return currentRev?.status === statusFilter || pkg.status === statusFilter;
  });

  return (
    <div className="flex flex-col h-full">
      {/* Top Action Bar */}
      <div className="h-12 border-b border-border px-4 flex items-center justify-between gap-4 bg-card/60">
        <div className="flex items-center gap-2">
          <FolderKanban className="w-4 h-4 text-primary" />
          <h1 className="text-sm font-semibold tracking-tight text-foreground">Daftar Paket Pengadaan & SPJ</h1>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-semibold">
            {packages.length} Paket
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
            onClick={() => setIsImportOpen(true)}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border border-border bg-card hover:bg-muted text-foreground transition"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Impor Spreadsheet</span>
          </button>
          <button
            type="button"
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded bg-primary text-primary-foreground hover:opacity-90 transition shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Buat Paket Baru</span>
          </button>
        </div>
      </div>

      {/* Quick Navigation / Filter Banner for deep links */}
      {(filterParam === "inspection" || tabParam === "inspection") && latestPackage && (
        <div className="bg-primary/10 border-b border-primary/25 px-4 py-2 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-foreground">
            <CheckSquare className="w-4 h-4 text-primary" />
            <span className="font-medium">Pemeriksaan Sistem & Verifikasi AI</span>
            <span className="text-muted-foreground font-mono">
              (Pilih paket di bawah atau buka paket aktif langsung)
            </span>
          </div>
          <Link
            href={`/packages/${latestPackage.id}?tab=inspection`}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-primary text-primary-foreground font-semibold text-[11px] hover:opacity-90 transition shadow-xs"
          >
            <span>Buka Pemeriksaan ({latestPackage.package_code || latestPackage.package_number})</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {(filterParam === "document" || filterParam === "documents" || tabParam === "documents") && latestPackage && (
        <div className="bg-primary/10 border-b border-primary/25 px-4 py-2 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-foreground">
            <Archive className="w-4 h-4 text-primary" />
            <span className="font-medium">Arsip & Pembuatan 13 Dokumen SPJ</span>
            <span className="text-muted-foreground font-mono">
              (Pilih paket di bawah atau buka paket aktif langsung)
            </span>
          </div>
          <Link
            href={`/packages/${latestPackage.id}?tab=documents`}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-primary text-primary-foreground font-semibold text-[11px] hover:opacity-90 transition shadow-xs"
          >
            <span>Buka Generator Dokumen ({latestPackage.package_code || latestPackage.package_number})</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {filterParam === "under_review" && (
        <div className="bg-amber-500/15 border-b border-amber-500/30 px-4 py-2 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-amber-300">
            <ShieldCheck className="w-4 h-4 text-amber-400" />
            <span className="font-medium">Filter Aktif: Paket Menunggu Persetujuan Direktur Keuangan (UNDER_REVIEW)</span>
          </div>
          <button
            type="button"
            onClick={() => {
              setStatusFilter("ALL");
              router.replace("/packages");
            }}
            className="flex items-center gap-1 text-[11px] text-amber-300 hover:text-amber-200 transition"
          >
            <X className="w-3.5 h-3.5" />
            <span>Reset Filter</span>
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="border-b border-border px-4 py-2.5 bg-card/40 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 flex-1 max-w-sm">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Cari kode paket, nama sekolah..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
            />
          </div>
        </div>

        {/* Status Pills Filter */}
        <div className="flex items-center gap-1.5 font-mono text-[11px] overflow-x-auto">
          {["ALL", "DRAFT", "UNDER_REVIEW", "APPROVED", "ISSUED", "CANCELLED"].map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => {
                setStatusFilter(st);
                if (st === "ALL") router.replace("/packages");
                else router.replace(`/packages?filter=${st.toLowerCase()}`);
              }}
              className={`px-2.5 py-1 rounded transition border ${
                statusFilter === st
                  ? "bg-primary text-primary-foreground font-semibold border-primary shadow-xs"
                  : "bg-card hover:bg-muted text-muted-foreground hover:text-foreground border-border"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Main Table */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-muted-foreground text-xs font-mono">
            Memuat daftar transaksi...
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-48 text-destructive text-xs gap-2">
            <AlertCircle className="w-5 h-5" />
            <span>Gagal menghubungi backend API: {(error as any)?.message}</span>
            <button
              type="button"
              onClick={() => refetch()}
              className="px-2.5 py-1 text-[11px] bg-card border border-border text-foreground rounded hover:bg-muted transition"
            >
              Coba Lagi
            </button>
          </div>
        ) : filteredPackages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-muted-foreground text-xs font-mono space-y-2">
            <span>Tidak ada paket pengadaan yang cocok.</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsCreateOpen(true)}
                className="px-2.5 py-1 rounded bg-primary text-primary-foreground font-sans font-semibold hover:opacity-90 transition shadow-xs"
              >
                + Buat Paket Baru Manual
              </button>
              <button
                type="button"
                onClick={() => setIsImportOpen(true)}
                className="px-2.5 py-1 rounded border border-border bg-card hover:bg-muted text-foreground transition"
              >
                Impor Spreadsheet
              </button>
            </div>
          </div>
        ) : (
          <table className="w-full text-left border-collapse font-sans text-xs">
            <thead>
              <tr className="bg-muted/80 border-b border-border text-[11px] font-semibold uppercase tracking-wider text-slate-200 font-mono shadow-xs">
                <th className="px-3.5 py-2.5">Kode Paket</th>
                <th className="px-3.5 py-2.5">Nama Sekolah / Lembaga</th>
                <th className="px-3.5 py-2.5">TA / TW</th>
                <th className="px-3.5 py-2.5">Sumber Dana</th>
                <th className="px-3.5 py-2.5">Rev (Ver)</th>
                <th className="px-3.5 py-2.5">Status Bisnis</th>
                <th className="px-3.5 py-2.5 text-right">Nilai Transaksi (IDR)</th>
                <th className="px-3.5 py-2.5">Tanggal</th>
                <th className="px-3.5 py-2.5 text-center">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredPackages.map((pkg) => {
                const latestRev = pkg.revisions?.[pkg.revisions.length - 1];
                const status = latestRev?.status || "DRAFT";
                const schoolName = latestRev?.school_snapshot?.name || "-";
                const grandTotal = latestRev?.grand_total || 0;

                const href = targetTab ? `/packages/${pkg.id}?tab=${targetTab}` : `/packages/${pkg.id}`;
                const isDraft = status === "DRAFT" || status === "RETURNED";

                return (
                  <tr
                    key={pkg.id}
                    className="hover:bg-primary/5 transition-colors group cursor-pointer"
                  >
                    <td className="px-3.5 py-2.5 font-mono font-medium text-foreground whitespace-nowrap">
                      <Link
                        href={href}
                        className="text-primary hover:underline flex items-center gap-1 font-semibold"
                      >
                        {pkg.package_code || pkg.package_number}
                      </Link>
                    </td>
                    <td className="px-3.5 py-2.5 text-foreground font-medium truncate max-w-xs">
                      {schoolName}
                    </td>
                    <td className="px-3.5 py-2.5 font-mono whitespace-nowrap text-muted-foreground">
                      {pkg.fiscal_year} - TW {pkg.quarter}
                    </td>
                    <td className="px-3.5 py-2.5 font-mono whitespace-nowrap text-muted-foreground">
                      {pkg.fund_source}
                    </td>
                    <td className="px-3.5 py-2.5 font-mono whitespace-nowrap text-slate-300">
                      Rev {latestRev?.revision_number || 1} (v{latestRev?.version || 1})
                    </td>
                    <td className="px-3.5 py-2.5 whitespace-nowrap">
                      <StatusBadge status={status} />
                    </td>
                    <td className="px-3.5 py-2.5 font-mono tabular-nums text-right font-medium text-foreground whitespace-nowrap">
                      {formatIDR(grandTotal)}
                    </td>
                    <td className="px-3.5 py-2.5 font-mono text-muted-foreground whitespace-nowrap">
                      {formatShortDateIndo(pkg.created_at)}
                    </td>
                    <td className="px-3.5 py-2.5 text-center whitespace-nowrap">
                      <div className="inline-flex items-center gap-1">
                        <Link
                          href={href}
                          className="inline-flex p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition"
                          title="Buka Lembar Kerja"
                        >
                          <ArrowUpRight className="w-3.5 h-3.5" />
                        </Link>
                        {isDraft && (
                          <button
                            type="button"
                            onClick={(e) => handleDeletePackage(e, pkg)}
                            disabled={deletingId === pkg.id}
                            className="inline-flex p-1.5 text-muted-foreground hover:text-destructive hover:bg-red-500/10 rounded transition"
                            title="Hapus Draf Pengadaan"
                          >
                            {deletingId === pkg.id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-destructive" />
                            ) : (
                              <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-red-400" />
                            )}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Import Modal */}
      <ImportModal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onSuccess={() => {
          setIsImportOpen(false);
          refetch();
        }}
      />

      {/* Manual Create Package Modal */}
      <CreatePackageModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onCreated={(newPkg) => {
          refetch();
          router.push(`/packages/${newPkg.id}`);
        }}
      />
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "ISSUED") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/40">
        [ 🟢 TERBIT / ISSUED ]
      </span>
    );
  }
  if (status === "APPROVED") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/40">
        [ 🟢 DISETUJUI ]
      </span>
    );
  }
  if (status === "UNDER_REVIEW") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/40">
        [ 🟡 DALAM TINJAUAN ]
      </span>
    );
  }
  if (status === "RETURNED") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-red-500/15 text-red-300 border border-red-500/40">
        [ 🔴 DIKEMBALIKAN ]
      </span>
    );
  }
  if (status === "CANCELLED") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-700/50 text-slate-300 border border-slate-600/60">
        [ ✕ DIBATALKAN ]
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-muted text-slate-300 border border-border">
      [ ⚪ DRAF ]
    </span>
  );
}
