"use client";

import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api-client";
import { PackageItem } from "@/types/package";
import {
  FolderPlus,
  Building2,
  Calendar,
  Layers,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Plus,
  Landmark,
  ShieldCheck,
} from "lucide-react";

interface CreatePackageModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (pkg: PackageItem) => void;
}

export function CreatePackageModal({
  isOpen,
  onClose,
  onCreated,
}: CreatePackageModalProps) {
  const [schools, setSchools] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [isLoadingMasters, setIsLoadingMasters] = useState(false);

  // Form states
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>("");
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
  const [fiscalYear, setFiscalYear] = useState<number>(2026);
  const [quarter, setQuarter] = useState<number>(2);
  const [fundSource, setFundSource] = useState<string>("BOS_REGULER");
  const [customPackageNumber, setCustomPackageNumber] = useState<string>("");

  // Inline "Register New School" quick modal/form
  const [showNewSchoolForm, setShowNewSchoolForm] = useState(false);
  const [newSchoolName, setNewSchoolName] = useState("");
  const [newSchoolNpsn, setNewSchoolNpsn] = useState("");
  const [newSchoolAddress, setNewSchoolAddress] = useState("");
  const [isCreatingSchool, setIsCreatingSchool] = useState(false);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    async function loadMasters() {
      setIsLoadingMasters(true);
      setErrorMsg(null);
      try {
        const [schoolsData, companiesData] = await Promise.all([
          apiClient.getSchools().catch(() => []),
          apiClient.getCompanies().catch(() => []),
        ]);
        setSchools(schoolsData || []);
        setCompanies(companiesData || []);
        if (schoolsData && schoolsData.length > 0) {
          setSelectedSchoolId(schoolsData[0].id);
        }
        if (companiesData && companiesData.length > 0) {
          setSelectedCompanyId(companiesData[0].id);
        }
      } catch (err: any) {
        setErrorMsg("Gagal memuat master data sekolah.");
      } finally {
        setIsLoadingMasters(false);
      }
    }
    loadMasters();
  }, [isOpen]);

  const handleCreateNewSchool = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSchoolName.trim() || !newSchoolAddress.trim()) {
      alert("Nama sekolah dan alamat wajib diisi.");
      return;
    }
    setIsCreatingSchool(true);
    try {
      const created = await apiClient.createSchool({
        name: newSchoolName.trim(),
        npsn: newSchoolNpsn.trim() || undefined,
        address: newSchoolAddress.trim(),
        level: "SD",
      });
      setSchools((prev) => [created, ...prev]);
      setSelectedSchoolId(created.id);
      setShowNewSchoolForm(false);
      setNewSchoolName("");
      setNewSchoolNpsn("");
      setNewSchoolAddress("");
    } catch (err: any) {
      alert(`Gagal mendaftarkan sekolah: ${err.message || err}`);
    } finally {
      setIsCreatingSchool(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSchoolId) {
      setErrorMsg("Silakan pilih sekolah terlebih dahulu.");
      return;
    }
    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const payload: any = {
        school_id: selectedSchoolId,
        fiscal_year: fiscalYear,
        quarter: quarter,
      };
      if (selectedCompanyId) {
        payload.company_id = selectedCompanyId;
      }
      if (customPackageNumber.trim()) {
        payload.package_number = customPackageNumber.trim();
      }

      const newPkg = await apiClient.createPackage(payload);
      onCreated(newPkg);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Gagal membuat paket pengadaan baru.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3 bg-muted/30">
          <div className="flex items-center gap-2">
            <FolderPlus className="w-4 h-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">
              Buat Paket Pengadaan Manual
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground p-1 rounded hover:bg-muted transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4 overflow-y-auto text-xs">
          {errorMsg && (
            <div className="p-3 bg-red-500/15 border border-red-500/40 text-red-300 rounded-md flex items-center gap-2 shadow-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* 1. School Selector */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-mono uppercase text-muted-foreground font-semibold flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 text-primary" />
                <span>Satuan Pendidikan / Sekolah (BR01)</span>
              </label>
              <button
                type="button"
                onClick={() => setShowNewSchoolForm(!showNewSchoolForm)}
                className="text-[11px] text-primary hover:underline font-mono flex items-center gap-1"
              >
                <Plus className="w-3 h-3" />
                <span>{showNewSchoolForm ? "Tutup Form" : "Daftar Sekolah Baru"}</span>
              </button>
            </div>

            {showNewSchoolForm ? (
              <div className="p-3 border border-primary/40 bg-primary/5 rounded space-y-2">
                <div className="text-[11px] font-semibold text-primary">
                  Pendaftaran Satuan Pendidikan Baru ke Master
                </div>
                <div>
                  <label className="block text-[10px] text-muted-foreground uppercase font-mono">
                    Nama Sekolah
                  </label>
                  <input
                    type="text"
                    value={newSchoolName}
                    onChange={(e) => setNewSchoolName(e.target.value)}
                    placeholder="Contoh: SDN Kebon Kosong 09"
                    className="w-full px-2 py-1 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[10px] text-muted-foreground uppercase font-mono">
                      NPSN (8 Digit)
                    </label>
                    <input
                      type="text"
                      value={newSchoolNpsn}
                      onChange={(e) => setNewSchoolNpsn(e.target.value)}
                      placeholder="20101234"
                      className="w-full px-2 py-1 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-muted-foreground uppercase font-mono">
                      Alamat Lengkap
                    </label>
                    <input
                      type="text"
                      value={newSchoolAddress}
                      onChange={(e) => setNewSchoolAddress(e.target.value)}
                      placeholder="Jl. Kemayoran No. 32"
                      className="w-full px-2 py-1 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setShowNewSchoolForm(false)}
                    className="px-2 py-1 text-[11px] border border-border rounded bg-muted/40 hover:bg-muted"
                  >
                    Batal
                  </button>
                  <button
                    type="button"
                    disabled={isCreatingSchool}
                    onClick={handleCreateNewSchool}
                    className="px-3 py-1 text-[11px] font-semibold rounded bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 flex items-center gap-1"
                  >
                    {isCreatingSchool && <Loader2 className="w-3 h-3 animate-spin" />}
                    <span>Simpan ke Master</span>
                  </button>
                </div>
              </div>
            ) : (
              <select
                value={selectedSchoolId}
                disabled={isLoadingMasters || schools.length === 0}
                onChange={(e) => setSelectedSchoolId(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
              >
                {isLoadingMasters ? (
                  <option value="">Memuat daftar sekolah...</option>
                ) : schools.length === 0 ? (
                  <option value="">Belum ada sekolah di database</option>
                ) : (
                  schools.map((sc) => (
                    <option key={sc.id} value={sc.id}>
                      {sc.name} {sc.npsn ? `(NPSN: ${sc.npsn})` : ""}
                    </option>
                  ))
                )}
              </select>
            )}
          </div>

          {/* 1.5. Company Selector (Rekanan Penyedia) */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 text-foreground font-semibold">
              <Landmark className="w-3.5 h-3.5 text-emerald-400" />
              <span>Badan Usaha Rekanan (Penyedia)</span>
            </div>
            <select
              value={selectedCompanyId}
              disabled={isLoadingMasters || companies.length === 0}
              onChange={(e) => setSelectedCompanyId(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-sans"
            >
              {isLoadingMasters ? (
                <option value="">Memuat daftar rekanan...</option>
              ) : companies.length === 0 ? (
                <option value="">Belum ada rekanan di database</option>
              ) : (
                companies.map((cp) => (
                  <option key={cp.id} value={cp.id}>
                    {cp.legal_name || cp.name}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* 2. Fiscal Year & Quarter */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1 font-semibold">
                Tahun Anggaran
              </label>
              <input
                type="number"
                min="2020"
                max="2030"
                value={fiscalYear}
                onChange={(e) => setFiscalYear(parseInt(e.target.value) || 2026)}
                className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono tabular-nums"
              />
            </div>

            <div>
              <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1 font-semibold">
                Triwulan Pelaksanaan
              </label>
              <select
                value={quarter}
                onChange={(e) => setQuarter(parseInt(e.target.value) || 1)}
                className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono"
              >
                <option value={1}>Triwulan I (TW 1)</option>
                <option value={2}>Triwulan II (TW 2)</option>
                <option value={3}>Triwulan III (TW 3)</option>
                <option value={4}>Triwulan IV (TW 4)</option>
              </select>
            </div>
          </div>

          {/* 3. Funding Source */}
          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1 font-semibold">
              Sumber Dana Anggaran
            </label>
            <select
              value={fundSource}
              onChange={(e) => setFundSource(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono text-[11px]"
            >
              <option value="BOS_REGULER">BOS Reguler (Bantuan Operasional Sekolah)</option>
              <option value="BOS_KINERJA">BOS Kinerja</option>
              <option value="BOP">BOP (Bantuan Operasional Pendidikan)</option>
              <option value="LAINNYA">Lainnya / Swakelola</option>
            </select>
          </div>

          {/* 4. Optional Custom Package Number */}
          <div>
            <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1 font-semibold">
              Nomor Registrasi Paket (Opsional)
            </label>
            <input
              type="text"
              value={customPackageNumber}
              onChange={(e) => setCustomPackageNumber(e.target.value)}
              placeholder={`Otomatis: PKG/${fiscalYear}/Q${quarter}/XXXX`}
              className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-ring font-mono text-[11px]"
            />
          </div>

          {/* PRD Compliance Notice */}
          <div className="p-3 bg-muted/30 border border-border rounded space-y-1 text-muted-foreground font-mono text-[10px] leading-relaxed">
            <div className="flex items-center gap-1.5 text-foreground font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Integritas PRD Pengadaan:</span>
            </div>
            <p>
              • Draf paket akan dibuat dengan nilai awal Rp 0,00 tanpa mengarang tanggal fiktif (BR07).
            </p>
            <p>
              • Rincian item barang diisi pada Tab Barang & Harga dengan tombol <strong>+ Tambah Baris</strong>.
            </p>
            <p>
              • Nomor surat dinas sekolah diisi sesuai surat fisik resmi yang dikeluarkan pihak sekolah di Tab Tanggal & Nomor.
            </p>
          </div>

          {/* Submit Action */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs rounded border border-border bg-card hover:bg-muted text-foreground transition"
            >
              Batal
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !selectedSchoolId}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded bg-primary text-primary-foreground hover:opacity-90 transition shadow-sm disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <FolderPlus className="w-3.5 h-3.5" />
              )}
              <span>Buat Paket & Buka Lembar Kerja</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
