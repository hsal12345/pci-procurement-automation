"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient, AuthUser, getCurrentUser } from "@/lib/api-client";
import { UserRole } from "@/types/package";
import {
  Users,
  Search,
  Plus,
  RefreshCw,
  ShieldCheck,
  UserCheck,
  UserX,
  Pencil,
  Trash2,
  KeyRound,
  Mail,
  Clock,
  CheckCircle2,
  AlertCircle,
  X,
  Loader2,
  Shield,
} from "lucide-react";

const ROLE_OPTIONS: Array<{
  value: UserRole;
  label: string;
  badge: string;
  badgeClass: string;
  capabilities: string;
}> = [
  {
    value: "SYSTEM_ADMINISTRATOR",
    label: "Administrator Sistem",
    badge: "SYSADMIN",
    badgeClass: "bg-red-500/15 text-red-300 border-red-500/30",
    capabilities:
      "Akses penuh ke seluruh modul sistem, pengaturan master data, persetujuan darurat, serta manajemen akun pengguna & RBAC.",
  },
  {
    value: "ADMINISTRATION",
    label: "Staf Administrasi",
    badge: "ADMIN",
    badgeClass: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
    capabilities:
      "Membuat & mengedit draf paket pengadaan, impor spreadsheet Excel, kelola master sekolah/rekanan, validasi aturan, dan cetak 13 dokumen SPJ.",
  },
  {
    value: "FINANCE_DIRECTOR",
    label: "Direktur Keuangan",
    badge: "DIREKTUR",
    badgeClass: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    capabilities:
      "Meninjau paket Under Review, menyetujui (Approve) atau mengembalikan (Return) revisi, menerbitkan SPJ (Issue), membuka kembali (Reopen), dan membatalkan paket.",
  },
  {
    value: "LOGISTICS",
    label: "Petugas Logistik",
    badge: "LOGISTIK",
    badgeClass: "bg-blue-500/15 text-blue-300 border-blue-500/30",
    capabilities:
      "Mencatat fakta pengiriman (Surat Jalan, kurir, pelat kendaraan), hasil pemeriksaan barang (BAPB), dan mengunggah foto bukti serah terima lapangan.",
  },
];

function getRoleMeta(role: string) {
  return (
    ROLE_OPTIONS.find((r) => r.value === role) || {
      value: "ADMINISTRATION" as UserRole,
      label: role,
      badge: role,
      badgeClass: "bg-muted text-muted-foreground border-border",
      capabilities: "",
    }
  );
}

export default function UsersDashboardPage() {
  const queryClient = useQueryClient();
  const currentUser = getCurrentUser();

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("ALL");

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<AuthUser | null>(null);
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("ADMINISTRATION");
  const [isActive, setIsActive] = useState(true);
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    data: users = [],
    isLoading,
    error,
    refetch,
  } = useQuery<AuthUser[]>({
    queryKey: ["users"],
    queryFn: () => apiClient.getUsers(),
  });

  const filteredUsers = users.filter((u) => {
    const term = search.toLowerCase();
    const matchesSearch =
      u.full_name.toLowerCase().includes(term) ||
      u.username.toLowerCase().includes(term) ||
      u.email.toLowerCase().includes(term);
    const matchesRole = roleFilter === "ALL" || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const handleOpenCreate = () => {
    setEditingUser(null);
    setFullName("");
    setUsername("");
    setEmail("");
    setPassword("");
    setRole("ADMINISTRATION");
    setIsActive(true);
    setFormError("");
    setIsModalOpen(true);
  };

  const handleOpenEdit = (u: AuthUser) => {
    setEditingUser(u);
    setFullName(u.full_name);
    setUsername(u.username);
    setEmail(u.email);
    setPassword("");
    setRole(u.role);
    setIsActive(u.is_active);
    setFormError("");
    setIsModalOpen(true);
  };

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");

    if (!fullName.trim() || !username.trim() || !email.trim()) {
      setFormError("Nama lengkap, username, dan email wajib diisi.");
      return;
    }

    if (!editingUser && password.trim().length < 6) {
      setFormError("Kata sandi awal wajib diisi minimal 6 karakter.");
      return;
    }

    if (editingUser && password.trim() && password.trim().length < 6) {
      setFormError("Kata sandi baru minimal 6 karakter.");
      return;
    }

    setIsSubmitting(true);
    try {
      if (editingUser) {
        await apiClient.updateUser(editingUser.id, {
          full_name: fullName.trim(),
          username: username.trim(),
          email: email.trim(),
          role,
          is_active: isActive,
          ...(password.trim() ? { password: password.trim() } : {}),
        });
      } else {
        await apiClient.createUser({
          full_name: fullName.trim(),
          username: username.trim(),
          email: email.trim(),
          password: password.trim(),
          role,
          is_active: isActive,
        });
      }
      await queryClient.invalidateQueries({ queryKey: ["users"] });
      setIsModalOpen(false);
    } catch (err: any) {
      setFormError(err.message || "Gagal menyimpan data pengguna.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleActive = async (u: AuthUser) => {
    if (u.id === currentUser?.id) {
      alert("Anda tidak dapat menonaktifkan akun Administrator Anda sendiri yang sedang aktif.");
      return;
    }
    try {
      await apiClient.updateUser(u.id, { is_active: !u.is_active });
      await queryClient.invalidateQueries({ queryKey: ["users"] });
    } catch (err: any) {
      alert(err.message || "Gagal mengubah status pengguna.");
    }
  };

  const handleDeleteUser = async (u: AuthUser) => {
    if (u.id === currentUser?.id) {
      alert("Anda tidak dapat menghapus akun Anda sendiri yang sedang aktif.");
      return;
    }
    if (!confirm(`Hapus akun pengguna "${u.full_name}" (@${u.username}) secara permanen?`)) {
      return;
    }
    try {
      await apiClient.deleteUser(u.id);
      await queryClient.invalidateQueries({ queryKey: ["users"] });
    } catch (err: any) {
      alert(err.message || "Gagal menghapus pengguna.");
    }
  };

  const totalActive = users.filter((u) => u.is_active).length;

  return (
    <div className="flex flex-col h-full font-sans text-xs">
      {/* Top Action Bar */}
      <div className="h-12 border-b border-border px-4 flex items-center justify-between gap-4 bg-card/60">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-primary" />
          <h1 className="text-sm font-semibold tracking-tight text-foreground">
            Manajemen Pengguna &amp; Hak Akses (RBAC)
          </h1>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/30 font-semibold">
            {users.length} Akun ({totalActive} Aktif)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition"
            title="Segarkan Daftar Pengguna"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            onClick={handleOpenCreate}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary text-primary-foreground font-semibold text-xs hover:opacity-90 transition shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Tambah Pengguna Baru</span>
          </button>
        </div>
      </div>

      {/* Role Summary & Filter Bar */}
      <div className="border-b border-border px-4 py-3 bg-card/40 space-y-3">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
          {ROLE_OPTIONS.map((r) => {
            const count = users.filter((u) => u.role === r.value).length;
            const isSelected = roleFilter === r.value;
            return (
              <button
                key={r.value}
                type="button"
                onClick={() => setRoleFilter(isSelected ? "ALL" : r.value)}
                className={`p-2.5 rounded-lg border text-left transition flex flex-col justify-between gap-1 ${
                  isSelected
                    ? "border-primary bg-primary/10"
                    : "border-border bg-card hover:bg-muted/40"
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border ${r.badgeClass}`}>
                    {r.badge}
                  </span>
                  <span className="text-sm font-bold font-mono text-foreground">{count}</span>
                </div>
                <span className="text-xs font-medium text-foreground">{r.label}</span>
                <span className="text-[10px] text-muted-foreground line-clamp-2 leading-snug">
                  {r.capabilities}
                </span>
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="relative w-full max-w-md">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Cari nama lengkap, @username, atau email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-background border border-border rounded text-xs outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition"
            />
          </div>

          <div className="flex items-center gap-1.5 font-mono text-[11px]">
            {(["ALL", "SYSTEM_ADMINISTRATOR", "ADMINISTRATION", "FINANCE_DIRECTOR", "LOGISTICS"] as const).map(
              (rf) => (
                <button
                  key={rf}
                  type="button"
                  onClick={() => setRoleFilter(rf)}
                  className={`px-2.5 py-1 rounded border transition ${
                    roleFilter === rf
                      ? "bg-primary text-primary-foreground border-primary font-bold"
                      : "bg-card text-muted-foreground border-border hover:text-foreground"
                  }`}
                >
                  {rf === "ALL" ? "SEMUA PERAN" : getRoleMeta(rf).badge}
                </button>
              )
            )}
          </div>
        </div>
      </div>

      {/* Main Users Table */}
      <div className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-muted-foreground font-mono">
            Memuat daftar akun pengguna...
          </div>
        ) : error ? (
          <div className="p-4 border border-red-500/40 bg-red-500/10 rounded-lg text-red-200 font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400" />
            <span>Gagal memuat daftar pengguna: {(error as Error).message}</span>
          </div>
        ) : (
          <div className="border border-border rounded-lg bg-card overflow-hidden shadow-xs">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-muted/80 border-b border-border text-[11px] uppercase font-mono font-bold tracking-wider text-muted-foreground">
                  <th className="px-4 py-2.5">Pengguna</th>
                  <th className="px-4 py-2.5">Username &amp; Email</th>
                  <th className="px-4 py-2.5">Peran RBAC</th>
                  <th className="px-4 py-2.5">Status Akun</th>
                  <th className="px-4 py-2.5">Login Terakhir</th>
                  <th className="px-4 py-2.5 text-right">Tindakan Admin</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredUsers.map((u) => {
                  const meta = getRoleMeta(u.role);
                  const isSelf = u.id === currentUser?.id;

                  return (
                    <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-full bg-primary/15 border border-primary/30 text-primary flex items-center justify-center font-bold text-xs flex-shrink-0">
                            {u.full_name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-semibold text-foreground flex items-center gap-1.5">
                              <span>{u.full_name}</span>
                              {isSelf && (
                                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-primary/20 text-primary border border-primary/40">
                                  ANDA
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-muted-foreground line-clamp-1 max-w-xs">
                              {meta.label}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-3 font-mono text-[11px]">
                        <div className="text-foreground font-semibold">@{u.username}</div>
                        <div className="text-muted-foreground flex items-center gap-1">
                          <Mail className="w-3 h-3" />
                          <span>{u.email}</span>
                        </div>
                      </td>

                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${meta.badgeClass}`}
                        >
                          <Shield className="w-3 h-3" />
                          <span>{meta.badge}</span>
                        </span>
                      </td>

                      <td className="px-4 py-3 font-mono text-[11px]">
                        {u.is_active ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold text-[10px]">
                            <UserCheck className="w-3 h-3" />
                            <span>AKTIF</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-red-500/15 text-red-300 border border-red-500/30 font-semibold text-[10px]">
                            <UserX className="w-3 h-3" />
                            <span>NONAKTIF</span>
                          </span>
                        )}
                      </td>

                      <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground">
                        {u.last_login_at ? (
                          <span className="inline-flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>
                              {new Date(u.last_login_at).toLocaleString("id-ID", {
                                dateStyle: "short",
                                timeStyle: "short",
                              })}
                            </span>
                          </span>
                        ) : (
                          <span className="opacity-60">Belum pernah login</span>
                        )}
                      </td>

                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleOpenEdit(u)}
                            className="px-2.5 py-1 rounded border border-border bg-background hover:bg-muted text-foreground text-[11px] font-medium inline-flex items-center gap-1 transition"
                            title="Edit profil, peran RBAC, atau reset kata sandi"
                          >
                            <Pencil className="w-3 h-3" />
                            <span>Edit / Sandi</span>
                          </button>

                          <button
                            type="button"
                            disabled={isSelf}
                            onClick={() => handleToggleActive(u)}
                            className={`px-2 py-1 rounded border text-[11px] font-mono transition disabled:opacity-30 ${
                              u.is_active
                                ? "border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300"
                                : "border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300"
                            }`}
                            title={u.is_active ? "Nonaktifkan akun" : "Aktifkan kembali akun"}
                          >
                            {u.is_active ? "Nonaktifkan" : "Aktifkan"}
                          </button>

                          <button
                            type="button"
                            disabled={isSelf}
                            onClick={() => handleDeleteUser(u)}
                            className="p-1.5 rounded border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-red-300 transition disabled:opacity-30"
                            title="Hapus akun pengguna"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create / Edit User Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4">
          <div className="bg-card border border-border w-full max-w-lg rounded-xl shadow-2xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-border bg-muted/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-primary" />
                <span className="text-xs font-bold uppercase tracking-wider font-mono text-foreground">
                  {editingUser
                    ? `Edit Pengguna: @${editingUser.username}`
                    : "Tambah Pengguna Baru (Provisioning RBAC)"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveUser} className="p-5 space-y-4">
              {formError && (
                <div className="p-3 rounded-lg border border-red-500/40 bg-red-500/10 text-red-200 flex items-center gap-2 font-mono text-xs">
                  <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="block font-medium text-foreground">Nama Lengkap Pejabat / Staf</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="contoh: Budi Santoso, S.E."
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="block font-medium text-foreground">Username Login</label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="contoh: budi_admin"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground font-mono text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block font-medium text-foreground">Alamat Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="contoh: budi@pci.co.id"
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground font-mono text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block font-medium text-foreground flex items-center gap-1.5">
                  <KeyRound className="w-3.5 h-3.5 text-amber-400" />
                  <span>
                    {editingUser
                      ? "Reset Kata Sandi (Kosongkan jika tidak ingin mengubah sandi)"
                      : "Kata Sandi Awal (Min. 6 Karakter)"}
                  </span>
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={
                    editingUser
                      ? "Biarkan kosong untuk mempertahankan kata sandi lama"
                      : "Masukkan kata sandi awal untuk pengguna ini"
                  }
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground font-mono text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              <div className="space-y-2">
                <label className="block font-medium text-foreground">Pilih Peran &amp; Kewenangan (RBAC)</label>
                <div className="grid grid-cols-1 gap-2">
                  {ROLE_OPTIONS.map((opt) => {
                    const selected = role === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setRole(opt.value)}
                        className={`p-2.5 rounded-lg border text-left transition flex items-start justify-between gap-3 ${
                          selected
                            ? "border-primary bg-primary/10 ring-1 ring-primary/40"
                            : "border-border bg-background/60 hover:bg-muted/40"
                        }`}
                      >
                        <div className="space-y-0.5">
                          <div className="font-semibold text-foreground flex items-center gap-2">
                            <span>{opt.label}</span>
                            <span
                              className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded border ${opt.badgeClass}`}
                            >
                              {opt.badge}
                            </span>
                          </div>
                          <p className="text-[11px] text-muted-foreground leading-snug">
                            {opt.capabilities}
                          </p>
                        </div>
                        <div
                          className={`w-4 h-4 rounded-full border flex items-center justify-center flex-shrink-0 mt-0.5 ${
                            selected ? "border-primary bg-primary text-primary-foreground" : "border-muted-foreground"
                          }`}
                        >
                          {selected && <CheckCircle2 className="w-3 h-3" />}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    disabled={editingUser?.id === currentUser?.id}
                    className="rounded border-border"
                  />
                  <span className="text-xs font-medium text-foreground">
                    Status Akun Aktif (Diizinkan Masuk Sistem)
                  </span>
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3.5 py-2 rounded-lg border border-border bg-card hover:bg-muted text-muted-foreground text-xs font-medium"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-xs hover:opacity-90 flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                >
                  {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{editingUser ? "Simpan Perubahan" : "Buat Akun Pengguna"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

