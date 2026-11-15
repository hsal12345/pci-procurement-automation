"use client";

import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import Link from "next/link";
import { Decimal } from "decimal.js";
import { RevisionLine } from "@/types/package";
import { formatIDR } from "@/lib/formatters";
import {
  BookOpen,
  Search,
  X,
  Check,
  Sparkles,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  Info,
  PackageCheck,
  Loader2,
  ArrowUpDown,
  Plus,
} from "lucide-react";

export interface CatalogItem {
  id: string;
  sku?: string | null;
  kbli?: string | null;
  canonical_description: string;
  default_spec?: string | null;
  brand?: string | null;
  category?: string | null;
  default_unit?: string | null;
  reference_price: number | string;
  is_active: boolean;
}

export function isPlaceholderLine(line: RevisionLine): boolean {
  if (line.item_id) return false;
  const desc = (line.confirmed_description || line.original_description || "").trim().toLowerCase();
  const isDefaultName =
    !desc || desc === "-" || desc.startsWith("barang baru") || desc.startsWith("item baru");
  const hasNoPrice =
    Number(line.hps_unit_price || 0) === 0 &&
    Number(line.offer_unit_price || 0) === 0 &&
    Number(line.final_unit_price || 0) === 0;
  return isDefaultName && hasNoPrice;
}

type SortOption = "name_asc" | "price_asc" | "price_desc" | "category_asc";

interface CatalogPickerModalProps {
  isOpen: boolean;
  catalogItems: CatalogItem[];
  isLoading?: boolean;
  existingLines: RevisionLine[];
  currentSubtotal: number;
  effectiveTaxRatePercent?: number;
  onRefreshCatalog?: () => Promise<void> | void;
  onConfirm: (
    selections: Array<{ item: CatalogItem; quantity: number }>,
    options: { replaceEmptyPlaceholders: boolean }
  ) => void;
  onClose: () => void;
}

const STOP_WORDS = new Set([
  "dan",
  "atau",
  "yang",
  "untuk",
  "dengan",
  "dari",
  "pada",
  "dalam",
  "baru",
  "barang",
  "item",
  "paket",
  "unit",
  "pcs",
  "set",
  "buah",
]);

export function CatalogPickerModal({
  isOpen,
  catalogItems,
  isLoading = false,
  existingLines,
  currentSubtotal,
  effectiveTaxRatePercent = 11,
  onRefreshCatalog,
  onConfirm,
  onClose,
}: CatalogPickerModalProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [hideAlreadyAdded, setHideAlreadyAdded] = useState(false);
  const [sortBy, setSortBy] = useState<SortOption>("name_asc");
  const [selectedQuantities, setSelectedQuantities] = useState<Record<string, number>>({});
  const [inspectedItemId, setInspectedItemId] = useState<string | null>(null);
  const [replaceEmptyPlaceholders, setReplaceEmptyPlaceholders] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const searchInputRef = useRef<HTMLInputElement>(null);

  const emptyPlaceholderCount = useMemo(
    () => existingLines.filter((l) => isPlaceholderLine(l)).length,
    [existingLines]
  );

  // Reset modal state on open
  useEffect(() => {
    if (!isOpen) return;
    setSearchQuery("");
    setSelectedCategory("ALL");
    setHideAlreadyAdded(false);
    setSortBy("name_asc");
    setSelectedQuantities({});
    setInspectedItemId(null);
    setReplaceEmptyPlaceholders(emptyPlaceholderCount > 0);
    setTimeout(() => {
      searchInputRef.current?.focus();
    }, 30);
  }, [isOpen, emptyPlaceholderCount]);

  // Keyboard shortcuts: Esc closes modal, '/' focuses search
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (
        e.key === "/" &&
        document.activeElement?.tagName !== "INPUT" &&
        document.activeElement?.tagName !== "SELECT" &&
        document.activeElement?.tagName !== "TEXTAREA"
      ) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Map existing package lines by item_id or lowercase description for duplicate detection
  const existingLineMap = useMemo(() => {
    const byId = new Map<string, { lineNumbers: number[]; totalQty: number }>();
    const byName = new Map<string, { lineNumbers: number[]; totalQty: number }>();

    existingLines.forEach((line) => {
      if (isPlaceholderLine(line)) return;
      const qty = Number(line.quantity || 0);
      if (line.item_id) {
        const prev = byId.get(line.item_id) || { lineNumbers: [], totalQty: 0 };
        prev.lineNumbers.push(line.line_number);
        prev.totalQty += qty;
        byId.set(line.item_id, prev);
      }
      const desc = (line.confirmed_description || line.original_description || "").trim().toLowerCase();
      if (desc) {
        const prev = byName.get(desc) || { lineNumbers: [], totalQty: 0 };
        prev.lineNumbers.push(line.line_number);
        prev.totalQty += qty;
        byName.set(desc, prev);
      }
    });

    return { byId, byName };
  }, [existingLines]);

  const getExistingUsage = useCallback(
    (item: CatalogItem) => {
      const byId = existingLineMap.byId.get(item.id);
      if (byId) return byId;
      const desc = (item.canonical_description || "").trim().toLowerCase();
      return existingLineMap.byName.get(desc) || null;
    },
    [existingLineMap]
  );

  // Extract unique categories & counts
  const categoryStats = useMemo(() => {
    const counts = new Map<string, number>();
    let uncategorized = 0;
    catalogItems.forEach((item) => {
      const cat = (item.category || "").trim();
      if (cat) {
        counts.set(cat, (counts.get(cat) || 0) + 1);
      } else {
        uncategorized += 1;
      }
    });
    const sorted = Array.from(counts.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    return { sorted, uncategorized };
  }, [catalogItems]);

  // Smart quick-search keyword chips derived from unlinked lines in the package
  const suggestedKeywords = useMemo(() => {
    const seen = new Set<string>();
    const keywords: string[] = [];
    for (const line of existingLines) {
      if (line.item_id || isPlaceholderLine(line)) continue;
      const words = (line.confirmed_description || line.original_description || "")
        .replace(/[^a-zA-Z0-9\s]/g, " ")
        .split(/\s+/)
        .map((w) => w.trim())
        .filter((w) => w.length >= 4 && !STOP_WORDS.has(w.toLowerCase()));
      for (const word of words) {
        const lower = word.toLowerCase();
        if (seen.has(lower)) continue;
        // Only suggest if at least one catalog item actually matches this keyword
        const hasMatch = catalogItems.some((ci) =>
          `${ci.canonical_description} ${ci.category || ""} ${ci.brand || ""} ${ci.default_spec || ""}`
            .toLowerCase()
            .includes(lower)
        );
        if (hasMatch) {
          seen.add(lower);
          keywords.push(word);
          if (keywords.length >= 4) return keywords;
        }
      }
    }
    return keywords;
  }, [existingLines, catalogItems]);

  // Filtered and sorted catalog items
  const filteredItems = useMemo(() => {
    const needle = searchQuery.trim().toLowerCase();

    const filtered = catalogItems.filter((item) => {
      if (selectedCategory === "__UNCATEGORIZED__") {
        if ((item.category || "").trim() !== "") return false;
      } else if (selectedCategory !== "ALL") {
        if ((item.category || "").trim() !== selectedCategory) return false;
      }

      if (hideAlreadyAdded && getExistingUsage(item) !== null) {
        return false;
      }

      if (!needle) return true;

      const haystack = [
        item.canonical_description,
        item.sku,
        item.kbli,
        item.default_spec,
        item.brand,
        item.category,
        item.default_unit,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(needle);
    });

    return filtered.sort((a, b) => {
      if (sortBy === "price_asc") {
        return Number(a.reference_price || 0) - Number(b.reference_price || 0);
      }
      if (sortBy === "price_desc") {
        return Number(b.reference_price || 0) - Number(a.reference_price || 0);
      }
      if (sortBy === "category_asc") {
        const catCompare = (a.category || "zzz").localeCompare(b.category || "zzz");
        if (catCompare !== 0) return catCompare;
      }
      return (a.canonical_description || "").localeCompare(b.canonical_description || "");
    });
  }, [catalogItems, searchQuery, selectedCategory, hideAlreadyAdded, sortBy, getExistingUsage]);

  if (!isOpen) return null;

  const selectedIds = Object.keys(selectedQuantities);
  const selectedCount = selectedIds.length;
  const allFilteredSelected =
    filteredItems.length > 0 && filteredItems.every((item) => selectedQuantities[item.id] != null);

  const toggleItemSelection = (item: CatalogItem) => {
    setInspectedItemId(item.id);
    setSelectedQuantities((prev) => {
      const next = { ...prev };
      if (next[item.id] != null) {
        delete next[item.id];
      } else {
        next[item.id] = 1;
      }
      return next;
    });
  };

  const handleToggleSelectAllFiltered = () => {
    setSelectedQuantities((prev) => {
      const next = { ...prev };
      if (allFilteredSelected) {
        filteredItems.forEach((item) => {
          delete next[item.id];
        });
      } else {
        filteredItems.forEach((item) => {
          if (next[item.id] == null) {
            next[item.id] = 1;
          }
        });
      }
      return next;
    });
  };

  const handleQuantityChange = (item: CatalogItem, rawValue: string) => {
    setInspectedItemId(item.id);
    const parsed = parseInt(rawValue, 10);
    const qty = isNaN(parsed) || parsed < 1 ? 1 : parsed;
    setSelectedQuantities((prev) => ({
      ...prev,
      [item.id]: qty,
    }));
  };

  const handleQuickAddSingle = (item: CatalogItem) => {
    const qty = selectedQuantities[item.id] || 1;
    onConfirm([{ item, quantity: qty }], {
      replaceEmptyPlaceholders: emptyPlaceholderCount > 0 && replaceEmptyPlaceholders,
    });
  };

  const handleConfirmSelected = () => {
    if (selectedCount === 0) return;
    const itemLookup = new Map(catalogItems.map((ci) => [ci.id, ci]));
    const selections: Array<{ item: CatalogItem; quantity: number }> = [];

    // Preserve display order for predictable row ordering
    catalogItems.forEach((ci) => {
      const qty = selectedQuantities[ci.id];
      if (qty != null && itemLookup.has(ci.id)) {
        selections.push({ item: ci, quantity: Math.max(1, qty) });
      }
    });

    onConfirm(selections, {
      replaceEmptyPlaceholders: emptyPlaceholderCount > 0 && replaceEmptyPlaceholders,
    });
  };

  const handleRefresh = async () => {
    if (!onRefreshCatalog || isRefreshing) return;
    setIsRefreshing(true);
    try {
      await onRefreshCatalog();
    } finally {
      setIsRefreshing(false);
    }
  };

  // Financial impact calculations (Decimal-safe)
  let totalSelectedUnits = 0;
  let addedSubtotalDec = new Decimal(0);

  catalogItems.forEach((item) => {
    const qty = selectedQuantities[item.id];
    if (qty != null) {
      totalSelectedUnits += qty;
      const lineSub = new Decimal(qty).times(new Decimal(Number(item.reference_price || 0))).round();
      addedSubtotalDec = addedSubtotalDec.plus(lineSub);
    }
  });

  const projectedSubtotalDec = new Decimal(currentSubtotal || 0).plus(addedSubtotalDec);
  const taxRateDec = new Decimal(effectiveTaxRatePercent || 0).dividedBy(100);
  const projectedTaxDec = projectedSubtotalDec.times(taxRateDec).round();
  const projectedGrandTotalDec = projectedSubtotalDec.plus(projectedTaxDec);

  const inspectedItem =
    catalogItems.find((ci) => ci.id === inspectedItemId) ||
    (selectedIds.length > 0 ? catalogItems.find((ci) => ci.id === selectedIds[selectedIds.length - 1]) : null) ||
    filteredItems[0] ||
    null;
  const inspectedUsage = inspectedItem ? getExistingUsage(inspectedItem) : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-card border border-border w-full max-w-5xl max-h-[90vh] rounded-lg shadow-2xl overflow-hidden flex flex-col font-sans">
        {/* Header */}
        <div className="px-4 py-3 border-b border-border bg-muted/40 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-md bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center shrink-0">
              <BookOpen className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="min-w-0">
              <h3 className="text-xs font-bold text-foreground uppercase tracking-wider font-mono truncate">
                Pilih Barang dari Master Katalog
              </h3>
              <p className="text-[11px] text-muted-foreground truncate">
                Pilih satu atau beberapa item dari katalog master. Harga acuan (HPS), satuan, SKU, dan KBLI terisi otomatis.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {onRefreshCatalog && (
              <button
                type="button"
                onClick={handleRefresh}
                disabled={isRefreshing || isLoading}
                className="flex items-center gap-1 px-2 py-1 rounded border border-border bg-background hover:bg-muted text-muted-foreground hover:text-foreground text-[11px] transition disabled:opacity-50"
                title="Muat ulang daftar katalog dari server"
              >
                <RefreshCw className={`w-3 h-3 ${isRefreshing ? "animate-spin" : ""}`} />
                <span className="hidden sm:inline">Segarkan</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition"
              title="Tutup (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Assistance Strip */}
        <div className="px-4 py-2.5 border-b border-border bg-emerald-500/5 flex flex-col gap-2 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-[11px] text-emerald-200/90">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>
                <strong>Asisten Katalog:</strong> Harga Acuan katalog otomatis disalin ke{" "}
                <span className="font-mono text-foreground">HPS</span>,{" "}
                <span className="font-mono text-foreground">Penawaran</span>, dan{" "}
                <span className="font-mono text-foreground">Final</span> (dapat dinegosiasi ulang di tabel utama).
              </span>
            </div>

            {emptyPlaceholderCount > 0 && (
              <label className="flex items-center gap-1.5 text-[11px] text-amber-300 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={replaceEmptyPlaceholders}
                  onChange={(e) => setReplaceEmptyPlaceholders(e.target.checked)}
                  className="rounded border-amber-500/50 accent-emerald-500"
                />
                <span>
                  Ganti {emptyPlaceholderCount} baris kosong (&quot;Barang Baru&quot;) otomatis
                </span>
              </label>
            )}
          </div>

          {/* Search Suggestions from unlinked lines (if any) */}
          {suggestedKeywords.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
              <span className="text-muted-foreground font-mono text-[10px] uppercase">
                Saran pencarian dari baris paket:
              </span>
              {suggestedKeywords.map((kw) => (
                <button
                  key={kw}
                  type="button"
                  onClick={() => setSearchQuery(kw)}
                  className="px-2 py-0.5 rounded-full bg-background hover:bg-muted border border-border text-foreground text-[10px] font-mono transition"
                >
                  &ldquo;{kw}&rdquo;
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Search, Category Filter & Sort Toolbar */}
        <div className="px-4 py-2.5 border-b border-border bg-background/60 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Cari nama barang, SKU, KBLI, merek, atau spesifikasi... (tekan /)"
                className="w-full pl-8 pr-7 py-1.5 bg-background border border-border rounded text-xs text-foreground outline-none focus:ring-1 focus:ring-primary"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2 top-2 text-muted-foreground hover:text-foreground"
                  title="Hapus pencarian"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <div className="flex items-center gap-1.5">
              <ArrowUpDown className="w-3.5 h-3.5 text-muted-foreground" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="px-2 py-1.5 bg-background border border-border rounded text-xs text-foreground outline-none focus:ring-1 focus:ring-primary"
                aria-label="Urutkan katalog"
              >
                <option value="name_asc">Urut: Nama (A–Z)</option>
                <option value="price_asc">Harga: Termurah</option>
                <option value="price_desc">Harga: Termahal</option>
                <option value="category_asc">Urut: Kategori</option>
              </select>
            </div>

            <label className="flex items-center gap-1.5 text-[11px] text-muted-foreground cursor-pointer select-none px-2 py-1 rounded border border-border bg-background hover:bg-muted/40">
              <input
                type="checkbox"
                checked={hideAlreadyAdded}
                onChange={(e) => setHideAlreadyAdded(e.target.checked)}
                className="rounded border-border accent-emerald-500"
              />
              <span>Sembunyikan yang sudah di paket</span>
            </label>
          </div>

          {/* Category Filter Chips */}
          {catalogItems.length > 0 && (
            <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 text-[11px]">
              <button
                type="button"
                onClick={() => setSelectedCategory("ALL")}
                className={`px-2 py-0.5 rounded-md font-mono whitespace-nowrap border transition ${
                  selectedCategory === "ALL"
                    ? "bg-primary text-primary-foreground border-primary font-semibold"
                    : "bg-card text-muted-foreground hover:text-foreground border-border"
                }`}
              >
                Semua ({catalogItems.length})
              </button>
              {categoryStats.sorted.map(([cat, count]) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-2 py-0.5 rounded-md font-mono whitespace-nowrap border transition ${
                    selectedCategory === cat
                      ? "bg-primary text-primary-foreground border-primary font-semibold"
                      : "bg-card text-muted-foreground hover:text-foreground border-border"
                  }`}
                >
                  {cat} ({count})
                </button>
              ))}
              {categoryStats.uncategorized > 0 && (
                <button
                  type="button"
                  onClick={() => setSelectedCategory("__UNCATEGORIZED__")}
                  className={`px-2 py-0.5 rounded-md font-mono whitespace-nowrap border transition ${
                    selectedCategory === "__UNCATEGORIZED__"
                      ? "bg-primary text-primary-foreground border-primary font-semibold"
                      : "bg-card text-muted-foreground hover:text-foreground border-border"
                  }`}
                >
                  Lainnya ({categoryStats.uncategorized})
                </button>
              )}
              <span className="ml-auto text-[10px] font-mono text-muted-foreground whitespace-nowrap pl-2">
                Menampilkan {filteredItems.length} dari {catalogItems.length} item
              </span>
            </div>
          )}
        </div>

        {/* Selection Table */}
        <div className="flex-1 overflow-auto min-h-[240px]">
          {isLoading ? (
            <div className="h-60 flex flex-col items-center justify-center gap-2 text-muted-foreground text-xs font-mono">
              <Loader2 className="w-5 h-5 animate-spin text-primary" />
              <span>Memuat data Master Katalog Barang...</span>
            </div>
          ) : catalogItems.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center gap-3 p-6 text-center">
              <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-muted-foreground" />
              </div>
              <div className="space-y-1 max-w-md">
                <p className="text-sm font-semibold text-foreground">
                  Master Katalog Barang Belum Tersedia
                </p>
                <p className="text-xs text-muted-foreground">
                  Belum ada item aktif di Master Katalog. Tambahkan item di halaman Katalog &amp; Anggaran agar bisa dipilih langsung di sini, atau tambahkan baris manual di tabel paket.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  href="/catalog"
                  target="_blank"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 transition"
                >
                  <span>Buka Master Katalog</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
                {onRefreshCatalog && (
                  <button
                    type="button"
                    onClick={handleRefresh}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-border bg-background hover:bg-muted text-xs text-foreground transition"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
                    <span>Cek Ulang</span>
                  </button>
                )}
              </div>
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="h-56 flex flex-col items-center justify-center gap-2.5 p-6 text-center">
              <p className="text-xs font-mono text-muted-foreground">
                Tidak ada item katalog yang sesuai dengan filter saat ini.
              </p>
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setSelectedCategory("ALL");
                  setHideAlreadyAdded(false);
                }}
                className="px-3 py-1 rounded border border-border bg-background hover:bg-muted text-xs text-foreground transition"
              >
                Reset Pencarian &amp; Filter
              </button>
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-muted/95 backdrop-blur border-b border-border text-[10px] font-mono uppercase tracking-wider text-muted-foreground sticky top-0 z-10 select-none">
                  <th className="px-3 py-2 w-10 text-center">
                    <input
                      type="checkbox"
                      checked={allFilteredSelected}
                      onChange={handleToggleSelectAllFiltered}
                      title="Pilih / Batal pilih semua yang tampil"
                      className="rounded border-border accent-emerald-500 cursor-pointer"
                    />
                  </th>
                  <th className="px-2.5 py-2 w-32">SKU / KBLI</th>
                  <th className="px-2.5 py-2 min-w-[240px]">Nama Barang &amp; Spesifikasi</th>
                  <th className="px-2.5 py-2 w-28">Kategori</th>
                  <th className="px-2.5 py-2 w-20 text-center">Satuan</th>
                  <th className="px-2.5 py-2 w-32 text-right">Harga Acuan</th>
                  <th className="px-2.5 py-2 w-20 text-center">Vol</th>
                  <th className="px-3 py-2 w-32 text-right">Subtotal / Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {filteredItems.map((item) => {
                  const isSelected = selectedQuantities[item.id] != null;
                  const qty = selectedQuantities[item.id] ?? 1;
                  const refPrice = Number(item.reference_price || 0);
                  const existingUsage = getExistingUsage(item);
                  const rowSubtotal = isSelected
                    ? new Decimal(qty).times(new Decimal(refPrice)).round().toNumber()
                    : 0;
                  const isInspected = inspectedItem?.id === item.id;

                  return (
                    <tr
                      key={item.id}
                      onClick={() => toggleItemSelection(item)}
                      onMouseEnter={() => setInspectedItemId(item.id)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? "bg-emerald-500/12 hover:bg-emerald-500/18"
                          : isInspected
                          ? "bg-muted/40"
                          : "hover:bg-muted/30"
                      }`}
                    >
                      {/* Checkbox */}
                      <td
                        className="px-3 py-2 text-center"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleItemSelection(item)}
                          className="rounded border-border accent-emerald-500 cursor-pointer"
                        />
                      </td>

                      {/* SKU / KBLI */}
                      <td className="px-2.5 py-2 font-mono align-top">
                        <div className="text-[11px] font-semibold text-primary">
                          {item.sku || "-"}
                        </div>
                        {item.kbli && (
                          <div className="text-[10px] text-muted-foreground">
                            KBLI: {item.kbli}
                          </div>
                        )}
                      </td>

                      {/* Description & Spec */}
                      <td className="px-2.5 py-2 align-top">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="font-semibold text-foreground">
                            {item.canonical_description}
                          </span>
                          {existingUsage && (
                            <span
                              className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded bg-sky-500/15 border border-sky-500/30 text-sky-300 font-mono text-[9px]"
                              title={`Sudah ada di paket pada baris #${existingUsage.lineNumbers.join(", #")}`}
                            >
                              <PackageCheck className="w-2.5 h-2.5" />
                              Di Paket (#{existingUsage.lineNumbers.join(",")})
                            </span>
                          )}
                        </div>
                        {(item.default_spec || item.brand) && (
                          <div className="text-[11px] text-muted-foreground line-clamp-1 mt-0.5">
                            {item.brand ? `[${item.brand}] ` : ""}
                            {item.default_spec || ""}
                          </div>
                        )}
                      </td>

                      {/* Category */}
                      <td className="px-2.5 py-2 align-top">
                        {item.category ? (
                          <span className="inline-block px-1.5 py-0.5 rounded bg-muted border border-border text-[10px] text-muted-foreground font-mono">
                            {item.category}
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-[11px]">-</span>
                        )}
                      </td>

                      {/* Unit */}
                      <td className="px-2.5 py-2 text-center font-mono text-foreground align-top">
                        {item.default_unit || "Pcs"}
                      </td>

                      {/* Reference Price */}
                      <td className="px-2.5 py-2 text-right font-mono tabular-nums align-top">
                        {refPrice === 0 ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 text-[10px] font-semibold">
                            Rp 0
                          </span>
                        ) : (
                          <span className="font-semibold text-foreground">
                            {formatIDR(refPrice)}
                          </span>
                        )}
                      </td>

                      {/* Quantity Input */}
                      <td
                        className="px-2.5 py-1.5 text-center align-top"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="number"
                          min={1}
                          value={qty}
                          onChange={(e) => handleQuantityChange(item, e.target.value)}
                          onFocus={() => setInspectedItemId(item.id)}
                          aria-label={`Kuantitas ${item.canonical_description}`}
                          className={`w-16 px-1.5 py-1 text-right font-mono tabular-nums text-xs rounded border outline-none transition ${
                            isSelected
                              ? "bg-background border-emerald-500/60 text-foreground ring-1 ring-emerald-500/30"
                              : "bg-background/50 border-border text-muted-foreground focus:text-foreground focus:border-primary"
                          }`}
                        />
                      </td>

                      {/* Subtotal or 1-click add */}
                      <td
                        className="px-3 py-2 text-right font-mono tabular-nums align-top"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {isSelected ? (
                          <span className="font-bold text-emerald-300 text-[11px]">
                            {formatIDR(rowSubtotal)}
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleQuickAddSingle(item)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-border bg-background hover:bg-emerald-500/15 hover:border-emerald-500/40 hover:text-emerald-300 text-muted-foreground text-[10px] font-sans transition"
                            title="Langsung tambahkan 1 baris barang ini ke paket"
                          >
                            <Plus className="w-3 h-3" />
                            <span>Tambah</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Assistance Inspector & Budget Impact Panel */}
        <div className="px-4 py-2.5 border-t border-border bg-muted/25 grid grid-cols-1 md:grid-cols-12 gap-3 text-xs">
          {/* Left: Item Detail Assistant */}
          <div className="md:col-span-7 flex items-start gap-2 min-w-0">
            <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
            {inspectedItem ? (
              <div className="min-w-0 space-y-0.5 text-[11px]">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-semibold text-foreground">
                    {inspectedItem.canonical_description}
                  </span>
                  {inspectedItem.brand && (
                    <span className="px-1.5 py-0.2 rounded bg-muted border border-border text-[10px] font-mono text-muted-foreground">
                      Merek: {inspectedItem.brand}
                    </span>
                  )}
                </div>
                <p className="text-muted-foreground break-words">
                  <span className="font-mono text-[10px] uppercase mr-1">Spesifikasi:</span>
                  {inspectedItem.default_spec || "Belum ada spesifikasi default di master katalog."}
                </p>
                {Number(inspectedItem.reference_price || 0) === 0 && (
                  <p className="text-amber-300 flex items-center gap-1 text-[10px]">
                    <AlertTriangle className="w-3 h-3 shrink-0" />
                    Harga acuan Rp 0 — Anda dapat mengisi harga manual atau alasan Gratis di tabel paket.
                  </p>
                )}
                {inspectedUsage && (
                  <p className="text-sky-300 text-[10px]">
                    Info: Barang ini sudah ada pada baris #{inspectedUsage.lineNumbers.join(", #")} (total{" "}
                    {inspectedUsage.totalQty} {inspectedItem.default_unit || "Pcs"}). Menambahkannya akan membuat baris baru.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground">
                Klik baris pada tabel untuk mencentang barang, ubah jumlah <span className="font-mono text-foreground">Vol</span> sesuai kebutuhan, atau klik <span className="font-mono text-foreground">+ Tambah</span> untuk menambahkan satu barang secara langsung.
              </p>
            )}
          </div>

          {/* Right: Budget Impact Preview */}
          <div className="md:col-span-5 md:border-l md:border-border md:pl-3 flex flex-col justify-center space-y-1 font-mono text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">
                Terpilih ({selectedCount} item / {totalSelectedUnits} unit):
              </span>
              <span className="font-bold text-emerald-300 tabular-nums">
                + {formatIDR(addedSubtotalDec.toNumber())}
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px] text-muted-foreground">
              <span>Proyeksi Grand Total (+ Pajak {effectiveTaxRatePercent}%):</span>
              <span className="font-semibold text-foreground tabular-nums">
                {formatIDR(projectedGrandTotalDec.toNumber())}
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-border bg-card flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3 text-xs">
            {selectedCount > 0 && (
              <button
                type="button"
                onClick={() => setSelectedQuantities({})}
                className="text-[11px] text-muted-foreground hover:text-foreground underline underline-offset-2 transition"
              >
                Bersihkan Pilihan ({selectedCount})
              </button>
            )}
            <Link
              href="/catalog"
              target="_blank"
              className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-primary transition"
            >
              <span>Kelola Master Katalog</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs rounded border border-border bg-card hover:bg-muted text-foreground transition"
            >
              Batal
            </button>
            <button
              type="button"
              disabled={selectedCount === 0}
              onClick={handleConfirmSelected}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition shadow-xs disabled:opacity-45 disabled:cursor-not-allowed"
            >
              <Check className="w-3.5 h-3.5" />
              <span>
                {selectedCount > 0
                  ? `Tambahkan ke Paket (${selectedCount} Barang)`
                  : "Pilih Barang Terlebih Dahulu"}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
