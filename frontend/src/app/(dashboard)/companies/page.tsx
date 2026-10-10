"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import {
  Landmark,
  Search,
  Plus,
  RefreshCw,
  Building,
  UserCheck,
  CreditCard,
  Mail,
  Phone,
  MapPin,
  CheckCircle2,
  AlertCircle,
  Pencil,
  Image as ImageIcon,
} from "lucide-react";
import { CreateCompanyModal } from "@/components/packages/create-company-modal";

export default function CompaniesPage() {
  const [search, setSearch] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<any | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const { data: companies = [], isLoading, error, refetch } = useQuery<any[]>({
    queryKey: ["companies"],
    queryFn: () => apiClient.getCompanies(),
  });

  const filteredCompanies = companies.filter((cp) => {
    const term = search.toLowerCase();
    const name = (cp.legal_name || cp.name || "").toLowerCase();
    const director = (cp.director_name || "").toLowerCase();
    const npwp = (cp.npwp || "").toLowerCase();
    return name.includes(term) || director.includes(term) || npwp.includes(term);
  });

  const handleOpenCreate = () => {
    setSelectedCompany(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (cp: any) => {
    setSelectedCompany(cp);
    setIsModalOpen(true);
  };

  return (
    <div className="flex flex-col h-full font-sans">
      {/* Top Action Bar */}
      <div className="h-12 border-b border-border px-4 flex items-center justify-between gap-4 bg-card/60">
        <div className="flex items-center gap-2">
          <Landmark className="w-4 h-4 text-emerald-400" />
          <h1 className="text-sm font-semibold tracking-tight text-foreground">
            Master Data Badan Usaha & Rekanan Penyedia
          </h1>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold">
            {companies.length} Rekanan
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition"
            title="Muat Ulang Data"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={handleOpenCreate}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Tambah Rekanan Baru</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="border-b border-border px-4 py-2.5 bg-card/40 flex items-center justify-between gap-3 text-xs">
        <div className="relative w-full max-w-md">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Cari nama rekanan, direktur, nomor NPWP..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
          />
        </div>
        <span className="text-[11px] font-mono text-muted-foreground">
          Menampilkan {filteredCompanies.length} dari {companies.length} rekanan
        </span>
      </div>

      {/* Main Content List */}
      <div className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-muted-foreground text-xs font-mono">
            Memuat daftar rekanan penyedia...
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-48 text-destructive text-xs gap-2">
            <AlertCircle className="w-5 h-5" />
            <span>Gagal memuat master data rekanan: {(error as any)?.message}</span>
            <button
              type="button"
              onClick={() => refetch()}
              className="px-2.5 py-1 text-[11px] bg-card border border-border text-foreground rounded hover:bg-muted transition"
            >
              Coba Lagi
            </button>
          </div>
        ) : filteredCompanies.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-muted-foreground text-xs font-mono space-y-2">
            <span>Tidak ada data rekanan yang cocok dengan pencarian.</span>
            <button
              type="button"
              onClick={handleOpenCreate}
              className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-sans font-semibold transition shadow-xs text-xs"
            >
              + Daftarkan Rekanan Baru
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredCompanies.map((cp) => {
              const fullLogoUrl = cp.logo_path
                ? cp.logo_path.startsWith("http")
                  ? cp.logo_path
                  : `${apiBase}${cp.logo_path}`
                : null;

              return (
                <div
                  key={cp.id}
                  className="border border-border rounded-lg bg-card p-4 space-y-3 shadow-xs hover:border-emerald-500/40 transition flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    {/* Optional Banner Kop Preview */}
                    {fullLogoUrl && (
                      <div className="relative border border-border/70 rounded bg-white/5 p-1 flex items-center justify-center max-h-16 overflow-hidden">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={fullLogoUrl}
                          alt={`Kop ${cp.legal_name || cp.name}`}
                          className="max-h-14 w-auto object-contain"
                        />
                      </div>
                    )}

                    {/* Header Card */}
                    <div className="flex items-start justify-between border-b border-border/80 pb-2.5 gap-2">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <Building className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                          <h3 className="font-semibold text-foreground text-sm tracking-tight">
                            {cp.legal_name || cp.name}
                          </h3>
                        </div>
                        <span className="text-[11px] font-mono text-muted-foreground block">
                          NPWP: <span className="text-foreground font-semibold">{cp.npwp || "-"}</span>
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {fullLogoUrl && (
                          <span
                            className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30"
                            title="Banner kop surat resmi diunggah"
                          >
                            <ImageIcon className="w-2.5 h-2.5" />
                            <span>Kop Banner</span>
                          </span>
                        )}
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          <span>AKTIF</span>
                        </span>
                      </div>
                    </div>

                    {/* Details Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      {/* Direktur */}
                      <div className="p-2 rounded bg-muted/30 border border-border/60 space-y-0.5">
                        <div className="flex items-center gap-1 text-[10px] font-mono text-muted-foreground uppercase font-semibold">
                          <UserCheck className="w-3 h-3 text-sky-400" />
                          <span>{cp.director_title || "Direktur Utama"}</span>
                        </div>
                        <div className="font-semibold text-foreground text-[11px]">
                          {cp.director_name || "-"}
                        </div>
                        <div
                          className="text-[10px] font-mono text-muted-foreground truncate"
                          title={cp.director_sk_number}
                        >
                          {cp.director_sk_number || "Akta Notaris Belum Dicatat"}
                        </div>
                      </div>

                      {/* Bank & Rekening */}
                      <div className="p-2 rounded bg-muted/30 border border-border/60 space-y-0.5">
                        <div className="flex items-center gap-1 text-[10px] font-mono text-muted-foreground uppercase font-semibold">
                          <CreditCard className="w-3 h-3 text-amber-400" />
                          <span>Rekening Pembayaran</span>
                        </div>
                        <div className="font-semibold text-foreground text-[11px]">
                          {cp.bank_name || "-"}
                        </div>
                        <div className="text-[10px] font-mono text-foreground font-medium">
                          {cp.bank_account_number || "-"}
                        </div>
                      </div>
                    </div>

                    {/* Alamat & Kontak */}
                    <div className="text-[11px] text-muted-foreground space-y-1 pt-1 border-t border-border/60 font-sans">
                      <div className="flex items-center gap-1.5 truncate">
                        <MapPin className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                        <span className="truncate">
                          {cp.address || "-"}, {cp.city || "Jakarta"}
                        </span>
                      </div>
                      {(cp.email || cp.phone) && (
                        <div className="flex items-center gap-3 font-mono text-[10px]">
                          {cp.phone && (
                            <span className="flex items-center gap-1">
                              <Phone className="w-2.5 h-2.5" />
                              <span>{cp.phone}</span>
                            </span>
                          )}
                          {cp.email && (
                            <span className="flex items-center gap-1">
                              <Mail className="w-2.5 h-2.5" />
                              <span>{cp.email}</span>
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Bottom Actions */}
                  <div className="pt-2 border-t border-border flex items-center justify-end">
                    <button
                      type="button"
                      onClick={() => handleOpenEdit(cp)}
                      className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded border border-border bg-card hover:bg-muted text-foreground transition font-sans font-medium"
                    >
                      <Pencil className="w-3 h-3 text-primary" />
                      <span>Edit Rekanan</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create / Edit Company Modal */}
      <CreateCompanyModal
        isOpen={isModalOpen}
        initialCompany={selectedCompany}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedCompany(null);
        }}
        onSuccess={() => {
          refetch();
        }}
      />
    </div>
  );
}
