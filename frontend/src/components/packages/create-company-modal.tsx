"use client";

import { useState, useEffect, useRef } from "react";
import { apiClient } from "@/lib/api-client";
import {
  Landmark,
  X,
  Loader2,
  AlertCircle,
  Building,
  CreditCard,
  UserCheck,
  ShieldCheck,
  Upload,
  Image as ImageIcon,
  CheckCircle2,
} from "lucide-react";

interface CreateCompanyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated?: (newCompany: any) => void;
  onSuccess?: () => void;
  initialCompany?: any | null;
}

export function CreateCompanyModal({
  isOpen,
  onClose,
  onCreated,
  onSuccess,
  initialCompany,
}: CreateCompanyModalProps) {
  const isEdit = Boolean(initialCompany?.id);

  const [legalName, setLegalName] = useState("");
  const [npwp, setNpwp] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("Jakarta");
  const [postalCode, setPostalCode] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [directorName, setDirectorName] = useState("");
  const [directorTitle, setDirectorTitle] = useState("Direktur");
  const [directorSkNumber, setDirectorSkNumber] = useState("Akta Notaris No. 12 Th 2020");
  const [bankName, setBankName] = useState("Bank BJB / Bank Mandiri");
  const [bankAccountNumber, setBankAccountNumber] = useState("");
  const [bankAccountHolder, setBankAccountHolder] = useState("");

  // Letterhead / Logo Image state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

  useEffect(() => {
    if (isOpen) {
      if (initialCompany) {
        setLegalName(initialCompany.legal_name || initialCompany.name || "");
        setNpwp(initialCompany.npwp || "");
        setAddress(initialCompany.address || "");
        setCity(initialCompany.city || "Jakarta");
        setPostalCode(initialCompany.postal_code || "");
        setEmail(initialCompany.email || "");
        setPhone(initialCompany.phone || "");
        setDirectorName(initialCompany.director_name || "");
        setDirectorTitle(initialCompany.director_title || "Direktur");
        setDirectorSkNumber(initialCompany.director_sk_number || "Akta Notaris No. 12 Th 2020");
        setBankName(initialCompany.bank_name || "Bank DKI");
        setBankAccountNumber(initialCompany.bank_account_number || "");
        setBankAccountHolder(initialCompany.bank_account_holder || initialCompany.legal_name || "");
        if (initialCompany.logo_path) {
          const fullPath = initialCompany.logo_path.startsWith("http")
            ? initialCompany.logo_path
            : `${apiBase}/${initialCompany.logo_path.replace(/^\/+/, "")}`;
          setPreviewUrl(fullPath);
        } else {
          setPreviewUrl(null);
        }
      } else {
        // Reset defaults
        setLegalName("");
        setNpwp("");
        setAddress("");
        setCity("Jakarta");
        setPostalCode("");
        setEmail("");
        setPhone("");
        setDirectorName("");
        setDirectorTitle("Direktur");
        setDirectorSkNumber("Akta Notaris No. 12 Th 2020");
        setBankName("Bank DKI");
        setBankAccountNumber("");
        setBankAccountHolder("");
        setPreviewUrl(null);
      }
      setSelectedFile(null);
      setErrorMsg("");
    }
  }, [isOpen, initialCompany, apiBase]);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.match(/^image\/(png|jpe?g)$/)) {
      setErrorMsg("Format file harus berupa PNG, JPG, atau JPEG.");
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
    if (!legalName.trim()) {
      setErrorMsg("Nama legal badan usaha/rekanan wajib diisi.");
      return;
    }
    if (!directorName.trim()) {
      setErrorMsg("Nama direktur / pimpinan rekanan wajib diisi.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg("");

    try {
      const payload = {
        legal_name: legalName.trim(),
        npwp: npwp.trim() || undefined,
        address: address.trim() || "Jakarta",
        city: city.trim() || "Jakarta",
        postal_code: postalCode.trim() || undefined,
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
        director_name: directorName.trim(),
        director_title: directorTitle.trim() || "Direktur",
        director_sk_number: directorSkNumber.trim() || undefined,
        bank_name: bankName.trim() || undefined,
        bank_account_number: bankAccountNumber.trim() || undefined,
        bank_account_holder: bankAccountHolder.trim() || legalName.trim(),
        is_active: true,
      };

      let companyResult: any;

      if (isEdit && initialCompany?.id) {
        companyResult = await apiClient.updateCompany(initialCompany.id, payload);
        if (selectedFile) {
          await apiClient.uploadCompanyLogo(initialCompany.id, selectedFile);
        }
      } else {
        companyResult = await apiClient.createCompany(payload);
        if (selectedFile && companyResult?.id) {
          await apiClient.uploadCompanyLogo(companyResult.id, selectedFile);
        }
      }

      if (onCreated) onCreated(companyResult);
      if (onSuccess) onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Gagal menyimpan data rekanan.");
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
            <Landmark className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
              {isEdit ? "Edit Data Rekanan Penyedia" : "Tambah Badan Usaha / Rekanan Penyedia Baru"}
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

          {/* Section 1: Badan Usaha */}
          <div className="space-y-3">
            <div className="text-[11px] font-mono uppercase text-muted-foreground font-semibold flex items-center gap-1.5 border-b border-border/80 pb-1">
              <Building className="w-3.5 h-3.5 text-primary" />
              <span>1. Identitas Badan Usaha</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="md:col-span-2">
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Nama Badan Usaha / Perusahaan (Wajib)
                </label>
                <input
                  type="text"
                  required
                  placeholder="Contoh: CV. Pustaka Cemerlang Indonesia / PT. Sarana Edukasi"
                  value={legalName}
                  onChange={(e) => {
                    setLegalName(e.target.value);
                    if (!bankAccountHolder) setBankAccountHolder(e.target.value);
                  }}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  NPWP Perusahaan (16 Digit Text)
                </label>
                <input
                  type="text"
                  placeholder="01.234.567.8-012.000"
                  value={npwp}
                  onChange={(e) => setNpwp(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono tabular-nums transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Kota / Kabupaten
                </label>
                <input
                  type="text"
                  placeholder="Jakarta Pusat / Jakarta Selatan"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Alamat Lengkap Perusahaan
                </label>
                <input
                  type="text"
                  placeholder="Jl. Salemba Raya No. 10, Kel. Paseban"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  No. Telepon / WhatsApp
                </label>
                <input
                  type="text"
                  placeholder="021-8888888 / 081234567890"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Email Perusahaan
                </label>
                <input
                  type="email"
                  placeholder="kontak@perusahaan.co.id"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Direktur / Pejabat Rekanan */}
          <div className="space-y-3 pt-2">
            <div className="text-[11px] font-mono uppercase text-muted-foreground font-semibold flex items-center gap-1.5 border-b border-border/80 pb-1">
              <UserCheck className="w-3.5 h-3.5 text-sky-400" />
              <span>2. Direktur & Legalitas SK Notaris</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="md:col-span-2">
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Nama Direktur Utama / Pimpinan (Wajib)
                </label>
                <input
                  type="text"
                  required
                  placeholder="Contoh: Bambang Solifian / Ir. Gunawan"
                  value={directorName}
                  onChange={(e) => setDirectorName(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Jabatan Resmi
                </label>
                <input
                  type="text"
                  placeholder="Direktur / Direktur Utama"
                  value={directorTitle}
                  onChange={(e) => setDirectorTitle(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div className="md:col-span-3">
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Nomor Akta Notaris / SK Direksi (SK Penugasan)
                </label>
                <input
                  type="text"
                  placeholder="Contoh: Akta Notaris No. 12 Th 2020 / SK Direksi No. 001/SK/2022"
                  value={directorSkNumber}
                  onChange={(e) => setDirectorSkNumber(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono transition"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Data Bank Pembayaran */}
          <div className="space-y-3 pt-2">
            <div className="text-[11px] font-mono uppercase text-muted-foreground font-semibold flex items-center gap-1.5 border-b border-border/80 pb-1">
              <CreditCard className="w-3.5 h-3.5 text-amber-400" />
              <span>3. Data Rekening Bank Rekanan</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Nama Bank
                </label>
                <input
                  type="text"
                  placeholder="Bank DKI / Mandiri / BCA"
                  value={bankName}
                  onChange={(e) => setBankName(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Nomor Rekening
                </label>
                <input
                  type="text"
                  placeholder="0012345678901"
                  value={bankAccountNumber}
                  onChange={(e) => setBankAccountNumber(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-mono tabular-nums transition"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Atas Nama Rekening
                </label>
                <input
                  type="text"
                  placeholder="Sesuai buku rekening"
                  value={bankAccountHolder}
                  onChange={(e) => setBankAccountHolder(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary font-sans transition"
                />
              </div>
            </div>
          </div>

          {/* Section 4: Kop Surat Banner Rekanan */}
          <div className="space-y-3 pt-2">
            <div className="text-[11px] font-mono uppercase text-muted-foreground font-semibold flex items-center justify-between border-b border-border/80 pb-1">
              <div className="flex items-center gap-1.5">
                <ImageIcon className="w-3.5 h-3.5 text-emerald-400" />
                <span>4. Banner Kop Surat Rekanan (Opsional)</span>
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
                      alt="Preview Kop Surat"
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
                    Klik untuk Unggah Banner Kop Surat
                  </span>
                  <span className="text-[10px] text-muted-foreground mt-0.5">
                    Banner horizontal (rasio ~5:1) otomatis menjadi header dokumen Word & PDF
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* PRD Compliance Notice */}
          <div className="p-3 bg-muted/30 border border-border rounded space-y-1 text-muted-foreground font-mono text-[10px] leading-relaxed">
            <div className="flex items-center gap-1.5 text-foreground font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Integritas Master Rekanan:</span>
            </div>
            <p>
              • Rekanan yang terdaftar dapat dipilih di Tab Identitas pada setiap paket pengadaan.
            </p>
            <p>
              • Jika banner diunggah, dokumen otomatis menggunakan kop grafis ini sebagai header resmi.
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
              disabled={isSubmitting || !legalName.trim() || !directorName.trim()}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-xs disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Landmark className="w-3.5 h-3.5" />
              )}
              <span>{isEdit ? "Simpan Perubahan Rekanan" : "Daftarkan Rekanan Baru"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
