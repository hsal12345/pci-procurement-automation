/**
 * Strict Indonesian Financial & Identifier Formatters
 * Formats numbers with tabular-nums and prevents leading zero truncation.
 */

export function formatIDR(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined || amount === "") return "Rp 0,00";
  const cleanStr = typeof amount === "string" ? amount.replace(/,/g, ".") : String(amount);
  const num = parseFloat(cleanStr);
  if (isNaN(num)) return "Rp 0,00";

  const isNegative = num < 0;
  const absNum = Math.abs(num);
  const parts = absNum.toFixed(2).split(".");
  const integerPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const decimalPart = parts[1] || "00";

  return `${isNegative ? "-" : ""}Rp ${integerPart},${decimalPart}`;
}

export function formatQuantity(qty: number | string | null | undefined): string {
  if (qty === null || qty === undefined || qty === "") return "0";
  const cleanStr = typeof qty === "string" ? qty.replace(/,/g, ".") : String(qty);
  const num = parseFloat(cleanStr);
  if (isNaN(num)) return "0";

  // If whole number, format without decimals
  if (num % 1 === 0) {
    return Math.round(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }
  // Otherwise format with comma for decimal separator (e.g. 2,5)
  const parts = num.toString().split(".");
  const intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${intPart},${parts[1]}`;
}

export function formatPlainIDR(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined || amount === "") return "0,00";
  const cleanStr = typeof amount === "string" ? amount.replace(/,/g, ".") : String(amount);
  const num = parseFloat(cleanStr);
  if (isNaN(num)) return "0,00";

  const isNegative = num < 0;
  const absNum = Math.abs(num);
  const parts = absNum.toFixed(2).split(".");
  const integerPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const decimalPart = parts[1] || "00";

  return `${isNegative ? "-" : ""}${integerPart},${decimalPart}`;
}

export function formatTabularNumber(
  val: number | string | null | undefined,
  decimals: number = 0
): string {
  if (val === null || val === undefined || val === "") return "0";
  const num = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(num)) return "0";

  const parts = num.toFixed(decimals).split(".");
  const integerPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  if (decimals > 0 && parts[1]) {
    return `${integerPart},${parts[1]}`;
  }
  return integerPart;
}

export function normalizeLeadingZeros(
  val: string | number | null | undefined,
  targetLength?: number
): string {
  if (val === null || val === undefined) return "";
  const str = String(val).trim();
  if (targetLength && str.length < targetLength && /^\d+$/.test(str)) {
    return str.padStart(targetLength, "0");
  }
  return str;
}

const HARI_INDO = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
const BULAN_INDO = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni",
  "Juli", "Agustus", "September", "Oktober", "November", "Desember"
];

export function formatDateIndo(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return "-";
  try {
    const d = typeof dateInput === "string" ? new Date(dateInput) : dateInput;
    if (isNaN(d.getTime())) return String(dateInput);

    const hari = HARI_INDO[d.getDay()];
    const tanggal = d.getDate();
    const bulan = BULAN_INDO[d.getMonth()];
    const tahun = d.getFullYear();

    return `${hari}, ${tanggal} ${bulan} ${tahun}`;
  } catch {
    return String(dateInput);
  }
}

export function formatShortDateIndo(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return "-";
  try {
    const d = typeof dateInput === "string" ? new Date(dateInput) : dateInput;
    if (isNaN(d.getTime())) return String(dateInput);

    const dd = String(d.getDate()).padStart(2, "0");
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const yyyy = d.getFullYear();

    return `${dd}/${mm}/${yyyy}`;
  } catch {
    return String(dateInput);
  }
}

/**
 * Deterministic Indonesian Currency Words (Terbilang)
 * Exact mirror of Python backend terbilang algorithm (1 to trillions)
 */
export function terbilangIndonesian(n: number | string | null | undefined): string {
  if (n === null || n === undefined || n === "") return "Nol Rupiah";
  const num = Math.floor(typeof n === "string" ? parseFloat(n) : n);
  if (isNaN(num) || num === 0) return "Nol Rupiah";

  const satuan = [
    "", "Satu", "Dua", "Tiga", "Empat", "Lima",
    "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"
  ];

  function convertChunk(val: number): string {
    if (val < 12) {
      return satuan[val];
    } else if (val < 20) {
      return convertChunk(val - 10) + " Belas";
    } else if (val < 100) {
      return convertChunk(Math.floor(val / 10)) + " Puluh " + convertChunk(val % 10);
    } else if (val < 200) {
      return "Seratus " + convertChunk(val - 100);
    } else if (val < 1000) {
      return convertChunk(Math.floor(val / 100)) + " Ratus " + convertChunk(val % 100);
    } else if (val < 2000) {
      return "Seribu " + convertChunk(val - 1000);
    } else if (val < 1000000) {
      return convertChunk(Math.floor(val / 1000)) + " Ribu " + convertChunk(val % 1000);
    } else if (val < 1000000000) {
      return convertChunk(Math.floor(val / 1000000)) + " Juta " + convertChunk(val % 1000000);
    } else if (val < 1000000000000) {
      return convertChunk(Math.floor(val / 1000000000)) + " Milyar " + convertChunk(val % 1000000000);
    } else {
      return convertChunk(Math.floor(val / 1000000000000)) + " Triliun " + convertChunk(val % 1000000000000);
    }
  }

  const result = convertChunk(Math.abs(num))
    .replace(/\s+/g, " ")
    .trim();

  return `${num < 0 ? "Minus " : ""}${result} Rupiah`;
}
