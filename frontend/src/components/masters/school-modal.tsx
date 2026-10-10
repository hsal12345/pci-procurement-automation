"use client";

import { useState, useEffect, useRef } from "react";
import { apiClient } from "@/lib/api-client";
import {
  Building2,
  X,
  Loader2,
  AlertCircle,
  MapPin,
  Upload,
  Image as ImageIcon,
  CheckCircle2,
  ShieldCheck,
} from "lucide-react";

interface SchoolModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialSchool?: any | null;
}

export function SchoolModal({
  isOpen,
  onClose,
  onSuccess,
  initialSchool,
}: SchoolModalProps) {
  const isEdit = Boolean(initialSchool?.id);

  const [name, setName] = useState("");
  const [npsn, setNpsn] = useState("");
  const [level, setLevel] = useState("SD");
  const [address, setAddress] = useState("");
  const [subdistrict, setSubdistrict] = useState("");
  const [city, setCity] = useState("Jakarta Pusat");
  const [postalCode, setPostalCode] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (isOpen) {
      if (initialSchool) {
        setName(initialSchool.name || "");
        setNpsn(initialSchool.npsn || "");
        setLevel(initialSchool.level || "SD");
        setAddress(initialSchool.address || "");
        setSubdistrict(initialSchool.subdistrict || "");
        setCity(initialSchool.city || "Jakarta Pusat");
        setPostalCode(initialSchool.postal_code || "");
        setPhone(initialSchool.phone || "");
        setEmail(initialSchool.email || "");
        if (initialSchool.letterhead_path) {
          const fullPath = initialSchool.letterhead_path.startsWith("http")
            ? initialSchool.letterhead_path
            : `${apiBase}${initialSchool.letterhead_path}`;
          setPreviewUrl(fullPath);
        } else {
          setPreviewUrl(null);
        }
      } else {
        setName("");
        setNpsn("");
        setLevel("SD");
        setAddress("");
        setSubdistrict("");
        setCity("Jakarta Pusat");
        setPostalCode("");
        setPhone("");
        setEmail("");
        setPreviewUrl(null);
      }
      setSelectedFile(null);
      setErrorMsg("");
    }
  }, [isOpen, initialSchool, apiBase]);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.match(/^image\/(png|jpe?g)$/)) {
      setErrorMsg("Format file kop harus PNG, JPG, atau JPEG.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setErrorMsg("Ukuran file banner maksimal 5MB.");
      return;
    }

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setErrorMsg("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMsg("Nama satuan pendidikan / sekolah wajib diisi.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg("");

    try {
      const payload = {
        name: name.trim(),
        npsn: npsn.trim() || undefined,
        level: level.trim() || "SD",
        address: address.trim() || "Jakarta",
        subdistrict: subdistrict.trim() || undefined,
        city: city.trim() || "Jakarta Pusat",
        postal_code: postalCode.trim() || undefined,
        phone: phone.trim() || undefined,
        email: email.trim() || undefined,
      };

      if (isEdit && initialSchool?.id) {
        await apiClient.updateSchool(initialSchool.id, payload);
        if (selectedFile) {
          await apiClient.uploadSchoolLetterhead(initialSchool.id, selectedFile);
        }
      } else {
        const created = await apiClient.createSchool(payload);
        if (selectedFile && created?.id) {
          await apiClient.uploadSchoolLetterhead(created.id, selectedFile);
        }
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Gagal menyimpan data sekolah.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4">
      <div className="bg-card border border-border w-full max-w-xl rounded-lg shadow-2xl overflow-hidden font-sans flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-5 py-3.5 bg-muted/40 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
              {isEdit ? "Edit Satuan Pendidikan / Sekolah" : "Tambah Satuan Pendidikan / Sekolah Baru"}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 overflow-y-auto text-xs flex-1">
          {errorMsg && (
            <div className="p-3 bg-red-500/15 border border-red-500/40 text-red-300 rounded-md flex items-center gap-2 shadow-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Section 1: Profil Sekolah */}
          <div className="space-y-3">
            <div className="text-[11px] font-mono uppercase text-muted-foreground font-semibold flex items-center gap-1.5 border-b border-border/80 pb-1">
              <Building2 className="w-3.5 h-3.5 text-primary" />
              <span>1. Identitas Satuan Pendidikan</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="md:col-span-2">
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Nama Resmi Sekolah (Wajib)
                </label>
                <input
                  type="text"
                  required
                  placeholder="Contoh: SDN CEMPAKA PUTIH BARAT 01"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Jenjang
                </label>
                <select
                  value={level}
                  onChange={(e) => setLevel(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                >
                  <option value="SD">SD (Sekolah Dasar)</option>
                  <option value="SMP">SMP (Sekolah Menengah Pertama)</option>
                  <option value="SMA">SMA (Sekolah Menengah Atas)</option>
                  <option value="SMK">SMK (Sekolah Menengah Kejuruan)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  NPSN (8 Digit)
                </label>
                <input
                  type="text"
                  maxLength={8}
                  placeholder="20108304"
                  value={npsn}
                  onChange={(e) => setNpsn(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono tabular-nums transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Kecamatan
                </label>
                <input
                  type="text"
                  placeholder="Cempaka Putih / Kemayoran"
                  value={subdistrict}
                  onChange={(e) => setSubdistrict(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Kota / Kabupaten
                </label>
                <input
                  type="text"
                  placeholder="Jakarta Pusat"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Alamat Lengkap
                </label>
                <input
                  type="text"
                  placeholder="Jl. Cempaka Putih Barat No. 12"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Kode Pos
                </label>
                <input
                  type="text"
                  placeholder="10520"
                  value={postalCode}
                  onChange={(e) => setPostalCode(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono tabular-nums transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  No. Telepon Sekolah
                </label>
                <input
                  type="text"
                  placeholder="021-4240000"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Email Resmi Sekolah
                </label>
                <input
                  type="email"
                  placeholder="sdncempakaputihbarat01@jakarta.go.id"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Banner Kop Surat Sekolah */}
          <div className="space-y-3 pt-2">
            <div className="text-[11px] font-mono uppercase text-muted-foreground font-semibold flex items-center justify-between border-b border-border/80 pb-1">
              <div className="flex items-center gap-1.5">
                <ImageIcon className="w-3.5 h-3.5 text-primary" />
                <span>2. Banner Kop Surat Sekolah (Opsional)</span>
              </div>
              <span className="text-[10px] text-muted-foreground lowercase">PNG, JPG, max 5MB</span>
            </div>

            <div className="border border-border/80 rounded-md p-3 bg-muted/20 space-y-2">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png, image/jpeg, image/jpg"
                onChange={handleFileChange}
                className="hidden"
              />

              {previewUrl ? (
                <div className="space-y-2">
                  <div className="relative border border-border rounded overflow-hidden bg-white/5 p-1 flex items-center justify-center max-h-24">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={previewUrl}
                      alt="Preview Kop Sekolah"
                      className="max-h-20 w-auto object-contain rounded"
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      {selectedFile ? `File dipilih: ${selectedFile.name}` : "Banner tersimpan"}
                    </span>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="text-[11px] text-primary hover:underline font-mono"
                    >
                      Ganti Banner
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-border hover:border-primary/50 cursor-pointer rounded p-4 flex flex-col items-center justify-center text-center transition bg-muted/10 hover:bg-muted/30"
                >
                  <Upload className="w-5 h-5 text-muted-foreground mb-1" />
                  <span className="font-semibold text-foreground text-xs">
                    Klik untuk Unggah Banner Kop Surat Sekolah
                  </span>
                  <span className="text-[10px] text-muted-foreground mt-0.5">
                    Banner horizontal (rasio ~5.5:1) otomatis menjadi header dokumen HPS, SPP, BAST, SPJ
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Compliance Notice */}
          <div className="p-3 bg-muted/30 border border-border rounded space-y-1 text-muted-foreground font-mono text-[10px] leading-relaxed">
            <div className="flex items-center gap-1.5 text-foreground font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Integritas Master Sekolah:</span>
            </div>
            <p>
              • Setiap sekolah memiliki SK dan daftar pejabat penandatangan sendiri.
            </p>
            <p>
              • Jika banner diunggah, dokumen SPJ resmi otomatis menggunakan kop grafis ini secara rapi.
            </p>
          </div>

          {/* Action Buttons */}
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
              disabled={isSubmitting || !name.trim()}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded bg-primary hover:bg-primary/90 text-primary-foreground transition shadow-xs disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Building2 className="w-3.5 h-3.5" />
              )}
              <span>{isEdit ? "Simpan Perubahan Sekolah" : "Daftarkan Sekolah Baru"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
