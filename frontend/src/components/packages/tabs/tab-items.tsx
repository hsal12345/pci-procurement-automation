"use client";

import { useState, useRef, useEffect } from "react";
import { Decimal } from "decimal.js";
import { RevisionLine, PackageRevision } from "@/types/package";
import { formatIDR, formatTabularNumber, terbilangIndonesian } from "@/lib/formatters";
import { ZeroPriceModal } from "../zero-price-modal";
import {
  Plus,
  Trash2,
  Zap,
  ArrowDown,
  Info,
  AlertTriangle,
  Calculator,
} from "lucide-react";

interface TabItemsProps {
  revision: PackageRevision;
  isReadOnly: boolean;
  onLinesChanged: (newLines: RevisionLine[]) => void;
}

type EditableColumn =
  | "confirmed_description"
  | "specification"
  | "quantity"
  | "unit"
  | "hps_unit_price"
  | "offer_unit_price"
  | "final_unit_price"
  | "discount";

const EDITABLE_COLUMNS: EditableColumn[] = [
  "confirmed_description",
  "specification",
  "quantity",
  "unit",
  "hps_unit_price",
  "offer_unit_price",
  "final_unit_price",
  "discount",
];

export function TabItems({ revision, isReadOnly, onLinesChanged }: TabItemsProps) {
  const [lines, setLines] = useState<RevisionLine[]>(() => revision.lines || []);
  const [activeCell, setActiveCell] = useState<{ row: number; col: EditableColumn } | null>(null);
  const [zeroPriceTarget, setZeroPriceTarget] = useState<{ row: number; line: RevisionLine } | null>(null);

  // Sync when revision lines reload externally
  useEffect(() => {
    if (revision.lines && revision.lines.length > 0) {
      setLines(revision.lines);
    }
  }, [revision.lines]);

  // Handle cell value change
  const handleCellChange = (
    rowIndex: number,
    field: EditableColumn,
    rawVal: string | number
  ) => {
    const updated = [...lines];
    const row = { ...updated[rowIndex] };

    if (field === "quantity" || field === "hps_unit_price" || field === "offer_unit_price" || field === "final_unit_price" || field === "discount") {
      const numVal = parseFloat(String(rawVal).replace(/[^0-9.-]+/g, "")) || 0;
      (row as any)[field] = numVal;

      // Recalculate row line total with Decimal precision
      const qtyDec = new Decimal(row.quantity || 0);
      const priceDec = new Decimal(row.final_unit_price || 0);
      const discountDec = new Decimal(row.discount || 0);

      // line_total = round(qty * price * (1 - discount/100))
      const factor = new Decimal(1).minus(discountDec.dividedBy(100));
      const totalDec = qtyDec.times(priceDec).times(factor);
      row.line_total = totalDec.round().toNumber();
    } else {
      (row as any)[field] = rawVal;
      if (field === "confirmed_description") {
        const orig = (row.original_description || "").trim().toLowerCase();
        // If original is a default placeholder or was identical to previous confirmed, keep original_description in sync
        if (!orig || orig.startsWith("barang baru") || orig.startsWith("item") || row.original_description === row.confirmed_description) {
          row.original_description = String(rawVal);
        }
      }
    }

    updated[rowIndex] = row;
    setLines(updated);
    onLinesChanged(updated);
  };

  // Keyboard-first continuous grid navigation & Alt+C shortcut
  const handleKeyDown = (
    e: React.KeyboardEvent<HTMLInputElement>,
    rowIndex: number,
    col: EditableColumn
  ) => {
    // Alt + C: Copy previous price column into active cell (Ergonomic Finding #2)
    if (e.altKey && (e.key === "c" || e.key === "C")) {
      e.preventDefault();
      const current = lines[rowIndex];
      if (col === "offer_unit_price") {
        handleCellChange(rowIndex, "offer_unit_price", current.hps_unit_price);
      } else if (col === "final_unit_price") {
        handleCellChange(rowIndex, "final_unit_price", current.offer_unit_price || current.hps_unit_price);
      }
      return;
    }

    const colIdx = EDITABLE_COLUMNS.indexOf(col);

    if (e.key === "Tab") {
      e.preventDefault();
      if (e.shiftKey) {
        // Shift + Tab: Move previous cell
        if (colIdx > 0) {
          focusCell(rowIndex, EDITABLE_COLUMNS[colIdx - 1]);
        } else if (rowIndex > 0) {
          focusCell(rowIndex - 1, EDITABLE_COLUMNS[EDITABLE_COLUMNS.length - 1]);
        }
      } else {
        // Tab: Move next cell
        if (colIdx < EDITABLE_COLUMNS.length - 1) {
          focusCell(rowIndex, EDITABLE_COLUMNS[colIdx + 1]);
        } else if (rowIndex < lines.length - 1) {
          focusCell(rowIndex + 1, EDITABLE_COLUMNS[0]);
        }
      }
    } else if (e.key === "Enter") {
      e.preventDefault();
      // Enter: Move down row or next cell
      if (rowIndex < lines.length - 1) {
        focusCell(rowIndex + 1, col);
      } else if (colIdx < EDITABLE_COLUMNS.length - 1) {
        focusCell(0, EDITABLE_COLUMNS[colIdx + 1]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (rowIndex < lines.length - 1) {
        focusCell(rowIndex + 1, col);
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (rowIndex > 0) {
        focusCell(rowIndex - 1, col);
      }
    }
  };

  const focusCell = (row: number, col: EditableColumn) => {
    setActiveCell({ row, col });
    setTimeout(() => {
      const el = document.getElementById(`cell-${row}-${col}`) as HTMLInputElement | null;
      if (el) {
        el.focus();
        el.select();
      }
    }, 10);
  };

  // Zero-price check on blur
  const handleBlur = (rowIndex: number, col: EditableColumn) => {
    if (col === "final_unit_price") {
      const line = lines[rowIndex];
      if (line.final_unit_price === 0 && !line.notes?.includes("Gratis") && !line.notes?.includes("Bonus")) {
        setZeroPriceTarget({ row: rowIndex, line });
      }
    }
  };

  // Batch Shortcut 1: [ ⚡ Samakan Semua (HPS = Penawaran = Final) ]
  const handleBatchSyncAll = () => {
    if (!confirm("Apakah Anda yakin ingin menyamakan seluruh baris: Harga Penawaran = HPS, Harga Final = Penawaran?")) {
      return;
    }
    const updated = lines.map((l) => {
      const hps = l.hps_unit_price || 0;
      const qtyDec = new Decimal(l.quantity || 0);
      const priceDec = new Decimal(hps);
      const discountDec = new Decimal(l.discount || 0);
      const factor = new Decimal(1).minus(discountDec.dividedBy(100));
      const lineTotal = qtyDec.times(priceDec).times(factor).round().toNumber();

      return {
        ...l,
        offer_unit_price: hps,
        final_unit_price: hps,
        line_total: lineTotal,
      };
    });
    setLines(updated);
    onLinesChanged(updated);
  };

  // Batch Shortcut 2: [ ⬇ Salin HPS ke Penawaran ]
  const handleCopyHpsToOffer = () => {
    const updated = lines.map((l) => ({
      ...l,
      offer_unit_price: l.hps_unit_price || 0,
    }));
    setLines(updated);
    onLinesChanged(updated);
  };

  // Batch Shortcut 3: [ ⬇ Salin Penawaran ke Final ]
  const handleCopyOfferToFinal = () => {
    const updated = lines.map((l) => {
      const finalPrice = l.offer_unit_price || l.hps_unit_price || 0;
      const qtyDec = new Decimal(l.quantity || 0);
      const priceDec = new Decimal(finalPrice);
      const discountDec = new Decimal(l.discount || 0);
      const factor = new Decimal(1).minus(discountDec.dividedBy(100));
      const lineTotal = qtyDec.times(priceDec).times(factor).round().toNumber();

      return {
        ...l,
        final_unit_price: finalPrice,
        line_total: lineTotal,
      };
    });
    setLines(updated);
    onLinesChanged(updated);
  };

  // Add new line row
  const handleAddRow = () => {
    const nextLineNo = lines.length > 0 ? Math.max(...lines.map((l) => l.line_number)) + 1 : 1;
    const newLine: RevisionLine = {
      line_number: nextLineNo,
      original_description: `Barang Baru #${nextLineNo}`,
      confirmed_description: `Barang Baru #${nextLineNo}`,
      specification: "-",
      quantity: 1,
      received_quantity: 1,
      unit: "Pcs",
      hps_unit_price: 0,
      offer_unit_price: 0,
      final_unit_price: 0,
      discount: 0,
      line_total: 0,
      condition: "BAIK",
    };
    const updated = [...lines, newLine];
    setLines(updated);
    onLinesChanged(updated);
    setTimeout(() => focusCell(updated.length - 1, "confirmed_description"), 50);
  };

  // Remove line row
  const handleDeleteRow = (index: number) => {
    if (lines.length <= 1) {
      alert("Paket pengadaan harus memiliki minimal 1 baris barang.");
      return;
    }
    const updated = lines.filter((_, i) => i !== index).map((l, i) => ({ ...l, line_number: i + 1 }));
    setLines(updated);
    onLinesChanged(updated);
  };

  // High-Precision Decimal Recap Calculations (Finding #1)
  let subtotalDec = new Decimal(0);
  lines.forEach((l) => {
    subtotalDec = subtotalDec.plus(new Decimal(l.line_total || 0));
  });

  // Calculate dynamic taxes based on active tax_policy_snapshot
  const taxPolicies =
    revision.tax_policy_snapshot && revision.tax_policy_snapshot.length > 0
      ? revision.tax_policy_snapshot
      : [{ tax_type: "PPN", rate_percent: 11, is_withholding: false }];

  let taxTotalDec = new Decimal(0);
  const taxDetails: Array<{ tax_type: string; amount: number; rate: number }> = [];

  taxPolicies.forEach((p) => {
    let ratePct = 11;
    let rateDec = new Decimal("0.11");
    if (p.rate_percent != null && String(p.rate_percent).trim() !== "") {
      ratePct = Number(p.rate_percent);
      rateDec = new Decimal(ratePct).dividedBy(100);
    } else if (p.rate != null && String(p.rate).trim() !== "") {
      const rawRate = new Decimal(String(p.rate));
      if (rawRate.gt(0) && rawRate.lt(1)) {
        rateDec = rawRate;
        ratePct = rawRate.times(100).toNumber();
      } else {
        ratePct = rawRate.toNumber();
        rateDec = rawRate.dividedBy(100);
      }
    }

    const amountDec = subtotalDec.times(rateDec).round();
    const isWithholding = Boolean(
      p.is_withholding || (p.withholding_rule && String(p.withholding_rule).toUpperCase() !== "NONE")
    );

    taxDetails.push({
      tax_type: p.tax_type || "PPN",
      amount: amountDec.toNumber(),
      rate: ratePct,
    });
    if (!isWithholding) {
      taxTotalDec = taxTotalDec.plus(amountDec);
    }
  });

  const grandTotalDec = subtotalDec.plus(taxTotalDec);
  const computedSubtotal = subtotalDec.toNumber();
  const computedTaxTotal = taxTotalDec.toNumber();
  const computedGrandTotal = grandTotalDec.toNumber();
  const computedTerbilang = terbilangIndonesian(computedGrandTotal);

  return (
    <div className="flex flex-col h-full bg-card">
      {/* Grid Action Toolbar */}
      <div className="px-4 py-2 border-b border-border bg-muted/20 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-mono text-muted-foreground text-[11px]">
            {lines.length} Baris Barang
          </span>

          {!isReadOnly && (
            <>
              <div className="h-4 w-px bg-border mx-1" />
              {/* Batch Ergonomic Action Buttons */}
              <button
                type="button"
                onClick={handleBatchSyncAll}
                className="flex items-center gap-1 px-2 py-0.5 rounded bg-muted/60 hover:bg-muted text-foreground border border-border text-[11px] font-medium transition"
                title="Menyamakan harga penawaran dan negosiasi agar sama persis dengan HPS"
              >
                <Zap className="w-3 h-3 text-amber-400" />
                <span>Samakan Semua (HPS = Penawaran = Final)</span>
              </button>

              <button
                type="button"
                onClick={handleCopyHpsToOffer}
                className="flex items-center gap-1 px-2 py-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground text-[11px] transition"
              >
                <ArrowDown className="w-3 h-3" />
                <span>Salin HPS ke Penawaran</span>
              </button>

              <button
                type="button"
                onClick={handleCopyOfferToFinal}
                className="flex items-center gap-1 px-2 py-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground text-[11px] transition"
              >
                <ArrowDown className="w-3 h-3" />
                <span>Salin Penawaran ke Final</span>
              </button>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-muted-foreground flex items-center gap-1">
            <Info className="w-3 h-3" /> Navigasi: [Tab] / [Enter] • Salin kolom sebelumnya: [Alt+C]
          </span>
          {!isReadOnly && (
            <button
              type="button"
              onClick={handleAddRow}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-primary text-primary-foreground font-medium text-[11px] transition hover:opacity-90"
            >
              <Plus className="w-3 h-3" />
              <span>Tambah Baris</span>
            </button>
          )}
        </div>
      </div>

      {/* Dense Keyboard Data Grid */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left border-collapse font-sans text-xs">
          <thead>
            <tr className="bg-muted/50 border-b border-border text-[10px] uppercase font-mono font-semibold tracking-wider text-muted-foreground sticky top-0 z-10 select-none">
              <th className="px-2 py-1.5 w-10 text-center border-r border-border">No</th>
              <th className="px-2 py-1.5 min-w-[200px] border-r border-border">Deskripsi Barang</th>
              <th className="px-2 py-1.5 min-w-[140px] border-r border-border">Spesifikasi</th>
              <th className="px-2 py-1.5 w-16 text-right border-r border-border">Vol</th>
              <th className="px-2 py-1.5 w-16 text-center border-r border-border">Satuan</th>
              <th className="px-2 py-1.5 w-28 text-right border-r border-border">Harga HPS</th>
              <th className="px-2 py-1.5 w-28 text-right border-r border-border">Harga Penawaran</th>
              <th className="px-2 py-1.5 w-28 text-right border-r border-border">Harga Final</th>
              <th className="px-2 py-1.5 w-16 text-right border-r border-border">Diskon (%)</th>
              <th className="px-2 py-1.5 w-32 text-right border-r border-border">Total Akhir</th>
              {!isReadOnly && <th className="px-2 py-1.5 w-8 text-center">✕</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60 font-mono text-[11px]">
            {lines.map((line, idx) => {
              const isZeroPrice = line.final_unit_price === 0;

              return (
                <tr
                  key={line.id || `line-${idx}`}
                  className={`hover:bg-muted/20 transition-colors ${
                    isZeroPrice ? "bg-amber-950/10" : ""
                  }`}
                >
                  {/* Row No */}
                  <td className="px-2 py-1 text-center font-bold text-muted-foreground border-r border-border/80">
                    {line.line_number}
                  </td>

                  {/* Confirmed Description */}
                  <td className="p-0 border-r border-border/80">
                    <input
                      id={`cell-${idx}-confirmed_description`}
                      type="text"
                      disabled={isReadOnly}
                      value={line.confirmed_description || ""}
                      onChange={(e) => handleCellChange(idx, "confirmed_description", e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, idx, "confirmed_description")}
                      className="w-full h-8 px-2 py-1 bg-transparent text-xs font-sans text-foreground outline-none focus:ring-1 focus:ring-ring focus:bg-accent/40"
                    />
                  </td>

                  {/* Specification */}
                  <td className="p-0 border-r border-border/80">
                    <input
                      id={`cell-${idx}-specification`}
                      type="text"
                      disabled={isReadOnly}
                      value={line.specification || ""}
                      onChange={(e) => handleCellChange(idx, "specification", e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, idx, "specification")}
                      className="w-full h-8 px-2 py-1 bg-transparent text-xs font-sans text-muted-foreground focus:text-foreground outline-none focus:ring-1 focus:ring-ring focus:bg-accent/40"
                    />
                  </td>

                  {/* Quantity */}
                  <td className="p-0 border-r border-border/80">
                    <input
                      id={`cell-${idx}-quantity`}
                      type="number"
                      disabled={isReadOnly}
                      min="1"
                      value={line.quantity != null && !isNaN(Number(line.quantity)) ? Number(line.quantity) : ""}
                      onChange={(e) => handleCellChange(idx, "quantity", e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, idx, "quantity")}
                      className="w-full h-8 px-2 py-1 text-right bg-transparent tabular-nums text-foreground outline-none focus:ring-1 focus:ring-ring focus:bg-accent/40 font-mono"
                    />
                  </td>

                  {/* Unit */}
                  <td className="p-0 border-r border-border/80">
                    <input
                      id={`cell-${idx}-unit`}
                      type="text"
                      disabled={isReadOnly}
                      value={line.unit || ""}
                      onChange={(e) => handleCellChange(idx, "unit", e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, idx, "unit")}
                      className="w-full h-8 px-1 py-1 text-center bg-transparent text-foreground outline-none focus:ring-1 focus:ring-ring focus:bg-accent/40 font-mono"
                    />
                  </td>

                  {/* HPS Unit Price */}
                  <td className="p-0 border-r border-border/80">
                    <input
                      id={`cell-${idx}-hps_unit_price`}
                      type="number"
                      disabled={isReadOnly}
                      value={line.hps_unit_price != null && !isNaN(Number(line.hps_unit_price)) ? Number(line.hps_unit_price) : ""}
                      onChange={(e) => handleCellChange(idx, "hps_unit_price", e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, idx, "hps_unit_price")}
                      className="w-full h-8 px-2 py-1 text-right bg-transparent tabular-nums text-muted-foreground focus:text-foreground outline-none focus:ring-1 focus:ring-ring focus:bg-accent/40 font-mono"
                    />
                  </td>

                  {/* Offer Unit Price */}
                  <td className="p-0 border-r border-border/80">
                    <input
                      id={`cell-${idx}-offer_unit_price`}
                      type="number"
                      disabled={isReadOnly}
                      value={line.offer_unit_price != null && !isNaN(Number(line.offer_unit_price)) ? Number(line.offer_unit_price) : ""}
                      onChange={(e) => handleCellChange(idx, "offer_unit_price", e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, idx, "offer_unit_price")}
                      className="w-full h-8 px-2 py-1 text-right bg-transparent tabular-nums text-muted-foreground focus:text-foreground outline-none focus:ring-1 focus:ring-ring focus:bg-accent/40 font-mono"
                    />
                  </td>

                  {/* Final / Negotiation Price */}
                  <td className="p-0 border-r border-border/80 relative">
                    <input
                      id={`cell-${idx}-final_unit_price`}
                      type="number"
                      disabled={isReadOnly}
                      value={line.final_unit_price != null && !isNaN(Number(line.final_unit_price)) ? Number(line.final_unit_price) : ""}
                      onChange={(e) => handleCellChange(idx, "final_unit_price", e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, idx, "final_unit_price")}
                      onBlur={() => handleBlur(idx, "final_unit_price")}
                      className={`w-full h-8 px-2 py-1 text-right bg-transparent tabular-nums font-bold outline-none focus:ring-1 focus:ring-ring focus:bg-accent/40 font-mono ${
                        isZeroPrice ? "text-amber-400 bg-amber-950/20" : "text-foreground"
                      }`}
                    />
                    {isZeroPrice && (
                      <span className="absolute left-1 top-2 text-[9px] font-mono px-1 py-0.2 rounded bg-amber-500/20 text-amber-300 pointer-events-none">
                        GRATIS
                      </span>
                    )}
                  </td>

                  {/* Discount */}
                  <td className="p-0 border-r border-border/80">
                    <input
                      id={`cell-${idx}-discount`}
                      type="number"
                      disabled={isReadOnly}
                      min="0"
                      max="100"
                      value={line.discount || 0}
                      onChange={(e) => handleCellChange(idx, "discount", e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, idx, "discount")}
                      className="w-full h-8 px-2 py-1 text-right bg-transparent tabular-nums text-muted-foreground focus:text-foreground outline-none focus:ring-1 focus:ring-ring focus:bg-accent/40 font-mono"
                    />
                  </td>

                  {/* Line Total (Calculated) */}
                  <td className="px-2 py-1 text-right font-bold text-foreground tabular-nums border-r border-border/80">
                    {formatIDR(line.line_total)}
                  </td>

                  {/* Delete Action */}
                  {!isReadOnly && (
                    <td className="px-1 py-1 text-center">
                      <button
                        type="button"
                        onClick={() => handleDeleteRow(idx)}
                        className="p-1 text-muted-foreground hover:text-red-400 rounded hover:bg-muted transition"
                        title="Hapus baris ini"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Financial Recap Table (Server-Authoritative & Decimal Protected) */}
      <div className="border-t border-border bg-muted/30 p-4 font-mono select-none">
        <div className="max-w-4xl ml-auto space-y-1.5 text-xs">
          {/* Subtotal */}
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground uppercase text-[11px]">Subtotal (Nilai Barang Bersih):</span>
            <span className="font-bold tabular-nums text-foreground">{formatIDR(computedSubtotal)}</span>
          </div>

          {/* Tax Breakdown */}
          {taxDetails.map((td) => (
            <div key={td.tax_type} className="flex items-center justify-between text-[11px]">
              <span className="text-muted-foreground">
                Pajak {td.tax_type} ({td.rate}%):
              </span>
              <span className="font-medium tabular-nums text-foreground">{formatIDR(td.amount)}</span>
            </div>
          ))}

          {/* Grand Total */}
          <div className="flex items-center justify-between pt-1.5 border-t border-border text-sm">
            <span className="font-bold text-foreground uppercase tracking-wide">
              Grand Total (Termasuk PPN):
            </span>
            <span className="font-bold tabular-nums text-foreground text-base text-emerald-400">
              {formatIDR(computedGrandTotal)}
            </span>
          </div>

          {/* Terbilang String */}
          <div className="pt-1 text-[11px] text-muted-foreground font-sans italic">
            <span className="font-semibold text-foreground font-mono not-italic uppercase text-[10px] mr-1">
              Terbilang:
            </span>
            &quot;{computedTerbilang}&quot;
          </div>
        </div>
      </div>

      {/* Zero Price Justification Modal */}
      {zeroPriceTarget && (
        <ZeroPriceModal
          isOpen={true}
          itemNumber={zeroPriceTarget.line.line_number}
          itemDescription={zeroPriceTarget.line.confirmed_description || zeroPriceTarget.line.original_description}
          initialReason={zeroPriceTarget.line.notes || ""}
          onConfirm={(reason) => {
            const updated = [...lines];
            updated[zeroPriceTarget.row] = {
              ...updated[zeroPriceTarget.row],
              notes: reason,
            };
            setLines(updated);
            onLinesChanged(updated);
            setZeroPriceTarget(null);
          }}
          onCancel={() => setZeroPriceTarget(null)}
        />
      )}
    </div>
  );
}
