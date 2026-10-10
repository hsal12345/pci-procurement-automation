"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import {
  Building2,
  Search,
  Plus,
  RefreshCw,
  UserCheck,
  Mail,
  Phone,
  MapPin,
  CheckCircle2,
  AlertCircle,
  Pencil,
  Trash2,
  Image as ImageIcon,
  ShieldAlert,
  GraduationCap,
  FileText,
} from "lucide-react";
import { SchoolModal } from "@/components/masters/school-modal";
import { SchoolOfficialModal } from "@/components/masters/school-official-modal";

const ROLE_LABELS: Record<string, { label: string; color: string }> = {
  KEPALA_SEKOLAH: {
    label: "Kepala Sekolah",
    color: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  },
  BENDAHARA: {
    label: "Bendahara",
    color: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  },
  PENGURUS_BARANG: {
    label: "Pengurus Barang",
    color: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  },
  PEJABAT_PENGADAAN: {
    label: "Pejabat Pengadaan",
    color: "bg-purple-500/15 text-purple-300 border-purple-500/30",
  },
  PENERIMA_HASIL_PEKERJAAN: {
    label: "PPHP",
    color: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
  },
  TIM_BOS: {
    label: "Tim BOS",
    color: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
  },
};

interface SchoolCardProps {
  school: any;
  onEditSchool: (school: any) => void;
  onAddOfficial: (school: any) => void;
  onEditOfficial: (school: any, official: any) => void;
  apiBase: string;
}

function SchoolCard({
  school,
  onEditSchool,
  onAddOfficial,
  onEditOfficial,
  apiBase,
}: SchoolCardProps) {
  const queryClient = useQueryClient();

  const { data: officials = [], isLoading: isLoadingOfficials } = useQuery<any[]>({
    queryKey: ["school-officials", school.id],
    queryFn: () => apiClient.getSchoolOfficials(school.id),
  });

  const deleteMutation = useMutation({
    mutationFn: (officialId: string) =>
      apiClient.deleteSchoolOfficial(school.id, officialId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["school-officials", school.id] });
    },
  });

  const handleDeleteOfficial = (officialId: string, officialName: string) => {
    if (confirm(`Apakah Anda yakin ingin menghapus pejabat "${officialName}"?`)) {
      deleteMutation.mutate(officialId);
    }
  };

  const fullLetterheadUrl = school.letterhead_path
    ? school.letterhead_path.startsWith("http")
      ? school.letterhead_path
      : `${apiBase}/${school.letterhead_path.replace(/^\/+/, "")}`
    : null;

  return (
    <div className="border border-border rounded-xl bg-card p-4 space-y-4 shadow-xs hover:border-blue-500/40 transition flex flex-col justify-between">
      <div className="space-y-3">
        {/* Optional Banner Kop Preview */}
        {fullLetterheadUrl && (
          <div className="relative border border-border/70 rounded-lg bg-white/5 p-1 flex items-center justify-center max-h-16 overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={fullLetterheadUrl}
              alt={`Kop ${school.name}`}
              className="max-h-14 w-auto object-contain"
            />
          </div>
        )}

        {/* Header Card */}
        <div className="flex items-start justify-between border-b border-border/80 pb-3 gap-2">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                {school.level || "SD"}
              </span>
              <h3 className="font-semibold text-foreground text-sm tracking-tight">
                {school.name}
              </h3>
            </div>
            <div className="flex items-center gap-2 text-[11px] font-mono text-muted-foreground">
              <span>
                NPSN: <span className="text-foreground font-semibold">{school.npsn || "-"}</span>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 flex-shrink-0">
            {fullLetterheadUrl && (
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

        {/* Address & Contact info */}
        <div className="space-y-1 text-xs">
          <div className="flex items-start gap-1.5 text-muted-foreground">
            <MapPin className="w-3.5 h-3.5 mt-0.5 text-slate-400 flex-shrink-0" />
            <span className="leading-snug">
              {school.address}
              {school.subdistrict ? `, Kec. ${school.subdistrict}` : ""}
              {school.city ? `, ${school.city}` : ""}
              {school.postal_code ? ` ${school.postal_code}` : ""}
            </span>
          </div>

          {(school.phone || school.email) && (
            <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] font-mono text-muted-foreground">
              {school.phone && (
                <div className="flex items-center gap-1">
                  <Phone className="w-3 h-3 text-slate-400" />
                  <span>{school.phone}</span>
                </div>
              )}
              {school.email && (
                <div className="flex items-center gap-1">
                  <Mail className="w-3 h-3 text-slate-400" />
                  <span className="text-sky-400">{school.email}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Officials Section */}
        <div className="pt-2 border-t border-border/60 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <UserCheck className="w-3.5 h-3.5 text-blue-400" />
              Pejabat Penandatangan ({officials.length})
            </span>
            <button
              type="button"
              onClick={() => onAddOfficial(school)}
              className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium text-blue-300 hover:text-blue-200 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 rounded transition"
            >
              <Plus className="w-3 h-3" />
              <span>Pejabat</span>
            </button>
          </div>

          {isLoadingOfficials ? (
            <div className="text-[11px] text-muted-foreground py-2 font-mono">
              Memuat data pejabat...
            </div>
          ) : officials.length === 0 ? (
            <div className="p-2.5 rounded bg-muted/20 border border-border/40 text-[11px] text-muted-foreground flex items-center justify-between">
              <span>Belum ada pejabat penandatangan didaftarkan.</span>
              <button
                type="button"
                onClick={() => onAddOfficial(school)}
                className="text-blue-400 hover:underline font-medium text-[11px]"
              >
                + Tambah
              </button>
            </div>
          ) : (
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              {officials.map((off: any) => {
                const roleMeta = ROLE_LABELS[off.role] || {
                  label: off.role,
                  color: "bg-slate-500/15 text-slate-300 border-slate-500/30",
                };

                return (
                  <div
                    key={off.id}
                    className="p-2 rounded bg-muted/30 border border-border/60 flex items-start justify-between gap-2 hover:border-slate-600 transition"
                  >
                    <div className="space-y-0.5 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span
                          className={`text-[9px] font-mono px-1.5 py-0.2 rounded border font-semibold ${roleMeta.color}`}
                        >
                          {roleMeta.label}
                        </span>
                        <span className="text-xs font-semibold text-foreground truncate">
                          {off.person_name}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-x-2 text-[10px] font-mono text-muted-foreground">
                        {off.nip && (
                          <span>
                            NIP: <span className="text-slate-300">{off.nip}</span>
                          </span>
                        )}
                        {off.position_sk_number && (
                          <span className="flex items-center gap-0.5 text-blue-300/80">
                            <FileText className="w-2.5 h-2.5" />
                            <span>SK: {off.position_sk_number}</span>
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0 pt-0.5">
                      <button
                        type="button"
                        onClick={() => onEditOfficial(school, off)}
                        className="p-1 text-muted-foreground hover:text-blue-400 rounded hover:bg-muted transition"
                        title="Edit Data Pejabat & SK"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteOfficial(off.id, off.person_name)}
                        className="p-1 text-muted-foreground hover:text-rose-400 rounded hover:bg-muted transition"
                        title="Hapus Pejabat"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Card Action Footer */}
      <div className="pt-3 border-t border-border flex items-center justify-between gap-2">
        <span className="text-[10px] text-muted-foreground font-mono">
          ID: {school.id?.substring(0, 8)}...
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onEditSchool(school)}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded bg-muted hover:bg-accent text-foreground transition border border-border"
          >
            <Pencil className="w-3 h-3" />
            <span>Edit Sekolah</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default function SchoolsPage() {
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState("ALL");
  const queryClient = useQueryClient();

  // School modal state
  const [isSchoolModalOpen, setIsSchoolModalOpen] = useState(false);
  const [selectedSchool, setSelectedSchool] = useState<any | null>(null);

  // Official modal state
  const [isOfficialModalOpen, setIsOfficialModalOpen] = useState(false);
  const [officialTargetSchool, setOfficialTargetSchool] = useState<any | null>(null);
  const [selectedOfficial, setSelectedOfficial] = useState<any | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const { data: schools = [], isLoading, error, refetch } = useQuery<any[]>({
    queryKey: ["schools"],
    queryFn: () => apiClient.getSchools(),
  });

  const filteredSchools = schools.filter((sch) => {
    const term = search.toLowerCase();
    const name = (sch.name || "").toLowerCase();
    const npsn = (sch.npsn || "").toLowerCase();
    const subdistrict = (sch.subdistrict || "").toLowerCase();
    const address = (sch.address || "").toLowerCase();

    const matchesSearch =
      name.includes(term) ||
      npsn.includes(term) ||
      subdistrict.includes(term) ||
      address.includes(term);

    const matchesLevel =
      levelFilter === "ALL" || (sch.level || "SD").toUpperCase() === levelFilter;

    return matchesSearch && matchesLevel;
  });

  const handleOpenCreateSchool = () => {
    setSelectedSchool(null);
    setIsSchoolModalOpen(true);
  };

  const handleOpenEditSchool = (sch: any) => {
    setSelectedSchool(sch);
    setIsSchoolModalOpen(true);
  };

  const handleOpenAddOfficial = (sch: any) => {
    setOfficialTargetSchool(sch);
    setSelectedOfficial(null);
    setIsOfficialModalOpen(true);
  };

  const handleOpenEditOfficial = (sch: any, official: any) => {
    setOfficialTargetSchool(sch);
    setSelectedOfficial(official);
    setIsOfficialModalOpen(true);
  };

  const handleSchoolSuccess = () => {
    refetch();
  };

  const handleOfficialSuccess = () => {
    if (officialTargetSchool?.id) {
      queryClient.invalidateQueries({
        queryKey: ["school-officials", officialTargetSchool.id],
      });
    }
  };

  return (
    <div className="flex flex-col h-full font-sans">
      {/* Top Action Bar */}
      <div className="h-12 border-b border-border px-4 flex items-center justify-between gap-4 bg-card/60">
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-blue-400" />
          <h1 className="text-sm font-semibold tracking-tight text-foreground">
            Master Data Satuan Pendidikan & Sekolah
          </h1>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30 font-semibold">
            {schools.length} Sekolah
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
            onClick={handleOpenCreateSchool}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-blue-600 hover:bg-blue-500 text-white transition shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Tambah Sekolah Baru</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="border-b border-border px-4 py-2.5 bg-card/40 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3 flex-1 min-w-[280px] max-w-lg">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Cari nama sekolah, NPSN, kecamatan, alamat..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
            />
          </div>
        </div>

        {/* Level filter tabs */}
        <div className="flex items-center gap-1 bg-background p-1 border border-border rounded-lg text-[11px]">
          {["ALL", "SD", "SMP", "SMA", "SMK"].map((lvl) => (
            <button
              key={lvl}
              type="button"
              onClick={() => setLevelFilter(lvl)}
              className={`px-2.5 py-0.5 rounded font-medium transition ${
                levelFilter === lvl
                  ? "bg-blue-600 text-white shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {lvl === "ALL" ? "Semua" : lvl}
            </button>
          ))}
        </div>

        <span className="text-[11px] font-mono text-muted-foreground">
          Menampilkan {filteredSchools.length} dari {schools.length} sekolah
        </span>
      </div>

      {/* Main Content List */}
      <div className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-muted-foreground text-xs font-mono">
            Memuat daftar satuan pendidikan sekolah...
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-48 text-destructive text-xs gap-2">
            <AlertCircle className="w-5 h-5" />
            <span>Gagal memuat master data sekolah: {(error as any)?.message}</span>
            <button
              type="button"
              onClick={() => refetch()}
              className="px-2.5 py-1 text-[11px] bg-card border border-border text-foreground rounded hover:bg-muted transition"
            >
              Coba Lagi
            </button>
          </div>
        ) : filteredSchools.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-muted-foreground text-xs font-mono space-y-2">
            <span>Tidak ada data sekolah yang cocok dengan pencarian.</span>
            <button
              type="button"
              onClick={handleOpenCreateSchool}
              className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-sans font-semibold transition shadow-xs text-xs"
            >
              + Daftarkan Sekolah Baru
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filteredSchools.map((sch) => (
              <SchoolCard
                key={sch.id}
                school={sch}
                onEditSchool={handleOpenEditSchool}
                onAddOfficial={handleOpenAddOfficial}
                onEditOfficial={handleOpenEditOfficial}
                apiBase={apiBase}
              />
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      <SchoolModal
        isOpen={isSchoolModalOpen}
        onClose={() => setIsSchoolModalOpen(false)}
        onSuccess={handleSchoolSuccess}
        initialSchool={selectedSchool}
      />

      {officialTargetSchool && (
        <SchoolOfficialModal
          isOpen={isOfficialModalOpen}
          onClose={() => {
            setIsOfficialModalOpen(false);
            setOfficialTargetSchool(null);
            setSelectedOfficial(null);
          }}
          onSuccess={handleOfficialSuccess}
          schoolId={officialTargetSchool.id}
          schoolName={officialTargetSchool.name}
          initialOfficial={selectedOfficial}
        />
      )}
    </div>
  );
}
