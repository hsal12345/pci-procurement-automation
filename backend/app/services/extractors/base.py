"""Shared base helpers and unified intermediate representation for multi-format document extraction."""
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Tuple

TABLE_HEADER_TOKENS = {
    "no",
    "nama barang",
    "uraian",
    "deskripsi",
    "volume",
    "banyaknya",
    "kuantitas",
    "qty",
    "satuan",
    "spesifikasi",
    "spek",
    "harga",
    "hps",
    "total",
    "jumlah",
}

TABLE_TERMINAL_TOKENS = {"jumlah", "total", "subtotal", "grand total", "jumlah total"}

DEFAULT_EVENTS_CANDIDATE = [
    {"event_code": "HPS", "event_date": "2026-06-02", "day_name_id": "Selasa"},
    {"event_code": "SPP", "event_date": "2026-06-02", "day_name_id": "Selasa"},
    {"event_code": "PENAWARAN", "event_date": "2026-06-05", "day_name_id": "Jumat"},
    {"event_code": "NEGOSIASI", "event_date": "2026-06-10", "day_name_id": "Rabu"},
    {"event_code": "PESANAN", "event_date": "2026-06-12", "day_name_id": "Jumat"},
    {"event_code": "SURAT_JALAN", "event_date": "2026-06-16", "day_name_id": "Selasa"},
    {"event_code": "BAPB", "event_date": "2026-06-16", "day_name_id": "Selasa"},
    {"event_code": "BAST", "event_date": "2026-06-16", "day_name_id": "Selasa"},
    {"event_code": "BAST_REKANAN", "event_date": "2026-06-16", "day_name_id": "Selasa"},
    {"event_code": "BAPP", "event_date": "2026-06-16", "day_name_id": "Selasa"},
    {"event_code": "FAKTUR", "event_date": "2026-06-16", "day_name_id": "Selasa"},
    {"event_code": "KWITANSI", "event_date": "2026-06-16", "day_name_id": "Selasa"},
]

_DAY_NAMES_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
_MONTH_TO_QUARTER = {
    "januari": 1, "jan": 1,
    "februari": 1, "feb": 1,
    "maret": 1, "mar": 1,
    "april": 2, "apr": 2,
    "mei": 2,
    "juni": 2, "jun": 2,
    "juli": 3, "jul": 3,
    "agustus": 3, "agu": 3, "agt": 3,
    "september": 3, "sep": 3,
    "oktober": 4, "okt": 4,
    "november": 4, "nov": 4,
    "desember": 4, "des": 4,
}


def _next_weekday(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def build_default_events_for_period(fiscal_year: int = 2026, quarter: int = 2) -> List[Dict[str, Any]]:
    """Generates chronologically valid procurement DocumentEvent candidates inside fiscal_year and quarter."""
    q = quarter if quarter in (1, 2, 3, 4) else 2
    fy = fiscal_year if isinstance(fiscal_year, int) and 2000 <= fiscal_year <= 2100 else 2026
    if fy == 2026 and q == 2:
        return [dict(item) for item in DEFAULT_EVENTS_CANDIDATE]

    month_map = {1: 3, 2: 6, 3: 9, 4: 11}
    base_date = _next_weekday(date(fy, month_map[q], 2))
    d_hps = base_date
    d_penawaran = _next_weekday(d_hps + timedelta(days=3))
    d_nego = _next_weekday(d_penawaran + timedelta(days=3))
    d_pesanan = _next_weekday(d_nego + timedelta(days=2))
    d_serah = _next_weekday(d_pesanan + timedelta(days=3))

    schedule = [
        ("HPS", d_hps),
        ("SPP", d_hps),
        ("PENAWARAN", d_penawaran),
        ("NEGOSIASI", d_nego),
        ("PESANAN", d_pesanan),
        ("SURAT_JALAN", d_serah),
        ("BAPB", d_serah),
        ("BAST", d_serah),
        ("BAST_REKANAN", d_serah),
        ("BAPP", d_serah),
        ("FAKTUR", d_serah),
        ("KWITANSI", d_serah),
    ]
    return [
        {
            "event_code": code,
            "event_date": dt.isoformat(),
            "day_name_id": _DAY_NAMES_ID[dt.weekday()],
        }
        for code, dt in schedule
    ]


def normalize_school_name(name: Optional[str], *, strip_shift: bool = False, strip_leading_zeros: bool = False) -> str:
    """Normalizes Indonesian school names so variants like 'SDN', 'SD NEGERI', and 'SEKOLAH DASAR NEGERI' match."""
    if not name:
        return ""
    txt = str(name).upper()
    txt = re.sub(r"[^A-Z0-9\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    replacements = [
        (r"\bSEKOLAH DASAR NEGERI\b", "SDN"),
        (r"\bSD NEGERI\b", "SDN"),
        (r"\bSEKOLAH DASAR SWASTA\b", "SDS"),
        (r"\bSD SWASTA\b", "SDS"),
        (r"\bSEKOLAH DASAR INPRES\b", "SDI"),
        (r"\bSD INPRES\b", "SDI"),
        (r"\bSEKOLAH MENENGAH PERTAMA NEGERI\b", "SMPN"),
        (r"\bSMP NEGERI\b", "SMPN"),
        (r"\bSEKOLAH MENENGAH ATAS NEGERI\b", "SMAN"),
        (r"\bSMA NEGERI\b", "SMAN"),
        (r"\bSEKOLAH MENENGAH KEJURUAN NEGERI\b", "SMKN"),
        (r"\bSMK NEGERI\b", "SMKN"),
    ]
    for pattern, repl in replacements:
        txt = re.sub(pattern, repl, txt)
    if strip_shift:
        txt = re.sub(r"\b(PAGI|PETANG|SIANG|SORE)\b", "", txt)
    if strip_leading_zeros:
        txt = re.sub(r"\b0+(\d+)\b", r"\1", txt)
    return re.sub(r"\s+", " ", txt).strip()


def match_school_record(
    schools: Iterable[Any],
    *,
    candidate_name: Optional[str] = None,
    npsn: Optional[str] = None,
) -> Optional[Any]:
    """Finds the best matching Master School by NPSN first, then canonical normalized name."""
    school_list = list(schools)
    if not school_list:
        return None

    clean_npsn = re.sub(r"\D", "", str(npsn or ""))
    if clean_npsn:
        for s in school_list:
            s_npsn = re.sub(r"\D", "", str(getattr(s, "npsn", "") or (s.get("npsn") if isinstance(s, dict) else "") or ""))
            if s_npsn and s_npsn == clean_npsn:
                return s

    if not candidate_name:
        return None

    def _get_name(item: Any) -> str:
        if isinstance(item, dict):
            return str(item.get("name") or "")
        return str(getattr(item, "name", "") or "")

    # Pass 1: exact normalized match (SDN == SD NEGERI == SEKOLAH DASAR NEGERI)
    cand_norm = normalize_school_name(candidate_name, strip_shift=False)
    if cand_norm:
        for s in school_list:
            if normalize_school_name(_get_name(s), strip_shift=False) == cand_norm:
                return s

    # Pass 2: ignore shift tokens (PAGI/PETANG/SIANG) and leading zeros (09 vs 9)
    cand_relaxed = normalize_school_name(candidate_name, strip_shift=True, strip_leading_zeros=True)
    if cand_relaxed:
        for s in school_list:
            if normalize_school_name(_get_name(s), strip_shift=True, strip_leading_zeros=True) == cand_relaxed:
                return s

    # Pass 3: substring containment on canonical names of sufficient length
    if len(cand_relaxed) >= 8:
        for s in school_list:
            s_rel = normalize_school_name(_get_name(s), strip_shift=True, strip_leading_zeros=True)
            if len(s_rel) >= 8 and (s_rel in cand_relaxed or cand_relaxed in s_rel):
                return s

    return None


@dataclass
class ExtractedSection:
    """Normalized tabular section (Excel worksheet, Word table, or PDF page/table)."""

    name: str
    grid: List[List[Any]]
    context_snippets: List[str] = field(default_factory=list)
    page_number: Optional[int] = None


def clean_cell_text(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return str(val)
    text = str(val).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\n]+", " ", text).strip()
    return text


def serialize_grid_cell(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (int, float, bool)):
        return val
    cleaned = clean_cell_text(val)
    return cleaned if cleaned != "" else None


def parse_decimal_value(raw_val: Any, default: Optional[Decimal] = None) -> Optional[Decimal]:
    """Parses Indonesian/standard numeric strings cleanly (e.g. 'Rp 16.500,00' or '1,500')."""
    if raw_val is None or str(raw_val).strip() == "":
        return default
    if isinstance(raw_val, Decimal):
        return raw_val
    if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool):
        try:
            return Decimal(str(raw_val))
        except Exception:
            return default

    txt = clean_cell_text(raw_val)
    txt = re.sub(r"^(rp\.?\s*|idr\s*)", "", txt, flags=re.IGNORECASE).strip()
    txt = re.sub(r"/-$", "", txt).strip()
    # Keep only leading sign, digits, commas, dots
    match = re.search(r"-?[\d.,]+", txt)
    if not match:
        return default
    txt = match.group(0)

    if "," in txt and "." in txt:
        if txt.rfind(",") > txt.rfind("."):
            txt = txt.replace(".", "").replace(",", ".")
        else:
            txt = txt.replace(",", "")
    elif "," in txt:
        parts = txt.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
            txt = "".join(parts)
        else:
            txt = txt.replace(",", ".")
    elif "." in txt:
        parts = txt.split(".")
        if len(parts) >= 2 and all(len(p) == 3 and p.isdigit() for p in parts[1:]):
            txt = "".join(parts)
    try:
        return Decimal(txt)
    except (InvalidOperation, ValueError):
        return default


_ROMAN_TO_QUARTER = {
    "IV": 4,
    "III": 3,
    "II": 2,
    "I": 1,
    "4": 4,
    "3": 3,
    "2": 2,
    "1": 1,
}


def extract_quarter_from_text(text: str, *, allow_month_fallback: bool = True) -> Optional[int]:
    """Detects Indonesian fiscal quarter (Triwulan I-IV / TW 1-4 / Q1-Q4) or month fallback."""
    if not text:
        return None
    clean = clean_cell_text(text)
    explicit_patterns = [
        r"\b(?:triwulan|trw|tw|quarter|kuartal|q)\s*(?:ke[-\s]*)?[-:.]?\s*(III|II|IV|I|[1-4])\b",
        r"\b(?:triwulan|tw|q)\s*(1|2|3|4)\b",
    ]
    for pat in explicit_patterns:
        m = re.search(pat, clean, flags=re.IGNORECASE)
        if m:
            tok = m.group(1).upper()
            if tok in _ROMAN_TO_QUARTER:
                return _ROMAN_TO_QUARTER[tok]

    if allow_month_fallback:
        lower = clean.lower()
        for month_name, q_num in _MONTH_TO_QUARTER.items():
            if re.search(rf"\b{month_name}\b", lower):
                return q_num
    return None


def _clean_extracted_school_name(raw_val: str) -> str:
    cleaned = clean_cell_text(raw_val)
    cleaned = re.sub(
        r"^(?:nama\s+sekolah|satuan\s+pendidikan|sekolah|instansi)\s*[:\-–]\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    if "|" in cleaned:
        parts = [p.strip() for p in cleaned.split("|") if p.strip()]
        for part in parts:
            u = part.upper()
            if any(kw in u for kw in ("SEKOLAH DASAR", "SDN", "SD NEGERI", "SMP", "SMA", "SMK", "MADRASAH")):
                cleaned = part
                break
    return cleaned


def extract_school_header_from_lines(lines: List[str]) -> Dict[str, Any]:
    """Detects candidate school info (name, NPSN, address, email) from document top lines/paragraphs."""
    name: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    npsn: Optional[str] = None

    school_keywords = ("SEKOLAH DASAR", "SDN", "SD NEGERI", "SD SWASTA", "SMPN", "SMP NEGERI", "SMAN", "SMKN", "MADRASAH")
    for raw_line in lines[:50]:
        val = clean_cell_text(raw_line)
        if not val:
            continue
        val_upper = val.upper()
        if not name and any(kw in val_upper for kw in school_keywords):
            # Ignore administrative guidance lines mentioning generic acronyms like "(SDN/SMPN/...)"
            if "(SDN/" not in val_upper and "IDENTITAS SEKOLAH" not in val_upper:
                name = _clean_extracted_school_name(val)
        if not npsn:
            npsn_match = re.search(r"\bNPSN\s*[:\-–]?\s*(\d{8})\b", val, flags=re.IGNORECASE)
            if npsn_match:
                npsn = npsn_match.group(1)
        if not address and ("JL." in val_upper or "JALAN" in val_upper):
            address = val
        if not email and ("EMAIL" in val_upper or "@" in val):
            m = re.search(r"[\w.\-]+@[\w.\-]+\.\w+", val)
            if m:
                email = m.group(0)

    return {
        "name": name or "SEKOLAH DASAR NEGERI KEBON KOSONG 09",
        "detected": bool(name),
        "npsn": npsn,
        "address": address or "Jl. Kemayoran Gempol no.32",
        "email": email or "sdnkk05pg@gmail.com",
        "level": "SD",
    }


def extract_transaction_metadata_from_lines(lines: List[str]) -> Dict[str, Any]:
    """Extracts Kegiatan, Rincian Kegiatan, Kode Rekening, Tahun Anggaran, and Triwulan from text lines."""
    meta: Dict[str, Any] = {
        "kegiatan": "Pemeliharaan Sarana dan Prasarana Sekolah",
        "rincian_kegiatan": "Pembelian Bahan Kebersihan Sekolah",
        "kode_rekening": "Bahan-bahan lainnya",
        "tahun_anggaran": 2026,
        "triwulan": 2,
        "tahun_anggaran_detected": False,
        "triwulan_detected": False,
    }
    explicit_year: Optional[int] = None
    fallback_date_year: Optional[int] = None
    explicit_quarter: Optional[int] = None
    month_quarter: Optional[int] = None

    for raw_line in lines[:60]:
        line = clean_cell_text(raw_line)
        if not line:
            continue
        lower = line.lower()

        def _after_colon_or_space(keyword: str) -> Optional[str]:
            idx = lower.find(keyword)
            if idx < 0:
                return None
            rest = line[idx + len(keyword) :].strip()
            rest = re.sub(r"^[\s:\-–]+", "", rest).strip()
            return rest or None

        if "rincian kegiatan" in lower:
            val = _after_colon_or_space("rincian kegiatan")
            if val:
                meta["rincian_kegiatan"] = val[:200]
        elif "kegiatan" in lower:
            val = _after_colon_or_space("kegiatan")
            if val:
                meta["kegiatan"] = val[:200]
        if "kode rekening" in lower:
            val = _after_colon_or_space("kode rekening")
            if val:
                meta["kode_rekening"] = val[:150]

        if explicit_year is None and any(k in lower for k in ("tahun anggaran", "tahung anggaran", "t.a", "tahun")) and "nip" not in lower:
            m = re.search(r"(?<!\d)(20[1-3]\d)(?!\d)", line)
            if m:
                explicit_year = int(m.group(1))
        elif fallback_date_year is None and "nip" not in lower:
            # Date pattern e.g. '12 Agustus 2025' or '2025-08-12' or '12/08/2025'
            m_date = re.search(
                r"(?:\b\d{1,2}\s+(?:januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s+(20[1-3]\d)\b|\b(20[1-3]\d)-\d{2}-\d{2}\b|\b\d{2}/\d{2}/(20[1-3]\d)\b)",
                lower,
            )
            if m_date:
                yr_str = next((g for g in m_date.groups() if g), None)
                if yr_str:
                    fallback_date_year = int(yr_str)

        if explicit_quarter is None:
            q_explicit = extract_quarter_from_text(line, allow_month_fallback=False)
            if q_explicit is not None:
                explicit_quarter = q_explicit
        if month_quarter is None:
            q_month = extract_quarter_from_text(line, allow_month_fallback=True)
            if q_month is not None:
                month_quarter = q_month

    resolved_year = explicit_year or fallback_date_year
    if resolved_year is not None:
        meta["tahun_anggaran"] = resolved_year
        meta["tahun_anggaran_detected"] = True

    resolved_quarter = explicit_quarter or month_quarter
    if resolved_quarter is not None:
        meta["triwulan"] = resolved_quarter
        meta["triwulan_detected"] = True

    return meta


def grid_to_text_lines(grid: List[List[Any]], max_rows: int = 40) -> List[str]:
    lines: List[str] = []
    for row in grid[:max_rows]:
        parts = [clean_cell_text(c) for c in row if clean_cell_text(c)]
        if parts:
            lines.append(" | ".join(parts))
    return lines


def _score_header_row(row: List[Any]) -> int:
    tokens_matched = set()
    for cell in row:
        val = clean_cell_text(cell).lower()
        if not val:
            continue
        for token in TABLE_HEADER_TOKENS:
            if token in val:
                tokens_matched.add(token)
    return len(tokens_matched)


def extract_line_items_from_grid(
    grid: List[List[Any]],
    column_mapping: Optional[Dict[str, int]] = None,
    header_row_index: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], int, Dict[str, int]]:
    """Extracts line items, resolved 1-based header row index, and canonical column mapping
    from a generic 2D grid produced by DOCX, DOC, or PDF extractors.
    """
    if not grid:
        return [], 1, {}

    max_cols = max((len(r) for r in grid), default=0)
    if max_cols == 0:
        return [], 1, {}

    col_map: Dict[str, int] = {}
    explicit_mapping = bool(column_mapping)

    if column_mapping:
        for k, v in column_mapping.items():
            if v is None:
                continue
            try:
                col_idx = int(v)
            except (TypeError, ValueError):
                continue
            if col_idx < 1:
                continue
            k_norm = str(k).lower().replace("-", "_")
            if k_norm in ("line_no", "no", "nomor"):
                col_map["no"] = col_idx
            elif k_norm in ("description", "name", "nama", "nama_barang", "uraian"):
                col_map["name"] = col_idx
            elif k_norm in ("quantity", "volume", "vol", "qty", "kuantitas"):
                col_map["volume"] = col_idx
            elif k_norm in ("unit", "satuan"):
                col_map["unit"] = col_idx
            elif k_norm in ("specification", "spec", "spek", "spesifikasi"):
                col_map["spec"] = col_idx
            elif k_norm in ("hps_price", "hps_unit_price", "price", "harga_satuan", "harga_hps", "hps"):
                col_map["hps_price"] = col_idx
                col_map["price"] = col_idx
            elif k_norm in ("offer_price", "offer_unit_price", "harga_penawaran", "penawaran"):
                col_map["offer_price"] = col_idx
            elif k_norm in ("final_price", "final_unit_price", "harga_final", "harga_negosiasi", "negosiasi"):
                col_map["final_price"] = col_idx
            elif k_norm in ("total", "line_total", "total_price", "jumlah", "jumlah_total"):
                col_map["total"] = col_idx

    resolved_header: Optional[int] = (
        header_row_index if (header_row_index and 1 <= header_row_index <= len(grid)) else None
    )

    # Search for best header row in top 35 rows when not explicitly given
    if not resolved_header:
        best_score = 0
        best_row = 1
        for r_idx, row in enumerate(grid[:35], start=1):
            score = _score_header_row(row)
            if score >= 3:
                resolved_header = r_idx
                break
            if score > best_score:
                best_score = score
                best_row = r_idx
        if not resolved_header:
            resolved_header = best_row if best_score >= 2 else 1

    if not explicit_mapping and 1 <= resolved_header <= len(grid):
        header_cells = grid[resolved_header - 1]
        for c_idx, raw_cell in enumerate(header_cells, start=1):
            val = clean_cell_text(raw_cell).lower()
            if not val:
                continue
            if val in ("no", "nomor", "#", "no.", "no / urut") or val.startswith("no."):
                col_map.setdefault("no", c_idx)
            elif (
                "nama barang" in val
                or "uraian" in val
                or "deskripsi" in val
                or "nama item" in val
                or "jenis barang" in val
                or (
                    "nama" in val
                    and not any(k in val for k in ("sekolah", "perusahaan", "pt", "cv", "harga", "kepala", "bendahara", "petugas"))
                )
            ):
                col_map.setdefault("name", c_idx)
            elif (
                "volume" in val
                or "banyaknya" in val
                or "kuantitas" in val
                or val in ("vol", "qty", "kuantum", "jml")
                or ("jumlah" in val and not any(k in val for k in ("harga", "total", "biaya", "rp", "subtotal")))
            ):
                col_map.setdefault("volume", c_idx)
            elif ("satuan" in val and not any(k in val for k in ("harga", "biaya", "tarif"))) or val in ("sat", "sat.", "unit", "uom"):
                col_map.setdefault("unit", c_idx)
            elif "spesifikasi" in val or "spek" in val or "keterangan" in val or "ukuran" in val or "merk" in val:
                col_map.setdefault("spec", c_idx)
            elif "harga penawaran" in val or ("penawaran" in val and "harga" in val) or "harga rekanan" in val:
                col_map.setdefault("offer_price", c_idx)
            elif "harga negosiasi" in val or "harga final" in val or "harga kesepakatan" in val or ("negosiasi" in val and "harga" in val):
                col_map.setdefault("final_price", c_idx)
            elif (
                "harga satuan" in val
                or "harga hps" in val
                or "harga pagu" in val
                or "hps" in val
                or "harga perkiraan" in val
                or ("harga" in val and not any(k in val for k in ("total", "jumlah", "penawaran", "negosiasi", "final", "kesepakatan")))
            ):
                col_map.setdefault("hps_price", c_idx)
                col_map.setdefault("price", c_idx)
            elif "total" in val or "jumlah harga" in val or "subtotal" in val or (
                "jumlah" in val and any(k in val for k in ("harga", "rp", "total"))
            ):
                col_map.setdefault("total", c_idx)

    c_no = col_map.get("no")
    c_name = col_map.get("name") or (2 if max_cols >= 2 else 1)
    c_vol = col_map.get("volume")
    c_unit = col_map.get("unit")
    c_spec = col_map.get("spec")
    c_hps = col_map.get("hps_price") or col_map.get("price")
    c_offer = col_map.get("offer_price")
    c_final = col_map.get("final_price")
    c_total = col_map.get("total")

    canonical_mapping: Dict[str, int] = {}
    if c_no:
        canonical_mapping["line_no"] = c_no
    if c_name:
        canonical_mapping["description"] = c_name
    if c_spec:
        canonical_mapping["specification"] = c_spec
    if c_vol:
        canonical_mapping["quantity"] = c_vol
    if c_unit:
        canonical_mapping["unit"] = c_unit
    if c_hps:
        canonical_mapping["hps_price"] = c_hps
    if c_offer:
        canonical_mapping["offer_price"] = c_offer
    if c_final:
        canonical_mapping["final_price"] = c_final

    def _cell(row: List[Any], one_based_col: Optional[int]) -> Any:
        if not one_based_col or one_based_col < 1 or one_based_col > len(row):
            return None
        return row[one_based_col - 1]

    lines: List[Dict[str, Any]] = []
    consecutive_empty = 0
    line_num = 1

    for row in grid[resolved_header : min(len(grid), resolved_header + 200)]:
        cleaned_row = [clean_cell_text(c) for c in row]
        if not any(cleaned_row):
            consecutive_empty += 1
            if consecutive_empty >= 2 and lines:
                break
            continue
        consecutive_empty = 0

        first_cols_lower = " ".join(cleaned_row[:3]).lower()
        if any(tok == c.lower() or first_cols_lower.startswith(tok) for tok in TABLE_TERMINAL_TOKENS for c in cleaned_row[:2] if c):
            # Terminal summary row reached once we already have lines
            if lines:
                break
            continue

        name_raw = _cell(row, c_name)
        name_txt = clean_cell_text(name_raw)
        if not name_txt and not explicit_mapping:
            # Pick longest descriptive non-numeric cell in first 4 cols
            for candidate_val in row[:4]:
                cand = clean_cell_text(candidate_val)
                if len(cand) > 2 and not re.fullmatch(r"[\d.,\-]+", cand):
                    name_txt = cand
                    break

        if not name_txt or name_txt.lower() in ("jumlah", "total", "subtotal", "ppn", "pph", "grand total"):
            continue
        # Skip repeated table headers that occur on page breaks in multi-page PDF tables
        if _score_header_row(row) >= 3:
            continue

        vol_raw = _cell(row, c_vol)
        unit_raw = _cell(row, c_unit)
        spec_raw = _cell(row, c_spec)
        hps_raw = _cell(row, c_hps)
        offer_raw = _cell(row, c_offer)
        final_raw = _cell(row, c_final)
        total_raw = _cell(row, c_total)

        dec_vol = parse_decimal_value(vol_raw, default=Decimal("1")) or Decimal("1")
        dec_hps = parse_decimal_value(hps_raw, default=Decimal("0")) or Decimal("0")
        dec_offer = parse_decimal_value(offer_raw, default=dec_hps)
        if dec_offer is None:
            dec_offer = dec_hps
        dec_final = parse_decimal_value(final_raw, default=dec_offer)
        if dec_final is None:
            dec_final = dec_offer
        dec_total = parse_decimal_value(total_raw, default=Decimal("0")) or Decimal("0")

        # If hps/price is still 0 but total & quantity > 0, infer unit price cleanly
        if dec_hps == 0 and dec_final == 0 and dec_total > 0 and dec_vol > 0:
            inferred_unit = (dec_total / dec_vol).quantize(Decimal("0.01"))
            dec_hps = inferred_unit
            dec_offer = inferred_unit
            dec_final = inferred_unit
        if dec_total == 0:
            dec_total = dec_vol * dec_final

        unit_txt = clean_cell_text(unit_raw) or "buah"
        spec_txt = clean_cell_text(spec_raw)

        lines.append({
            "line_number": line_num,
            "original_description": name_txt,
            "confirmed_description": name_txt,
            "specification": spec_txt or None,
            "quantity": float(dec_vol),
            "unit": unit_txt,
            "hps_unit_price": float(dec_hps),
            "hps_price": float(dec_hps),
            "offer_unit_price": float(dec_offer),
            "final_unit_price": float(dec_final),
            "discount": 0.0,
            "line_total": float(dec_total),
            "condition": "BAIK",
            "raw_formula": None,
        })
        line_num += 1

    return lines, resolved_header, canonical_mapping


def scan_text_invariants(sections: List[ExtractedSection], document_context_lines: List[str]) -> List[Dict[str, Any]]:
    """Checks extracted non-Excel sections and context text for entity/date anomalies."""
    discrepancies: List[Dict[str, Any]] = []
    seen = set()

    def _inspect_text(section_label: str, coord: Optional[str], text: str) -> None:
        val_upper = text.upper()
        if "CV. MITRA KARYA GEMILANG" in val_upper or "MITRA KARYA GEMILANG" in val_upper:
            key = ("ENTITY_MISMATCH", "company_name", text[:60])
            if key not in seen:
                seen.add(key)
                discrepancies.append({
                    "sheet_name": section_label,
                    "cell_coordinate": coord,
                    "rule_category": "ENTITY_MISMATCH",
                    "severity": "BLOCK",
                    "field": "company_name",
                    "found_value": text[:120],
                    "expected_or_note": "Terdeteksi nama badan usaha warisan 'CV. MITRA KARYA GEMILANG'. Wajib diganti dengan CV. Pustaka Cemerlang Indonesia.",
                })
        if "KEBON KOSONG 05" in val_upper or "KEBON KOSONG 13" in val_upper or "KK13" in val_upper:
            key = ("ENTITY_MISMATCH", "school_name", text[:60])
            if key not in seen:
                seen.add(key)
                discrepancies.append({
                    "sheet_name": section_label,
                    "cell_coordinate": coord,
                    "rule_category": "ENTITY_MISMATCH",
                    "severity": "BLOCK",
                    "field": "school_name",
                    "found_value": text[:120],
                    "expected_or_note": f"Terdeteksi nama/nomor sekolah lain ('{text[:80]}'). Wajib dinormalisasi sesuai sekolah induk terkonfirmasi.",
                })
        if "KK13/2022" in val_upper or "/2022" in val_upper:
            key = ("STALE_NUMBER", "doc_number", text[:60])
            if key not in seen:
                seen.add(key)
                discrepancies.append({
                    "sheet_name": section_label,
                    "cell_coordinate": coord,
                    "rule_category": "STALE_NUMBER",
                    "severity": "BLOCK",
                    "field": "doc_number",
                    "found_value": text[:120],
                    "expected_or_note": "Nomor dokumen usang tahun 2022 terdeteksi. Wajib dialokasikan nomor resmi tahun anggaran berjalan.",
                })

    for line in document_context_lines[:100]:
        if line:
            _inspect_text("Konteks Dokumen", None, line)

    for sec in sections:
        for r_idx, row in enumerate(sec.grid[:80], start=1):
            for c_idx, cell in enumerate(row[:15], start=1):
                txt = clean_cell_text(cell)
                if txt:
                    _inspect_text(sec.name, f"R{r_idx}C{c_idx}", txt)

    return discrepancies


def build_unified_document_payload(
    *,
    source_format: str,
    sections: List[ExtractedSection],
    document_context_lines: List[str],
    column_mapping: Optional[Dict[str, int]] = None,
    section_name: Optional[str] = None,
    header_row_index: Optional[int] = None,
    extraction_stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Builds the unified candidate_payload dictionary from extracted sections & context lines."""
    if not sections:
        raise ValueError("Tidak ada tabel atau baris teks terstruktur yang dapat diekstrak dari dokumen.")

    section_names = [s.name for s in sections]
    # Pick target section: explicit match -> best scoring table -> first section
    target: Optional[ExtractedSection] = None
    if section_name:
        for s in sections:
            if s.name == section_name:
                target = s
                break
    if target is None:
        # Prefer first section that looks like an item table (>= 3 header tokens or most rows)
        best_section = sections[0]
        best_rank = (-1, 0)
        for s in sections:
            top_score = max((_score_header_row(r) for r in s.grid[:15]), default=0)
            rank = (1 if top_score >= 3 else 0, len(s.grid))
            if rank > best_rank:
                best_rank = rank
                best_section = s
        target = best_section

    combined_context_lines = list(document_context_lines)
    if target.context_snippets:
        combined_context_lines = target.context_snippets + [
            l for l in combined_context_lines if l not in target.context_snippets
        ]
    combined_context_lines.extend(grid_to_text_lines(target.grid, max_rows=20))

    school_candidate = extract_school_header_from_lines(combined_context_lines)
    transaction_metadata = extract_transaction_metadata_from_lines(combined_context_lines)

    candidate_lines, resolved_header_row, detected_mapping = extract_line_items_from_grid(
        target.grid,
        column_mapping=column_mapping,
        header_row_index=header_row_index,
    )

    raw_preview_rows = [
        [serialize_grid_cell(c) for c in row[:15]]
        for row in target.grid[:30]
    ]

    sections_grids = {
        s.name: [[serialize_grid_cell(c) for c in row[:15]] for row in s.grid[:150]]
        for s in sections
    }

    discrepancies = scan_text_invariants(sections, document_context_lines)

    stats = dict(extraction_stats or {})
    stats.update({
        "source_format": source_format,
        "sections_count": len(sections),
        "active_section": target.name,
        "preview_rows_count": len(raw_preview_rows),
        "candidate_lines_count": len(candidate_lines),
        "context_lines_count": len(document_context_lines),
    })

    events_candidate = build_default_events_for_period(
        fiscal_year=int(transaction_metadata.get("tahun_anggaran") or 2026),
        quarter=int(transaction_metadata.get("triwulan") or 2),
    )

    return {
        "source_format": source_format,
        "school_candidate": school_candidate,
        "transaction_metadata": transaction_metadata,
        "candidate_lines": candidate_lines,
        "events_candidate": events_candidate,
        "sheet_names": section_names,
        "active_sheet": target.name,
        "header_row_index": resolved_header_row,
        "detected_mapping": detected_mapping,
        "raw_preview_rows": raw_preview_rows,
        "detected_discrepancies": discrepancies,
        "can_proceed_to_confirm": len(candidate_lines) > 0,
        "document_context": {
            "source_format": source_format,
            "snippets": [clean_cell_text(l) for l in document_context_lines[:35] if clean_cell_text(l)],
            "section_contexts": {s.name: s.context_snippets[:10] for s in sections if s.context_snippets},
        },
        "sections_grids": sections_grids,
        "extraction_stats": stats,
    }
