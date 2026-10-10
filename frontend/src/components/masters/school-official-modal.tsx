"use client";

import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api-client";
import {
  UserCheck,
  X,
  Loader2,
  AlertCircle,
  FileText,
  Calendar,
  Building,
  CheckCircle2,
} from "lucide-react";

interface SchoolOfficialModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  schoolId: string;
  schoolName: string;
  initialOfficial?: any | null;
}

const ROLES = [
  { value: "KEPALA_SEKOLAH", label: "Kepala Sekolah" },
  { value: "BENDAHARA", label: "Bendahara Sekolah" },
  { value: "PENGURUS_BARANG", label: "Pengurus Barang" },
  { value: "PEJABAT_PENGADAAN", label: "Pejabat Pengadaan" },
  { value: "PENERIMA_HASIL_PEKERJAAN", label: "Penerima Hasil Pekerjaan (PPHP)" },
  { value: "TIM_BOS", label: "Tim BOS Sekolah" },
];

export function SchoolOfficialModal({
  isOpen,
  onClose,
  onSuccess,
  schoolId,
  schoolName,
  initialOfficial,
}: SchoolOfficialModalProps) {
  const isEdit = Boolean(initialOfficial?.id);

  const [role, setRole] = useState("KEPALA_SEKOLAH");
  const [personName, setPersonName] = useState("");
  const [nip, setNip] = useState("");
  const [positionSkNumber, setPositionSkNumber] = useState("");
  const [validFrom, setValidFrom] = useState("2026-01-01");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (isOpen) {
      if (initialOfficial) {
        setRole(initialOfficial.role || "KEPALA_SEKOLAH");
        setPersonName(initialOfficial.person_name || "");
        setNip(initialOfficial.nip || "");
        setPositionSkNumber(initialOfficial.position_sk_number || "");
        setValidFrom(initialOfficial.valid_from ? String(initialOfficial.valid_from).substring(0, 10) : "2026-01-01");
      } else {
        setRole("KEPALA_SEKOLAH");
        setPersonName("");
        setNip("");
        setPositionSkNumber("");
        setValidFrom("2026-01-01");
      }
      setErrorMsg("");
    }
  }, [isOpen, initialOfficial]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!personName.trim()) {
      setErrorMsg("Nama pejabat wajib diisi.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg("");

      const payload = {
        role,
        person_name: personName.trim(),
        nip: nip.trim() || undefined,
        position_sk_number: positionSkNumber.trim() || undefined,
        valid_from: validFrom || "2026-01-01",
      };

      if (isEdit && initialOfficial?.id) {
        await apiClient.updateSchoolOfficial(schoolId, initialOfficial.id, payload);
      } else {
        await apiClient.createSchoolOfficial(schoolId, payload);
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      console.error("Gagal menyimpan pejabat:", err);
      setErrorMsg(err.message || "Terjadi kesalahan saat menyimpan data pejabat.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-800/40">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">
                {isEdit ? "Edit Pejabat Penandatangan" : "Tambah Pejabat Penandatangan"}
              </h2>
              <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                <Building className="w-3.5 h-3.5 text-slate-500" />
                <span className="font-medium text-slate-300">{schoolName}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMsg && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Jabatan / Peran <span className="text-rose-400">*</span>
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Nama Lengkap Beserta Gelar <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={personName}
              onChange={(e) => setPersonName(e.target.value)}
              placeholder="Contoh: Drs. H. Bambang Sutrisno, M.Pd"
              className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                NIP (Nomor Induk Pegawai)
              </label>
              <input
                type="text"
                value={nip}
                onChange={(e) => setNip(e.target.value)}
                placeholder="19750814 200112 1 002"
                className="w-full px-3 py-2 text-sm font-mono bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">
                Biarkan strip (-) bila non-PNS
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Berlaku Mulai (SK)
              </label>
              <div className="relative">
                <input
                  type="date"
                  value={validFrom}
                  onChange={(e) => setValidFrom(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-blue-400" />
              Nomor SK Penugasan / SK Pengangkatan
            </label>
            <input
              type="text"
              value={positionSkNumber}
              onChange={(e) => setPositionSkNumber(e.target.value)}
              placeholder="Contoh: 800/014/SK/2026 atau 123/DISDIK/2026"
              className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
            />
            <span className="text-[10px] text-slate-400 mt-1 block">
              Nomor SK ini akan otomatis masuk ke dokumen BA Evaluasi, Penetapan, dan BAST.
            </span>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition"
            >
              Batal
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition shadow-lg shadow-blue-600/20 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Menyimpan...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  {isEdit ? "Simpan Perubahan" : "Tambah Pejabat"}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
