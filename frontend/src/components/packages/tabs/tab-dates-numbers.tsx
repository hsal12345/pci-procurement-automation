"use client";

import { useState, useEffect } from "react";
import { PackageRevision, DocumentEvent, DocumentNumber } from "@/types/package";
import { formatDateIndo } from "@/lib/formatters";
import { Calendar, Hash, AlertTriangle, CheckCircle2, Sparkles } from "lucide-react";

interface TabDatesNumbersProps {
  revision: PackageRevision;
  isReadOnly: boolean;
  onDataChanged: (payload: { events: DocumentEvent[]; numbers: DocumentNumber[] }) => void;
}

// Strict BR07 Chronological Lifecycle Sequence & Canonical 13 Documents (PRD Section 7)
export interface EventItemConfig {
  code: string;
  doc_code: string;
  name: string;
  issuer: "SCHOOL" | "COMPANY" | "JOINT";
}

const EVENT_ORDER: EventItemConfig[] = [
  { code: "HPS", doc_code: "D01", name: "Harga Perkiraan Sendiri (HPS)", issuer: "SCHOOL" },
  { code: "SPP", doc_code: "D02", name: "Surat Permintaan Penawaran (SPP)", issuer: "SCHOOL" },
  { code: "PENAWARAN", doc_code: "D03", name: "Surat Penawaran Harga (Rekanan)", issuer: "COMPANY" },
  { code: "NEGOSIASI", doc_code: "D04", name: "Berita Acara Klarifikasi & Negosiasi", issuer: "JOINT" },
  { code: "PESANAN", doc_code: "D05", name: "Surat Pesanan (SP)", issuer: "SCHOOL" },
  { code: "SURAT_JALAN", doc_code: "D08", name: "Surat Jalan / Pengantar Pengiriman", issuer: "COMPANY" },
  { code: "BAPB", doc_code: "D09", name: "Berita Acara Pemeriksaan Barang (BAPB)", issuer: "SCHOOL" },
  { code: "BAST", doc_code: "D10", name: "Berita Acara Serah Terima (BAST Sekolah)", issuer: "SCHOOL" },
  { code: "BAST_REKANAN", doc_code: "D13", name: "BAST Rekanan (CV PCI)", issuer: "COMPANY" },
  { code: "BAPP", doc_code: "D11", name: "Berita Acara Pembayaran (BAPP)", issuer: "SCHOOL" },
  { code: "LAMP_BAPP", doc_code: "D12", name: "Lampiran Berita Acara Pembayaran (Lamp BAPP)", issuer: "SCHOOL" },
  { code: "FAKTUR", doc_code: "D06", name: "Faktur Tagihan Pajak (Invoice)", issuer: "COMPANY" },
  { code: "KWITANSI", doc_code: "D07", name: "Kwitansi Pembayaran Resmi BOS", issuer: "SCHOOL" },
];

/**
 * Helper to add business days (skipping Saturday and Sunday)
 */
function addBusinessDays(startDateStr: string, daysToAdd: number): string {
  if (!startDateStr) return "";
  const [y, m, d] = startDateStr.split("-").map(Number);
  const cur = new Date(Date.UTC(y, m - 1, d));
  let added = 0;
  while (added < daysToAdd) {
    cur.setUTCDate(cur.getUTCDate() + 1);
    const dayOfWeek = cur.getUTCDay();
    // 0 = Sunday, 6 = Saturday
    if (dayOfWeek !== 0 && dayOfWeek !== 6) {
      added++;
    }
  }
  // Ensure it never lands on weekend
  while (cur.getUTCDay() === 0 || cur.getUTCDay() === 6) {
    cur.setUTCDate(cur.getUTCDate() + 1);
  }
  return cur.toISOString().split("T")[0];
}

export function TabDatesNumbers({ revision, isReadOnly, onDataChanged }: TabDatesNumbersProps) {
  const [events, setEvents] = useState<DocumentEvent[]>(() => revision.events || []);
  const [numbers, setNumbers] = useState<DocumentNumber[]>(() => revision.numbers || []);
  const [autoDateNotice, setAutoDateNotice] = useState<string | null>(null);
  const [autoNumberNotice, setAutoNumberNotice] = useState<string | null>(null);

  useEffect(() => {
    if (revision.events) setEvents(revision.events);
    if (revision.numbers) setNumbers(revision.numbers);
  }, [revision]);

  // Find date for an event code with backward-compatible alias fallback
  const getDate = (code: string): string => {
    let ev = events.find((e) => e.event_code === code);
    if (ev?.event_date) return ev.event_date;

    // Legacy aliases and shared dates
    if (code === "PENAWARAN") ev = events.find((e) => e.event_code === "SPN");
    else if (code === "NEGOSIASI") ev = events.find((e) => e.event_code === "BA_KLARIFIKASI");
    else if (code === "PESANAN") ev = events.find((e) => e.event_code === "SP");
    else if (code === "SURAT_JALAN") ev = events.find((e) => e.event_code === "SJ");
    else if (code === "LAMP_BAPP") ev = events.find((e) => e.event_code === "BAPP");
    else if (code === "KWITANSI") ev = events.find((e) => e.event_code === "FAKTUR");
    else if (code === "FAKTUR") ev = events.find((e) => e.event_code === "KWITANSI");

    return ev?.event_date || "";
  };

  const getNumber = (docCode: string, eventCode: string): DocumentNumber | undefined => {
    return numbers.find((n) => n.doc_code === docCode || n.doc_code === eventCode);
  };

  const handleDateChange = (eventCode: string, newDate: string) => {
    let updatedEvents = [...events];

    const setOrUpdate = (code: string, dt: string) => {
      const idx = updatedEvents.findIndex((e) => e.event_code === code);
      if (idx >= 0) {
        updatedEvents[idx] = { ...updatedEvents[idx], event_date: dt };
      } else {
        updatedEvents.push({ event_code: code, event_date: dt });
      }
    };

    setOrUpdate(eventCode, newDate);

    // Auto-sync Stage 9: If FAKTUR is modified, keep KWITANSI in sync
    if (eventCode === "FAKTUR") {
      setOrUpdate("KWITANSI", newDate);
    } else if (eventCode === "KWITANSI") {
      setOrUpdate("FAKTUR", newDate);
    } else if (eventCode === "BAPP") {
      setOrUpdate("LAMP_BAPP", newDate);
    } else if (eventCode === "LAMP_BAPP") {
      setOrUpdate("BAPP", newDate);
    }

    // Clean up any orphan legacy alias codes
    updatedEvents = updatedEvents.filter(
      (e) => !["SPN", "BA_KLARIFIKASI", "SP", "SJ"].includes(e.event_code)
    );

    setEvents(updatedEvents);
    onDataChanged({ events: updatedEvents, numbers });
  };

  const handleNumberChange = (
    docCode: string,
    newNumber: string,
    defaultIssuer: "SCHOOL" | "COMPANY" | "JOINT" = "SCHOOL"
  ) => {
    const updatedNumbers = [...numbers];
    const existingIdx = updatedNumbers.findIndex((n) => n.doc_code === docCode);
    if (existingIdx >= 0) {
      updatedNumbers[existingIdx] = { ...updatedNumbers[existingIdx], doc_number: newNumber };
    } else {
      updatedNumbers.push({
        doc_code: docCode,
        doc_number: newNumber,
        issuer: defaultIssuer,
        is_reserved: defaultIssuer === "COMPANY",
      });
    }
    setNumbers(updatedNumbers);
    onDataChanged({ events, numbers: updatedNumbers });
  };

  // Feature: Otomatiskan Rangkaian Tanggal dari HPS
  const handleAutomateDates = () => {
    const hpsDate = getDate("HPS");
    if (!hpsDate) {
      alert("Silakan pilih Tanggal HPS (Urutan 1) terlebih dahulu sebagai tanggal acuan siklus pengadaan.");
      return;
    }

    const updatedEvents = [...events];
    const setOrUpdate = (code: string, dt: string) => {
      const idx = updatedEvents.findIndex((e) => e.event_code === code);
      if (idx >= 0) {
        updatedEvents[idx] = { ...updatedEvents[idx], event_date: dt };
      } else {
        updatedEvents.push({ event_code: code, event_date: dt });
      }
    };

    // Calculate progression on business days
    const dHps = hpsDate;
    const dSpp = addBusinessDays(dHps, 1);
    const dPenawaran = addBusinessDays(dSpp, 2);
    const dNegosiasi = addBusinessDays(dPenawaran, 1);
    const dPesanan = addBusinessDays(dNegosiasi, 1);
    const dSuratJalan = addBusinessDays(dPesanan, 2);
    const dBapb = addBusinessDays(dSuratJalan, 1);
    const dBast = dBapb;
    const dBastRekanan = dBast;
    const dBapp = addBusinessDays(dBast, 1);
    const dLampBapp = dBapp;
    const dFaktur = addBusinessDays(dBapp, 1);
    const dKwitansi = dFaktur;

    setOrUpdate("HPS", dHps);
    setOrUpdate("SPP", dSpp);
    setOrUpdate("PENAWARAN", dPenawaran);
    setOrUpdate("NEGOSIASI", dNegosiasi);
    setOrUpdate("PESANAN", dPesanan);
    setOrUpdate("SURAT_JALAN", dSuratJalan);
    setOrUpdate("BAPB", dBapb);
    setOrUpdate("BAST", dBast);
    setOrUpdate("BAST_REKANAN", dBastRekanan);
    setOrUpdate("BAPP", dBapp);
    setOrUpdate("LAMP_BAPP", dLampBapp);
    setOrUpdate("FAKTUR", dFaktur);
    setOrUpdate("KWITANSI", dKwitansi);

    // Clean legacy alias codes
    const cleanEvents = updatedEvents.filter(
      (e) => !["SPN", "BA_KLARIFIKASI", "SP", "SJ"].includes(e.event_code)
    );

    setEvents(cleanEvents);
    onDataChanged({ events: cleanEvents, numbers });
    setAutoDateNotice(`Rangkaian tanggal berhasil diotomatisasi dari HPS (${formatDateIndo(dHps)}).`);
  };

  // Feature: Otomatiskan Nomor Dokumen
  const handleAutomateNumbers = (overwriteAll = false) => {
    const year = revision.fiscal_year || 2026;
    const schoolSnap = revision.school_snapshot as any;
    let schoolCode = "BOS";

    if (schoolSnap?.name) {
      const nameClean = schoolSnap.name.toUpperCase();
      if (nameClean.includes("KEBON KOSONG") && nameClean.includes("09")) {
        schoolCode = "SDN-KK09";
      } else if (schoolSnap.npsn) {
        schoolCode = `SD-${schoolSnap.npsn}`;
      } else {
        const words = nameClean
          .replace(/[^A-Z0-9\s]/g, "")
          .split(/\s+/)
          .filter((w: string) => !["SEKOLAH", "DASAR", "NEGERI"].includes(w));
        schoolCode = words.slice(0, 3).join("") || "BOS";
      }
    } else if (schoolSnap?.npsn) {
      schoolCode = `SD-${schoolSnap.npsn}`;
    }

    const defaultNumbersMap: Record<string, { number: string; issuer: "SCHOOL" | "COMPANY" | "JOINT" }> = {
      D01: { number: `01/HPS/${schoolCode}/${year}`, issuer: "SCHOOL" },
      D02: { number: `02/SPP/${schoolCode}/${year}`, issuer: "SCHOOL" },
      D03: { number: `03/SPN-PCI/${year}`, issuer: "COMPANY" },
      D04: { number: `04/BA-NEGO/${schoolCode}/${year}`, issuer: "JOINT" },
      D05: { number: `05/SP/${schoolCode}/${year}`, issuer: "SCHOOL" },
      D06: { number: `06/INV-PCI/${year}`, issuer: "COMPANY" },
      D07: { number: `07/KWT/${schoolCode}/${year}`, issuer: "SCHOOL" },
      D08: { number: `08/SJ-PCI/${year}`, issuer: "COMPANY" },
      D09: { number: `09/BAPB/${schoolCode}/${year}`, issuer: "SCHOOL" },
      D10: { number: `10/BAST/${schoolCode}/${year}`, issuer: "SCHOOL" },
      D11: { number: `11/BAPP/${schoolCode}/${year}`, issuer: "SCHOOL" },
      D12: { number: `12/LAMP-BAPP/${schoolCode}/${year}`, issuer: "SCHOOL" },
      D13: { number: `13/BAST-PCI/${year}`, issuer: "COMPANY" },
    };

    const updatedNumbers = [...numbers];

    Object.entries(defaultNumbersMap).forEach(([docCode, def]) => {
      const idx = updatedNumbers.findIndex((n) => n.doc_code === docCode);
      if (idx >= 0) {
        if (overwriteAll || !updatedNumbers[idx].doc_number || updatedNumbers[idx].doc_number.trim() === "") {
          updatedNumbers[idx] = {
            ...updatedNumbers[idx],
            doc_number: def.number,
            issuer: updatedNumbers[idx].issuer || def.issuer,
          };
        }
      } else {
        updatedNumbers.push({
          doc_code: docCode,
          doc_number: def.number,
          issuer: def.issuer,
          is_reserved: def.issuer === "COMPANY",
        });
      }
    });

    setNumbers(updatedNumbers);
    onDataChanged({ events, numbers: updatedNumbers });
    setAutoNumberNotice("Nomor 13 dokumen pengadaan berhasil diisi otomatis sesuai format resmi.");
  };

  return (
    <div className="p-6 max-w-5xl space-y-6 text-xs font-sans">
      {/* Automation Toolbar */}
      <div className="border border-border/80 rounded-lg bg-card p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              Otomatisasi Cerdas Tanggal & Nomor Dokumen
            </h3>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Pilih Tanggal HPS (Urutan 1), lalu klik tombol otomatisasi untuk mengisi seluruh rangkaian tanggal dan nomor dokumen secara kronologis (BR07 & BR02).
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              id="btn-auto-dates"
              disabled={isReadOnly}
              onClick={handleAutomateDates}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors shadow-sm disabled:opacity-50"
            >
              <Calendar className="w-3.5 h-3.5" />
              🪄 Otomatiskan Tanggal (dari HPS)
            </button>

            <button
              type="button"
              id="btn-auto-numbers"
              disabled={isReadOnly}
              onClick={() => handleAutomateNumbers(false)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-secondary text-secondary-foreground text-xs font-semibold hover:bg-secondary/80 transition-colors border border-border disabled:opacity-50"
            >
              <Hash className="w-3.5 h-3.5" />
              ⚡ Otomatiskan Nomor Dokumen
            </button>
          </div>
        </div>

        {/* Notices */}
        {(autoDateNotice || autoNumberNotice) && (
          <div className="flex flex-wrap gap-2 pt-2 border-t border-border/40 text-[11px] font-mono">
            {autoDateNotice && (
              <span className="px-2.5 py-1 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                {autoDateNotice}
              </span>
            )}
            {autoNumberNotice && (
              <span className="px-2.5 py-1 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30 flex items-center gap-1.5 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5 text-sky-400" />
                {autoNumberNotice}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Timeline Warning Explanation */}
      <div className="border border-border rounded bg-muted/40 p-3 flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="font-mono text-muted-foreground flex items-center gap-1.5 font-medium">
          <Calendar className="w-3.5 h-3.5 text-primary flex-shrink-0" />
          <span>
            Urutan Kronologis Resmi (BR07): [HPS/SPP] ≤ Penawaran ≤ Negosiasi ≤ Pesanan ≤ Surat Jalan ≤ BAPB ≤ BAST ≤ BAPP ≤ [Faktur & Kwitansi]
          </span>
        </span>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-bold">
          13 Dokumen Lengkap (D01-D13)
        </span>
      </div>

      {/* Chronological Table */}
      <div className="border border-border rounded-lg bg-card overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-muted/90 border-b border-border text-[11px] uppercase font-mono font-bold tracking-wider text-slate-200">
              <th className="px-3 py-2.5 w-10 text-center">Urutan</th>
              <th className="px-3 py-2.5 min-w-[220px]">Dokumen / Peristiwa Siklus</th>
              <th className="px-3 py-2.5 w-48">Tanggal Terpilih</th>
              <th className="px-3 py-2.5 min-w-[200px]">Nomor Dokumen</th>
              <th className="px-3 py-2.5 w-28 text-center">Penerbit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border font-mono text-[11px]">
            {EVENT_ORDER.map((item, idx) => {
              const currentDate = getDate(item.code);
              const prevItem = idx > 0 ? EVENT_ORDER[idx - 1] : null;
              const prevDate = prevItem ? getDate(prevItem.code) : "";

              // Inline Chronology Inversion Check (BR07)
              const isInverted = Boolean(
                prevDate && currentDate && new Date(currentDate) < new Date(prevDate)
              );

              const docNum = getNumber(item.doc_code, item.code);
              const isCompanyGenerated = docNum?.issuer === "COMPANY" || item.issuer === "COMPANY";

              return (
                <tr
                  key={item.code}
                  className={`hover:bg-primary/5 transition-colors ${
                    isInverted ? "bg-red-500/10" : ""
                  }`}
                >
                  {/* Sequence # */}
                  <td className="px-3 py-2 text-center text-muted-foreground font-bold">
                    {idx + 1}
                  </td>

                  {/* Document Title */}
                  <td className="px-3 py-2 font-sans font-medium text-foreground">
                    <div>{item.name}</div>
                    <div className="flex items-center gap-1 text-[10px] font-mono text-muted-foreground mt-0.5">
                      <span>Event: {item.code}</span>
                      <span>•</span>
                      <span className="font-bold text-foreground">Doc: {item.doc_code}</span>
                    </div>
                  </td>

                  {/* Reactive Date Picker with Dynamic Min */}
                  <td className="px-3 py-2">
                    <div className="space-y-1">
                      <input
                        type="date"
                        id={`date-${item.code.toLowerCase()}`}
                        disabled={isReadOnly}
                        value={currentDate}
                        min={prevDate || undefined}
                        onChange={(e) => handleDateChange(item.code, e.target.value)}
                        className={`w-full px-2.5 py-1.5 bg-background border rounded text-xs outline-none focus:ring-2 focus:ring-primary font-mono tabular-nums ${
                          isInverted ? "border-red-500 text-red-300 font-bold" : "border-border text-foreground"
                        }`}
                      />
                      {isInverted && (
                        <div className="text-[10px] text-red-300 font-sans flex items-center gap-1 font-semibold">
                          <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                          <span>Mendahului {prevItem?.name}</span>
                        </div>
                      )}
                      {currentDate && !isInverted && (
                        <div className="text-[10px] text-muted-foreground font-sans truncate">
                          {formatDateIndo(currentDate)}
                        </div>
                      )}
                    </div>
                  </td>

                  {/* Document Number */}
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        id={`docnum-${item.doc_code.toLowerCase()}`}
                        disabled={isReadOnly}
                        value={docNum?.doc_number || ""}
                        onChange={(e) => handleNumberChange(item.doc_code, e.target.value, item.issuer)}
                        placeholder={`Contoh: ${item.doc_code === "D03" ? "03/SPN-PCI/2026" : `Nomor ${item.doc_code}`}`}
                        className={`w-full px-2.5 py-1.5 bg-background border rounded text-xs outline-none focus:ring-2 focus:ring-primary font-mono ${
                          isCompanyGenerated
                            ? "border-purple-500/40 text-purple-200 focus:border-purple-400"
                            : "border-border text-foreground"
                        }`}
                      />
                      {isCompanyGenerated && (
                        <span className="text-[9px] font-mono text-purple-300 px-1.5 py-0.5 rounded bg-purple-500/15 border border-purple-500/30 flex-shrink-0 font-bold">
                          REKANAN
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Issuer Badge */}
                  <td className="px-3 py-2 text-center">
                    <span
                      className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border ${
                        item.issuer === "COMPANY"
                          ? "bg-purple-500/15 text-purple-300 border-purple-500/30"
                          : item.issuer === "SCHOOL"
                          ? "bg-sky-500/15 text-sky-300 border-sky-500/30"
                          : "bg-zinc-500/15 text-zinc-300 border-zinc-500/30"
                      }`}
                    >
                      {item.issuer}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
