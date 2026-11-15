"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { formatIDR } from "@/lib/formatters";
import {
  Package,
  Landmark,
  Ruler,
  Search,
  Plus,
  Pencil,
  PowerOff,
  Power,
  RefreshCw,
  DollarSign,
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

type CatalogTab = "ITEMS" | "BUDGETS" | "UNITS_FUNDS";

export default function CatalogAndBudgetPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<CatalogTab>("ITEMS");
  const [search, setSearch] = useState("");
  const [showInactive, setShowInactive] = useState(true);
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Item modal state
  const [itemModalOpen, setItemModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<any | null>(null);
  const [itemForm, setItemForm] = useState({
    sku: "",
    kbli: "",
    canonical_description: "",
    default_spec: "",
    brand: "",
    category: "",
    default_unit: "Eks",
    reference_price: "0",
    is_active: true,
  });

  // Budget modal state
  const [budgetModalOpen, setBudgetModalOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<any | null>(null);
  const [budgetForm, setBudgetForm] = useState({
    fiscal_year: 2026,
    activity_code: "",
    activity_name: "",
    sub_activity: "",
    account_code: "",
    account_name: "",
    funding_source_code: "BOS",
    funding_scheme: "BOS_REGULER",
    is_active: true,
  });

  // Unit & Funding Source forms
  const [unitForm, setUnitForm] = useState({ code: "", display_label: "", allowed_fractional: false });
  const [fsForm, setFsForm] = useState({ code: "", name: "", description: "" });

  const { data: items = [], isLoading: isLoadingItems, refetch: refetchItems } = useQuery<any[]>({
    queryKey: ["master-items"],
    queryFn: () => apiClient.getItems(),
  });

  const { data: budgets = [], isLoading: isLoadingBudgets, refetch: refetchBudgets } = useQuery<any[]>({
    queryKey: ["master-budgets"],
    queryFn: () => apiClient.getBudgets(),
  });

  const { data: units = [], refetch: refetchUnits } = useQuery<any[]>({
    queryKey: ["master-units"],
    queryFn: () => apiClient.getUnits(),
  });

  const { data: fundingSources = [], refetch: refetchFs } = useQuery<any[]>({
    queryKey: ["master-funding-sources"],
    queryFn: () => apiClient.getFundingSources(),
  });

  const showToast = (type: "success" | "error", text: string) => {
    setNotice({ type, text });
    setTimeout(() => setNotice(null), 5000);
  };

  // Item Mutations
  const saveItemMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        sku: itemForm.sku.trim() || null,
        kbli: itemForm.kbli.trim() || null,
        canonical_description: itemForm.canonical_description.trim(),
        default_spec: itemForm.default_spec.trim() || null,
        brand: itemForm.brand.trim() || null,
        category: itemForm.category.trim() || null,
        default_unit: itemForm.default_unit.trim() || "Pcs",
        reference_price: Number(itemForm.reference_price) || 0,
        is_active: itemForm.is_active,
      };
      if (editingItem) {
        return apiClient.updateItem(editingItem.id, payload);
      }
      return apiClient.createItem(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["master-items"] });
      setItemModalOpen(false);
      showToast("success", editingItem ? "Item katalog diperbarui." : "Item baru ditambahkan ke katalog.");
    },
    onError: (err: any) => showToast("error", err.message || "Gagal menyimpan item katalog."),
  });

  const updatePriceMutation = useMutation({
    mutationFn: ({ id, price }: { id: string; price: number }) => apiClient.updateItemPrice(id, price),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["master-items"] });
      showToast("success", "Harga acuan katalog berhasil diperbarui (updateHarga).");
    },
    onError: (err: any) => showToast("error", err.message || "Gagal memperbarui harga acuan."),
  });

  const toggleItemActiveMutation = useMutation({
    mutationFn: async (item: any) => {
      if (item.is_active) {
        return apiClient.deleteItem(item.id);
      }
      return apiClient.updateItem(item.id, { is_active: true });
    },
    onSuccess: (res: any) => {
      queryClient.invalidateQueries({ queryKey: ["master-items"] });
      showToast("success", res?.message || "Status item katalog diperbarui (UC-01 2a).");
    },
    onError: (err: any) => showToast("error", err.message || "Gagal mengubah status item."),
  });

  // Budget Mutations
  const saveBudgetMutation = useMutation({
    mutationFn: async () => {
      const payload = { ...budgetForm, fiscal_year: Number(budgetForm.fiscal_year) || 2026 };
      if (editingBudget) {
        return apiClient.updateBudget(editingBudget.id, payload);
      }
      return apiClient.createBudget(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["master-budgets"] });
      setBudgetModalOpen(false);
      showToast("success", editingBudget ? "Rekening anggaran diperbarui." : "Rekening anggaran BOS/BOP ditambahkan.");
    },
    onError: (err: any) => showToast("error", err.message || "Gagal menyimpan rekening anggaran."),
  });

  const toggleBudgetActiveMutation = useMutation({
    mutationFn: async (b: any) => {
      if (b.is_active) {
        return apiClient.deleteBudget(b.id);
      }
      return apiClient.updateBudget(b.id, { is_active: true });
    },
    onSuccess: (res: any) => {
      queryClient.invalidateQueries({ queryKey: ["master-budgets"] });
      showToast("success", res?.message || "Status kode rekening diperbarui (UC-01 2a).");
    },
    onError: (err: any) => showToast("error", err.message || "Gagal mengubah status rekening."),
  });

  const createUnitMutation = useMutation({
    mutationFn: () => apiClient.createUnit(unitForm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["master-units"] });
      setUnitForm({ code: "", display_label: "", allowed_fractional: false });
      showToast("success", "Satuan baru ditambahkan.");
    },
    onError: (err: any) => showToast("error", err.message || "Gagal menambah satuan."),
  });

  const createFsMutation = useMutation({
    mutationFn: () => apiClient.createFundingSource({ ...fsForm, is_active: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["master-funding-sources"] });
      setFsForm({ code: "", name: "", description: "" });
      showToast("success", "Sumber dana ditambahkan.");
    },
    onError: (err: any) => showToast("error", err.message || "Gagal menambah sumber dana."),
  });

  const openAddItemModal = () => {
    setEditingItem(null);
    setItemForm({
      sku: "",
      kbli: "",
      canonical_description: "",
      default_spec: "",
      brand: "",
      category: "",
      default_unit: units[0]?.code || "Eks",
      reference_price: "0",
      is_active: true,
    });
    setItemModalOpen(true);
  };

  const openEditItemModal = (item: any) => {
    setEditingItem(item);
    setItemForm({
      sku: item.sku || "",
      kbli: item.kbli || "",
      canonical_description: item.canonical_description || "",
      default_spec: item.default_spec || "",
      brand: item.brand || "",
      category: item.category || "",
      default_unit: item.default_unit || "Eks",
      reference_price: String(item.reference_price ?? 0),
      is_active: item.is_active ?? true,
    });
    setItemModalOpen(true);
  };

  const openAddBudgetModal = () => {
    setEditingBudget(null);
    setBudgetForm({
      fiscal_year: 2026,
      activity_code: "",
      activity_name: "",
      sub_activity: "",
      account_code: "",
      account_name: "",
      funding_source_code: "BOS",
      funding_scheme: "BOS_REGULER",
      is_active: true,
    });
    setBudgetModalOpen(true);
  };

  const openEditBudgetModal = (b: any) => {
    setEditingBudget(b);
    setBudgetForm({
      fiscal_year: b.fiscal_year || 2026,
      activity_code: b.activity_code || "",
      activity_name: b.activity_name || "",
      sub_activity: b.sub_activity || "",
      account_code: b.account_code || "",
      account_name: b.account_name || "",
      funding_source_code: b.funding_source_code || "BOS",
      funding_scheme: b.funding_scheme || "BOS_REGULER",
      is_active: b.is_active ?? true,
    });
    setBudgetModalOpen(true);
  };

  const filteredItems = items.filter((it) => {
    if (!showInactive && !it.is_active) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (it.canonical_description || "").toLowerCase().includes(q) ||
      (it.sku || "").toLowerCase().includes(q) ||
      (it.kbli || "").toLowerCase().includes(q) ||
      (it.category || "").toLowerCase().includes(q)
    );
  });

  const filteredBudgets = budgets.filter((b) => {
    if (!showInactive && !b.is_active) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (b.activity_name || "").toLowerCase().includes(q) ||
      (b.account_name || "").toLowerCase().includes(q) ||
      (b.account_code || "").toLowerCase().includes(q) ||
      (b.activity_code || "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex flex-col h-full">
      {/* Top Bar */}
      <div className="h-12 border-b border-border px-4 flex items-center justify-between gap-4 bg-card/60">
        <div className="flex items-center gap-2">
          <Package className="w-4 h-4 text-primary" />
          <h1 className="text-sm font-semibold tracking-tight text-foreground">
            Master Katalog Barang, Satuan &amp; Kode Rekening BOS/BOP (FR-01 / UC-01)
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              refetchItems();
              refetchBudgets();
              refetchUnits();
              refetchFs();
            }}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted transition"
            title="Muat Ulang"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          {activeTab === "ITEMS" && (
            <button
              type="button"
              onClick={openAddItemModal}
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded bg-primary text-primary-foreground hover:opacity-90 transition shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Tambah Barang / Jasa</span>
            </button>
          )}
          {activeTab === "BUDGETS" && (
            <button
              type="button"
              onClick={openAddBudgetModal}
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded bg-primary text-primary-foreground hover:opacity-90 transition shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Tambah Kode Rekening</span>
            </button>
          )}
        </div>
      </div>

      {/* Toast Notification */}
      {notice && (
        <div
          className={`px-4 py-2 text-xs flex items-center gap-2 border-b ${
            notice.type === "error"
              ? "bg-red-500/15 border-red-500/30 text-red-300"
              : "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"
          }`}
        >
          {notice.type === "error" ? (
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          )}
          <span>{notice.text}</span>
        </div>
      )}

      {/* Sub-navigation Tabs */}
      <div className="border-b border-border px-4 bg-muted/20 flex flex-wrap items-center justify-between gap-3 py-2">
        <div className="flex items-center gap-1.5 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("ITEMS")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition border ${
              activeTab === "ITEMS"
                ? "bg-primary text-primary-foreground border-primary shadow-xs"
                : "bg-card text-muted-foreground hover:text-foreground border-border"
            }`}
          >
            <Package className="w-3.5 h-3.5" />
            <span>Katalog Barang &amp; Harga Acuan ({items.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("BUDGETS")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition border ${
              activeTab === "BUDGETS"
                ? "bg-primary text-primary-foreground border-primary shadow-xs"
                : "bg-card text-muted-foreground hover:text-foreground border-border"
            }`}
          >
            <Landmark className="w-3.5 h-3.5" />
            <span>Kode Rekening &amp; Kegiatan BOS/BOP ({budgets.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("UNITS_FUNDS")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition border ${
              activeTab === "UNITS_FUNDS"
                ? "bg-primary text-primary-foreground border-primary shadow-xs"
                : "bg-card text-muted-foreground hover:text-foreground border-border"
            }`}
          >
            <Ruler className="w-3.5 h-3.5" />
            <span>Satuan ({units.length}) &amp; Sumber Dana ({fundingSources.length})</span>
          </button>
        </div>

        {activeTab !== "UNITS_FUNDS" && (
          <div className="flex items-center gap-3 text-xs">
            <div className="relative w-64">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-muted-foreground" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={activeTab === "ITEMS" ? "Cari SKU, KBLI, nama barang..." : "Cari kode rekening, kegiatan..."}
                className="w-full pl-8 pr-2.5 py-1 bg-background border border-border rounded text-xs outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <label className="flex items-center gap-1.5 text-[11px] font-mono text-muted-foreground cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showInactive}
                onChange={(e) => setShowInactive(e.target.checked)}
                className="rounded border-border"
              />
              <span>Tampilkan Nonaktif</span>
            </label>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === "ITEMS" && (
          <div className="border border-border rounded-lg bg-card overflow-hidden shadow-xs">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-muted/60 border-b border-border text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  <th className="px-3 py-2.5 w-28">SKU</th>
                  <th className="px-3 py-2.5 w-24">KBLI</th>
                  <th className="px-3 py-2.5 min-w-[220px]">Nama Barang / Jasa &amp; Spesifikasi</th>
                  <th className="px-3 py-2.5 w-28">Kategori / Merek</th>
                  <th className="px-3 py-2.5 w-20 text-center">Satuan</th>
                  <th className="px-3 py-2.5 w-36 text-right">Harga Acuan (HPS)</th>
                  <th className="px-3 py-2.5 w-24 text-center">Status</th>
                  <th className="px-3 py-2.5 w-36 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {isLoadingItems ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-muted-foreground font-mono">
                      Memuat katalog barang...
                    </td>
                  </tr>
                ) : filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-muted-foreground font-mono">
                      Belum ada item katalog sesuai filter.
                    </td>
                  </tr>
                ) : (
                  filteredItems.map((item) => (
                    <tr
                      key={item.id}
                      className={`hover:bg-muted/20 transition ${!item.is_active ? "opacity-55 bg-muted/10" : ""}`}
                    >
                      <td className="px-3 py-2 font-mono font-semibold text-primary">
                        {item.sku || "-"}
                      </td>
                      <td className="px-3 py-2 font-mono text-muted-foreground">
                        {item.kbli || "-"}
                      </td>
                      <td className="px-3 py-2">
                        <div className="font-semibold text-foreground">{item.canonical_description}</div>
                        {item.default_spec && (
                          <div className="text-[11px] text-muted-foreground truncate max-w-md">
                            {item.default_spec}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-[11px] text-muted-foreground">
                        <div>{item.category || "-"}</div>
                        {item.brand && <div className="font-mono text-[10px]">{item.brand}</div>}
                      </td>
                      <td className="px-3 py-2 text-center font-mono">{item.default_unit || "Pcs"}</td>
                      <td className="px-3 py-2 text-right font-mono font-bold tabular-nums text-foreground">
                        {formatIDR(Number(item.reference_price || 0))}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded border font-semibold ${
                            item.is_active
                              ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                              : "bg-zinc-500/15 text-zinc-400 border-zinc-500/30"
                          }`}
                        >
                          {item.is_active ? "AKTIF" : "NONAKTIF"}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => {
                              const input = prompt(
                                `Masukkan Harga Acuan baru (IDR) untuk "${item.canonical_description}":`,
                                String(item.reference_price || 0)
                              );
                              if (input !== null) {
                                const parsed = Number(input.replace(/[^0-9.]/g, ""));
                                if (!isNaN(parsed) && parsed >= 0) {
                                  updatePriceMutation.mutate({ id: item.id, price: parsed });
                                }
                              }
                            }}
                            title="Update Harga Acuan (updateHarga)"
                            className="p-1.5 rounded hover:bg-muted text-emerald-400 transition"
                          >
                            <DollarSign className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => openEditItemModal(item)}
                            title="Edit Item"
                            className="p-1.5 rounded hover:bg-muted text-foreground transition"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const actionText = item.is_active ? "nonaktifkan / hapus" : "aktifkan kembali";
                              if (confirm(`Apakah Anda yakin ingin ${actionText} "${item.canonical_description}"?`)) {
                                toggleItemActiveMutation.mutate(item);
                              }
                            }}
                            title={item.is_active ? "Nonaktifkan / Hapus (UC-01 2a)" : "Aktifkan Kembali"}
                            className={`p-1.5 rounded hover:bg-muted transition ${
                              item.is_active ? "text-amber-400" : "text-emerald-400"
                            }`}
                          >
                            {item.is_active ? <PowerOff className="w-3.5 h-3.5" /> : <Power className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === "BUDGETS" && (
          <div className="border border-border rounded-lg bg-card overflow-hidden shadow-xs">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-muted/60 border-b border-border text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  <th className="px-3 py-2.5 w-16 text-center">TA</th>
                  <th className="px-3 py-2.5 w-28">Skema Dana</th>
                  <th className="px-3 py-2.5 w-40">Kode Rekening</th>
                  <th className="px-3 py-2.5 min-w-[200px]">Nama Rekening Belanja</th>
                  <th className="px-3 py-2.5 min-w-[240px]">Rincian Kegiatan BOS/BOP</th>
                  <th className="px-3 py-2.5 w-24 text-center">Status</th>
                  <th className="px-3 py-2.5 w-24 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {isLoadingBudgets ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-muted-foreground font-mono">
                      Memuat daftar kode rekening...
                    </td>
                  </tr>
                ) : filteredBudgets.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-muted-foreground font-mono">
                      Belum ada data kode rekening anggaran.
                    </td>
                  </tr>
                ) : (
                  filteredBudgets.map((b) => (
                    <tr
                      key={b.id}
                      className={`hover:bg-muted/20 transition ${!b.is_active ? "opacity-55 bg-muted/10" : ""}`}
                    >
                      <td className="px-3 py-2 text-center font-mono font-bold">{b.fiscal_year}</td>
                      <td className="px-3 py-2">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/15 text-primary border border-primary/30 font-semibold">
                          {b.funding_scheme}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono font-semibold text-foreground">
                        {b.account_code || "-"}
                      </td>
                      <td className="px-3 py-2 text-foreground">{b.account_name}</td>
                      <td className="px-3 py-2">
                        <div className="font-medium text-foreground">
                          {b.activity_code ? `[${b.activity_code}] ` : ""}
                          {b.activity_name}
                        </div>
                        {b.sub_activity && (
                          <div className="text-[11px] text-muted-foreground">{b.sub_activity}</div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded border font-semibold ${
                            b.is_active
                              ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                              : "bg-zinc-500/15 text-zinc-400 border-zinc-500/30"
                          }`}
                        >
                          {b.is_active ? "AKTIF" : "NONAKTIF"}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => openEditBudgetModal(b)}
                            className="p-1.5 rounded hover:bg-muted text-foreground transition"
                            title="Edit Rekening"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => toggleBudgetActiveMutation.mutate(b)}
                            className={`p-1.5 rounded hover:bg-muted transition ${
                              b.is_active ? "text-amber-400" : "text-emerald-400"
                            }`}
                            title={b.is_active ? "Nonaktifkan (UC-01 2a)" : "Aktifkan Kembali"}
                          >
                            {b.is_active ? <PowerOff className="w-3.5 h-3.5" /> : <Power className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === "UNITS_FUNDS" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Units Card */}
            <div className="border border-border rounded-lg bg-card p-4 space-y-4">
              <h3 className="text-sm font-semibold text-foreground border-b border-border pb-2">
                Master Satuan Barang (`Unit`)
              </h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Kode (mis: Eks, Set)"
                  value={unitForm.code}
                  onChange={(e) => setUnitForm({ ...unitForm, code: e.target.value })}
                  className="w-32 px-2.5 py-1.5 bg-background border border-border rounded text-xs font-mono"
                />
                <input
                  type="text"
                  placeholder="Label Tampilan (mis: Eksemplar)"
                  value={unitForm.display_label}
                  onChange={(e) => setUnitForm({ ...unitForm, display_label: e.target.value })}
                  className="flex-1 px-2.5 py-1.5 bg-background border border-border rounded text-xs"
                />
                <button
                  type="button"
                  disabled={!unitForm.code.trim() || !unitForm.display_label.trim()}
                  onClick={() => createUnitMutation.mutate()}
                  className="px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-semibold disabled:opacity-50"
                >
                  + Tambah
                </button>
              </div>
              <div className="divide-y divide-border/60 border border-border rounded overflow-hidden">
                {units.map((u) => (
                  <div key={u.id} className="px-3 py-2 flex items-center justify-between text-xs bg-background/40">
                    <div>
                      <span className="font-mono font-bold text-primary mr-2">{u.code}</span>
                      <span className="text-foreground">{u.display_label}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm(`Hapus satuan '${u.code}'?`)) {
                          apiClient.deleteUnit(u.id).then(() => refetchUnits());
                        }
                      }}
                      className="text-[11px] font-mono text-red-400 hover:underline"
                    >
                      Hapus
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Funding Sources Card */}
            <div className="border border-border rounded-lg bg-card p-4 space-y-4">
              <h3 className="text-sm font-semibold text-foreground border-b border-border pb-2">
                Master Sumber Dana Anggaran (`FundingSource`)
              </h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Kode (mis: BOS_DAERAH)"
                  value={fsForm.code}
                  onChange={(e) => setFsForm({ ...fsForm, code: e.target.value.toUpperCase() })}
                  className="w-36 px-2.5 py-1.5 bg-background border border-border rounded text-xs font-mono"
                />
                <input
                  type="text"
                  placeholder="Nama Sumber Dana"
                  value={fsForm.name}
                  onChange={(e) => setFsForm({ ...fsForm, name: e.target.value })}
                  className="flex-1 px-2.5 py-1.5 bg-background border border-border rounded text-xs"
                />
                <button
                  type="button"
                  disabled={!fsForm.code.trim() || !fsForm.name.trim()}
                  onClick={() => createFsMutation.mutate()}
                  className="px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-semibold disabled:opacity-50"
                >
                  + Tambah
                </button>
              </div>
              <div className="divide-y divide-border/60 border border-border rounded overflow-hidden">
                {fundingSources.map((fs) => (
                  <div key={fs.id} className="px-3 py-2 flex items-center justify-between text-xs bg-background/40">
                    <div>
                      <span className="font-mono font-bold text-emerald-400 mr-2">{fs.code}</span>
                      <span className="text-foreground font-medium">{fs.name}</span>
                      {fs.description && (
                        <div className="text-[10px] text-muted-foreground">{fs.description}</div>
                      )}
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400">
                      {fs.is_active ? "AKTIF" : "NONAKTIF"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Add/Edit Item Modal */}
      {itemModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground">
                {editingItem ? "Edit Item Katalog Barang" : "Tambah Item ke Katalog Barang"}
              </h2>
              <button type="button" onClick={() => setItemModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">
                    Kode SKU (Unik)
                  </label>
                  <input
                    type="text"
                    value={itemForm.sku}
                    onChange={(e) => setItemForm({ ...itemForm, sku: e.target.value })}
                    placeholder="PCI-BK-003"
                    className="w-full px-2.5 py-1.5 bg-background border border-border rounded font-mono"
                  />
                </div>
                <div>
                  <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">
                    Kode KBLI (SIPLah)
                  </label>
                  <input
                    type="text"
                    value={itemForm.kbli}
                    onChange={(e) => setItemForm({ ...itemForm, kbli: e.target.value })}
                    placeholder="47611"
                    className="w-full px-2.5 py-1.5 bg-background border border-border rounded font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">
                  Nama Barang / Jasa *
                </label>
                <input
                  type="text"
                  required
                  value={itemForm.canonical_description}
                  onChange={(e) => setItemForm({ ...itemForm, canonical_description: e.target.value })}
                  placeholder="Contoh: Buku Teks Matematika Kelas 6"
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded"
                />
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">
                  Spesifikasi Standar
                </label>
                <input
                  type="text"
                  value={itemForm.default_spec}
                  onChange={(e) => setItemForm({ ...itemForm, default_spec: e.target.value })}
                  placeholder="Kertas HVS 70gr, Full Color, Jilid Soft Cover"
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">Kategori</label>
                  <input
                    type="text"
                    value={itemForm.category}
                    onChange={(e) => setItemForm({ ...itemForm, category: e.target.value })}
                    placeholder="Buku / ATK / TIK"
                    className="w-full px-2.5 py-1.5 bg-background border border-border rounded"
                  />
                </div>
                <div>
                  <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">Satuan Baku</label>
                  <select
                    value={itemForm.default_unit}
                    onChange={(e) => setItemForm({ ...itemForm, default_unit: e.target.value })}
                    className="w-full px-2.5 py-1.5 bg-background border border-border rounded font-mono"
                  >
                    {units.length > 0 ? (
                      units.map((u) => (
                        <option key={u.id} value={u.code}>
                          {u.code} ({u.display_label})
                        </option>
                      ))
                    ) : (
                      <option value="Pcs">Pcs</option>
                    )}
                  </select>
                </div>
                <div>
                  <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">
                    Harga Acuan (IDR)
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={itemForm.reference_price}
                    onChange={(e) => setItemForm({ ...itemForm, reference_price: e.target.value })}
                    className="w-full px-2.5 py-1.5 bg-background border border-border rounded font-mono text-right"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setItemModalOpen(false)}
                  className="px-3 py-1.5 rounded border border-border bg-card hover:bg-muted"
                >
                  Batal
                </button>
                <button
                  type="button"
                  disabled={!itemForm.canonical_description.trim() || saveItemMutation.isPending}
                  onClick={() => saveItemMutation.mutate()}
                  className="px-4 py-1.5 rounded bg-primary text-primary-foreground font-semibold flex items-center gap-1.5 disabled:opacity-50"
                >
                  {saveItemMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Simpan Item</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add/Edit Budget Modal */}
      {budgetModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground">
                {editingBudget ? "Edit Kode Rekening & Kegiatan" : "Tambah Kode Rekening & Kegiatan BOS/BOP"}
              </h2>
              <button type="button" onClick={() => setBudgetModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">Tahun Anggaran</label>
                  <input
                    type="number"
                    value={budgetForm.fiscal_year}
                    onChange={(e) => setBudgetForm({ ...budgetForm, fiscal_year: parseInt(e.target.value) || 2026 })}
                    className="w-full px-2.5 py-1.5 bg-background border border-border rounded font-mono"
                  />
                </div>
                <div>
                  <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">Skema Pendanaan</label>
                  <select
                    value={budgetForm.funding_scheme}
                    onChange={(e) => setBudgetForm({ ...budgetForm, funding_scheme: e.target.value })}
                    className="w-full px-2.5 py-1.5 bg-background border border-border rounded font-mono"
                  >
                    <option value="BOS_REGULER">BOS_REGULER</option>
                    <option value="BOS_KINERJA">BOS_KINERJA</option>
                    <option value="BOP">BOP</option>
                    <option value="LAINNYA">LAINNYA</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">Kode Rekening Belanja</label>
                  <input
                    type="text"
                    value={budgetForm.account_code}
                    onChange={(e) => setBudgetForm({ ...budgetForm, account_code: e.target.value })}
                    placeholder="5.1.02.01.01.0012"
                    className="w-full px-2.5 py-1.5 bg-background border border-border rounded font-mono"
                  />
                </div>
                <div>
                  <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">Kode Kegiatan (ARKAS)</label>
                  <input
                    type="text"
                    value={budgetForm.activity_code}
                    onChange={(e) => setBudgetForm({ ...budgetForm, activity_code: e.target.value })}
                    placeholder="05.02.01"
                    className="w-full px-2.5 py-1.5 bg-background border border-border rounded font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">Nama Rekening Belanja *</label>
                <input
                  type="text"
                  required
                  value={budgetForm.account_name}
                  onChange={(e) => setBudgetForm({ ...budgetForm, account_name: e.target.value })}
                  placeholder="Belanja Bahan Cetak / Buku Teks Pelajaran"
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded"
                />
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">Nama Kegiatan Belanja *</label>
                <input
                  type="text"
                  required
                  value={budgetForm.activity_name}
                  onChange={(e) => setBudgetForm({ ...budgetForm, activity_name: e.target.value })}
                  placeholder="Pengembangan Perpustakaan & Layanan Pojok Baca"
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded"
                />
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-muted-foreground mb-1">Sub-Kegiatan / Uraian</label>
                <input
                  type="text"
                  value={budgetForm.sub_activity}
                  onChange={(e) => setBudgetForm({ ...budgetForm, sub_activity: e.target.value })}
                  placeholder="Pengadaan buku pendamping Kurikulum Merdeka"
                  className="w-full px-2.5 py-1.5 bg-background border border-border rounded"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setBudgetModalOpen(false)}
                  className="px-3 py-1.5 rounded border border-border bg-card hover:bg-muted"
                >
                  Batal
                </button>
                <button
                  type="button"
                  disabled={!budgetForm.account_name.trim() || !budgetForm.activity_name.trim() || saveBudgetMutation.isPending}
                  onClick={() => saveBudgetMutation.mutate()}
                  className="px-4 py-1.5 rounded bg-primary text-primary-foreground font-semibold flex items-center gap-1.5 disabled:opacity-50"
                >
                  {saveBudgetMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Simpan Rekening</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
