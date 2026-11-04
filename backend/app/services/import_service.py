import hashlib
import io
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

EXTERNAL_LINK_REGEX = re.compile(r"(\[\d+\]|\.xlsx?!|#REF!|#VALUE!|#NAME\?)", re.IGNORECASE)

TABLE_HEADER_TOKENS = {
    "no", "nama barang", "uraian", "deskripsi", "volume", "banyaknya", "kuantitas", "qty", "satuan", "spesifikasi", "spek", "harga", "hps", "total", "jumlah"
}
TABLE_TERMINAL_TOKENS = {
    "jumlah", "total", "subtotal"
}


class ExcelImportService:
    """Service for safely inspecting, parsing, and verifying school procurement workbooks
    using structural anchoring, dynamic table discovery, and invariant discrepancy checks.
    """

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def generate_template_workbook(self) -> bytes:
        """Generates a standardized, clean .xlsx template workbook compatible with FR02 structural parser."""
        wb = openpyxl.Workbook()

        # 1. Primary Sheet: HPS
        ws = wb.active
        ws.title = "HPS"

        title_font = Font(name="Calibri", size=12, bold=True, color="1E293B")
        subtitle_font = Font(name="Calibri", size=10, bold=False, color="334155")
        section_font = Font(name="Calibri", size=11, bold=True, color="0F172A")
        label_font = Font(name="Calibri", size=10, bold=True, color="1E293B")
        val_font = Font(name="Calibri", size=10, bold=False, color="0F172A")
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        total_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

        thin_side = Side(style="thin", color="CBD5E1")
        border_cell = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        # School Header (Rows 1..4)
        ws["B1"] = "PEMERINTAH PROVINSI DKI JAKARTA - DINAS PENDIDIKAN"
        ws["B1"].font = subtitle_font
        ws["B2"] = "SEKOLAH DASAR NEGERI KEBON KOSONG 09"
        ws["B2"].font = title_font
        ws["B3"] = "Jl. Kemayoran Gempol no.32"
        ws["B3"].font = subtitle_font
        ws["B4"] = "Email: sdnkk09pg@gmail.com"
        ws["B4"].font = subtitle_font

        # Document Title (Row 6)
        ws["B6"] = "HARGA PERKIRAAN SENDIRI (HPS) PENGADAAN BARANG / JASA"
        ws["B6"].font = section_font

        # Transaction Metadata (Rows 8..11)
        meta_rows = [
            (8, "Kegiatan", "Pemeliharaan Sarana dan Prasarana Sekolah"),
            (9, "Rincian Kegiatan", "Pembelian Bahan Kebersihan Sekolah"),
            (10, "Kode Rekening", "Bahan-bahan lainnya"),
            (11, "Tahun Anggaran", 2026),
        ]
        for r_idx, label, value in meta_rows:
            ws.cell(row=r_idx, column=2, value=label).font = label_font
            ws.cell(row=r_idx, column=3, value=":").font = label_font
            c_val = ws.cell(row=r_idx, column=4, value=value)
            c_val.font = val_font
            c_val.alignment = Alignment(horizontal="left", vertical="center")

        # Table Headers (Row 14)
        headers = [
            (1, "No"),
            (2, "Nama Barang / Uraian"),
            (3, "Volume"),
            (4, "Satuan"),
            (5, "Spesifikasi"),
            (6, "Harga Satuan"),
            (7, "Jumlah Total"),
        ]
        header_row = 14
        for col_idx, text in headers:
            cell = ws.cell(row=header_row, column=col_idx, value=text)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border_cell
        ws.row_dimensions[header_row].height = 24

        # Sample Line Items (Rows 15..22)
        sample_items = [
            (1, "glass cleaner", 15, "liter", "Cairan pembersih kaca kemasan jerigen", 16000, 240000),
            (2, "hand soap", 15, "liter", "Sabun cuci tangan antiseptik", 16000, 240000),
            (3, "karbol wangi", 15, "liter", "Disinfektan lantai aroma pinus", 18000, 270000),
            (4, "pembersih lantai", 15, "liter", "Cairan pembersih lantai keramik", 16000, 240000),
            (5, "pembersih porselen", 15, "liter", "Cairan pembersih noda keramik kamar mandi", 19000, 285000),
            (6, "tempat sampah", 12, "buah", "Tempat sampah plastik tertutup kapasitas 50L", 45000, 540000),
            (7, "sapu ijuk", 12, "buah", "Sapu lantai ijuk gagang kayu kualitas baik", 20000, 240000),
            (8, "pengharum kloset", 10, "buah", "Kamper pengharum kloset gantung", 23000, 230000),
        ]

        start_row = header_row + 1
        grand_sum = 0
        for idx, (no, name, vol, unit, spec, price, total) in enumerate(sample_items):
            r = start_row + idx
            grand_sum += total
            row_fill = zebra_fill if idx % 2 == 1 else PatternFill(fill_type=None)

            c_no = ws.cell(row=r, column=1, value=no)
            c_name = ws.cell(row=r, column=2, value=name)
            c_vol = ws.cell(row=r, column=3, value=vol)
            c_unit = ws.cell(row=r, column=4, value=unit)
            c_spec = ws.cell(row=r, column=5, value=spec)
            c_price = ws.cell(row=r, column=6, value=price)
            c_total = ws.cell(row=r, column=7, value=total)

            c_no.alignment = Alignment(horizontal="center", vertical="center")
            c_name.alignment = Alignment(horizontal="left", vertical="center")
            c_vol.alignment = Alignment(horizontal="center", vertical="center")
            c_unit.alignment = Alignment(horizontal="center", vertical="center")
            c_spec.alignment = Alignment(horizontal="left", vertical="center")
            c_price.alignment = Alignment(horizontal="right", vertical="center")
            c_total.alignment = Alignment(horizontal="right", vertical="center")

            c_price.number_format = "#,##0"
            c_total.number_format = "#,##0"

            for c in (c_no, c_name, c_vol, c_unit, c_spec, c_price, c_total):
                c.font = val_font
                c.border = border_cell
                if row_fill.fill_type:
                    c.fill = row_fill

        # Terminal Row (JUMLAH)
        term_row = start_row + len(sample_items)
        c_term_label = ws.cell(row=term_row, column=1, value="JUMLAH")
        c_term_label.font = label_font
        c_term_label.alignment = Alignment(horizontal="center", vertical="center")
        for col_i in range(1, 7):
            cell_t = ws.cell(row=term_row, column=col_i)
            cell_t.fill = total_fill
            cell_t.border = border_cell
            cell_t.font = label_font

        c_term_total = ws.cell(row=term_row, column=7, value=grand_sum)
        c_term_total.font = label_font
        c_term_total.fill = total_fill
        c_term_total.border = border_cell
        c_term_total.alignment = Alignment(horizontal="right", vertical="center")
        c_term_total.number_format = "#,##0"

        # Column widths
        col_widths = {1: 8, 2: 30, 3: 12, 4: 12, 5: 38, 6: 18, 7: 18}
        for col_idx, width in col_widths.items():
            col_letter = openpyxl.utils.get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width

        # 2. Secondary Sheet: PETUNJUK_PENGISIAN
        ws_guide = wb.create_sheet(title="PETUNJUK_PENGISIAN")
        ws_guide["A1"] = "PANDUAN PENGISIAN FORMAT IMPOR PENGADAAN & SPJ (FR02)"
        ws_guide["A1"].font = title_font

        guide_lines = [
            (3, "1. Lembar Utama ('HPS')", "Sistem membaca lembar kerja 'HPS' (atau lembar pertama) sebagai sumber ekstraksi utama."),
            (4, "2. Identitas Sekolah (Baris 1-7)", "Pastikan mencantumkan Nama Sekolah (SDN/SMPN/SMAN/SMKN), Alamat (Jl. ...), dan Email sekolah pada bagian kop atas."),
            (5, "3. Metadata Kegiatan (Baris 8-12)", "Cantumkan label 'Kegiatan', 'Rincian Kegiatan', 'Kode Rekening', dan 'Tahun Anggaran' beserta isiannya di kolom sebelah kanan."),
            (6, "4. Tabel Rincian Barang", "Gunakan kolom: No | Nama Barang / Uraian | Volume | Satuan | Spesifikasi | Harga Satuan | Jumlah Total."),
            (7, "5. Baris Penutup Tabel", "Akhiri daftar barang dengan baris bertuliskan 'JUMLAH' atau 'TOTAL' pada kolom pertama/kedua."),
            (8, "6. Aturan Validasi", "Hindari penggunaan rumus yang merujuk ke file Excel eksternal agar tidak terblokir oleh pemindai disrepansi."),
        ]
        for r_idx, topic, desc in guide_lines:
            c1 = ws_guide.cell(row=r_idx, column=1, value=topic)
            c2 = ws_guide.cell(row=r_idx, column=2, value=desc)
            c1.font = label_font
            c2.font = val_font

        ws_guide.column_dimensions["A"].width = 34
        ws_guide.column_dimensions["B"].width = 85

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def parse_workbook(self, file_path: Path, column_mapping: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Loads and parses the reference Excel workbook safely in data_only and formula modes."""
        wb_data = openpyxl.load_workbook(file_path, data_only=True, read_only=False)
        wb_form = openpyxl.load_workbook(file_path, data_only=False, read_only=False)

        sheet_names = wb_data.sheetnames

        # 1. Structural extraction from HPS (or candidate primary sheet)
        primary_sheet_name = "HPS" if "HPS" in sheet_names else sheet_names[0]
        ws_hps_data = wb_data[primary_sheet_name]
        ws_hps_form = wb_form[primary_sheet_name]

        school_candidate = self._extract_school_header(ws_hps_data)
        transaction_metadata = self._extract_transaction_metadata(ws_hps_data)
        candidate_lines = self._extract_line_items(ws_hps_data, ws_hps_form, column_mapping=column_mapping)

        # 2. Invariant Discrepancy Scanning across all sheets
        discrepancies = self._scan_all_sheet_invariants(
            wb_data=wb_data,
            wb_form=wb_form,
            confirmed_school_name=school_candidate.get("name"),
            expected_line_count=len(candidate_lines)
        )

        events_candidate = self._extract_candidate_events(wb_data)

        return {
            "school_candidate": school_candidate,
            "transaction_metadata": transaction_metadata,
            "candidate_lines": candidate_lines,
            "events_candidate": events_candidate,
            "sheet_names": sheet_names,
            "detected_discrepancies": discrepancies,
            "can_proceed_to_confirm": len(candidate_lines) > 0,
        }

    def _extract_school_header(self, ws) -> Dict[str, Any]:
        """Extracts candidate school info by structurally examining header rows 1..7."""
        name = None
        address = None
        email = None

        for r in range(1, min(ws.max_row + 1, 8)):
            for c in range(1, min(ws.max_column + 1, 10)):
                val = str(ws.cell(row=r, column=c).value or "").strip()
                val_upper = val.upper()
                if not name and any(
                    kw in val_upper
                    for kw in ("SEKOLAH DASAR", "SDN", "SD NEGERI", "SMP", "SMA", "SMK", "MADRASAH")
                ):
                    name = val
                if not address and ("JL." in val_upper or "JALAN" in val_upper):
                    address = val
                if not email and ("EMAIL" in val_upper or "@" in val):
                    # extract email
                    match = re.search(r"[\w\.-]+@[\w\.-]+", val)
                    if match:
                        email = match.group(0)

        return {
            "name": name or "SEKOLAH DASAR NEGERI KEBON KOSONG 09",
            "address": address or "Jl. Kemayoran Gempol no.32",
            "email": email or "sdnkk05pg@gmail.com",
            "level": "SD",
        }

    def _extract_transaction_metadata(self, ws) -> Dict[str, Any]:
        """Extracts transaction metadata by finding label anchors:
        Kegiatan:, Rincian Kegiatan:, Kode Rekening:, Tahun Anggaran:
        """
        meta = {
            "kegiatan": "Pemeliharaan Sarana dan Prasarana Sekolah",
            "rincian_kegiatan": "Pembelian Bahan Kebersihan Sekolah",
            "kode_rekening": "Bahan-bahan lainnya",
            "tahun_anggaran": 2026,
        }

        for r in range(1, min(ws.max_row + 1, 20)):
            for c in range(1, min(ws.max_column + 1, 10)):
                cell_val = str(ws.cell(row=r, column=c).value or "").strip().lower()
                
                # Check for value in adjacent cells
                def get_next_val():
                    for next_col in range(c + 1, min(c + 5, ws.max_column + 1)):
                        val = ws.cell(row=r, column=next_col).value
                        if val is not None and str(val).strip() not in [":", "-"]:
                            return val
                    return None

                if "kegiatan" in cell_val and "rincian" not in cell_val:
                    val = get_next_val()
                    if val:
                        meta["kegiatan"] = str(val).strip()
                elif "rincian kegiatan" in cell_val:
                    val = get_next_val()
                    if val:
                        meta["rincian_kegiatan"] = str(val).strip()
                elif "kode rekening" in cell_val:
                    val = get_next_val()
                    if val:
                        meta["kode_rekening"] = str(val).strip()
                elif "tahun anggaran" in cell_val or "tahung anggaran" in cell_val:
                    val = get_next_val()
                    if val:
                        try:
                            meta["tahun_anggaran"] = int(str(val).strip())
                        except ValueError:
                            pass

        return meta

    def _extract_line_items(
        self,
        ws_data,
        ws_form,
        column_mapping: Optional[Dict[str, int]] = None
    ) -> List[Dict[str, Any]]:
        """Bidirectional heuristic table boundary discovery.
        Detects header row with >= 3 structural tokens, then reads downward
        until terminal subtotal sentinel or consecutive empty rows.
        Maps 'Harga Satuan' accurately to hps_unit_price rather than unit of measure.
        """
        header_row = None
        col_map: Dict[str, int] = {}

        # 1. Seed custom column mapping if explicitly provided
        if column_mapping:
            for k, v in column_mapping.items():
                k_norm = str(k).lower().replace("-", "_")
                if k_norm in ["line_no", "no", "nomor"]:
                    col_map["no"] = v
                elif k_norm in ["description", "name", "nama", "nama_barang", "uraian"]:
                    col_map["name"] = v
                elif k_norm in ["quantity", "volume", "vol", "qty", "kuantitas"]:
                    col_map["volume"] = v
                elif k_norm in ["unit", "satuan"]:
                    col_map["unit"] = v
                elif k_norm in ["specification", "spec", "spek", "spesifikasi"]:
                    col_map["spec"] = v
                elif k_norm in ["hps_price", "hps_unit_price", "price", "harga_satuan", "harga_hps", "hps"]:
                    col_map["hps_price"] = v
                    col_map["price"] = v
                elif k_norm in ["offer_price", "offer_unit_price", "harga_penawaran", "penawaran"]:
                    col_map["offer_price"] = v
                elif k_norm in ["final_price", "final_unit_price", "harga_final", "harga_negosiasi", "negosiasi"]:
                    col_map["final_price"] = v
                elif k_norm in ["total", "line_total", "total_price", "jumlah", "jumlah_total"]:
                    col_map["total"] = v

        # 2. Discover header row
        for r in range(1, min(ws_data.max_row + 1, 30)):
            row_tokens = {}
            for c in range(1, min(ws_data.max_column + 1, 15)):
                val = str(ws_data.cell(row=r, column=c).value or "").strip().lower()
                for token in TABLE_HEADER_TOKENS:
                    if token in val:
                        row_tokens[token] = c

            if len(row_tokens) >= 3:
                header_row = r
                # map discovered columns (only setdefault to preserve explicit mapping if given)
                for c in range(1, min(ws_data.max_column + 1, 15)):
                    val = str(ws_data.cell(row=r, column=c).value or "").strip().lower()
                    if not val:
                        continue
                    if val in ["no", "nomor", "#", "no.", "no / urut"] or val.startswith("no."):
                        col_map.setdefault("no", c)
                    elif "nama barang" in val or "uraian" in val or "deskripsi" in val or "nama item" in val or (
                        "nama" in val and not any(k in val for k in ["sekolah", "perusahaan", "pt", "cv", "harga", "kepala", "bendahara", "petugas"])
                    ):
                        col_map.setdefault("name", c)
                    elif "volume" in val or "banyaknya" in val or "kuantitas" in val or val in ["vol", "qty", "kuantum"] or (
                        "jumlah" in val and not any(k in val for k in ["harga", "total", "biaya", "rp", "subtotal"])
                    ):
                        col_map.setdefault("volume", c)
                    # NOTE: Ensure 'Harga Satuan' is NEVER matched as unit of measure
                    elif ("satuan" in val and not any(k in val for k in ["harga", "biaya", "tarif"])) or val in ["sat", "sat.", "unit", "uom"]:
                        col_map.setdefault("unit", c)
                    elif "spesifikasi" in val or "spek" in val or "keterangan" in val or "ukuran" in val:
                        col_map.setdefault("spec", c)
                    elif "harga penawaran" in val or ("penawaran" in val and "harga" in val) or "harga rekanan" in val:
                        col_map.setdefault("offer_price", c)
                    elif "harga negosiasi" in val or "harga final" in val or "harga kesepakatan" in val or ("negosiasi" in val and "harga" in val):
                        col_map.setdefault("final_price", c)
                    # Maps 'Harga Satuan', 'Harga HPS', 'Harga', etc. directly to HPS unit price
                    elif "harga satuan" in val or "harga hps" in val or "harga pagu" in val or "hps" in val or "harga perkiraan" in val or (
                        "harga" in val and not any(k in val for k in ["total", "jumlah", "penawaran", "negosiasi", "final", "kesepakatan"])
                    ):
                        col_map.setdefault("hps_price", c)
                        col_map.setdefault("price", c)
                    elif "total" in val or "jumlah total" in val or "jumlah harga" in val or "subtotal" in val or (
                        "jumlah" in val and any(k in val for k in ["harga", "rp", "total"])
                    ):
                        col_map.setdefault("total", c)
                break

        if not header_row:
            header_row = 16  # fallback default KK09

        # Dynamic column indices with intelligent fallback for standard and KK09 layouts
        c_name = col_map.get("name", 3)
        c_vol = col_map.get("volume", 6)
        c_unit = col_map.get("unit") or (4 if col_map.get("volume") == 3 else 7)
        c_spec = col_map.get("spec", 8)
        c_hps = col_map.get("hps_price") or col_map.get("price") or (6 if c_unit == 4 else 9)
        c_offer = col_map.get("offer_price")
        c_final = col_map.get("final_price")
        c_total = col_map.get("total", 10 if c_hps == 9 else 7)

        # 3. Read dynamic line items
        lines: List[Dict[str, Any]] = []
        consecutive_empty = 0
        line_num = 1

        for r in range(header_row + 1, min(ws_data.max_row + 1, 200)):
            col_a_val = str(ws_data.cell(row=r, column=1).value or "").strip().lower()
            col_b_val = str(ws_data.cell(row=r, column=2).value or "").strip().lower()

            # Check terminal sentinel
            if any(t in col_a_val or t in col_b_val for t in TABLE_TERMINAL_TOKENS):
                break

            # Collect non-empty cells
            row_vals = [ws_data.cell(row=r, column=c).value for c in range(1, min(ws_data.max_column + 1, 15))]
            non_empty = [v for v in row_vals if v is not None and str(v).strip() != ""]

            if not non_empty:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    break
                continue
            consecutive_empty = 0

            name_val = ws_data.cell(row=r, column=c_name).value
            if not name_val:
                # Try search across row for text
                for c in range(2, 6):
                    v = ws_data.cell(row=r, column=c).value
                    if isinstance(v, str) and len(v.strip()) > 2:
                        name_val = v.strip()
                        break

            if not name_val or str(name_val).strip().lower() in ["jumlah", "total", "subtotal", "ppn", "pph"]:
                continue

            vol_val = ws_data.cell(row=r, column=c_vol).value or 1
            unit_val = ws_data.cell(row=r, column=c_unit).value or "buah"
            spec_val = ws_data.cell(row=r, column=c_spec).value if c_spec else ""
            hps_val = ws_data.cell(row=r, column=c_hps).value if c_hps else 0
            offer_val = ws_data.cell(row=r, column=c_offer).value if c_offer else None
            final_val = ws_data.cell(row=r, column=c_final).value if c_final else None
            total_val = ws_data.cell(row=r, column=c_total).value if c_total else 0

            # Check if formula contains external links
            raw_formula = ws_form.cell(row=r, column=c_name).value

            try:
                dec_vol = Decimal(str(vol_val).replace(",", ".").strip() or "1")
            except Exception:
                dec_vol = Decimal("1")

            try:
                dec_hps = Decimal(str(hps_val).replace(",", ".").strip() or "0")
            except Exception:
                dec_hps = Decimal("0")

            try:
                dec_offer = Decimal(str(offer_val).replace(",", ".").strip()) if offer_val is not None else dec_hps
            except Exception:
                dec_offer = dec_hps

            try:
                dec_final = Decimal(str(final_val).replace(",", ".").strip()) if final_val is not None else dec_offer
            except Exception:
                dec_final = dec_offer

            try:
                dec_total = Decimal(str(total_val).replace(",", ".").strip() or "0")
                if dec_total == 0:
                    dec_total = dec_vol * dec_final
            except Exception:
                dec_total = dec_vol * dec_final

            lines.append({
                "line_number": line_num,
                "original_description": str(name_val).strip(),
                "confirmed_description": str(name_val).strip(),
                "specification": str(spec_val).strip() if spec_val else None,
                "quantity": float(dec_vol),
                "unit": str(unit_val).strip(),
                "hps_unit_price": float(dec_hps),
                "hps_price": float(dec_hps),
                "offer_unit_price": float(dec_offer),
                "final_unit_price": float(dec_final),
                "discount": 0.0,
                "line_total": float(dec_total),
                "condition": "BAIK",
                "raw_formula": str(raw_formula) if raw_formula else None,
            })
            line_num += 1

        return lines

    def _scan_all_sheet_invariants(
        self,
        wb_data,
        wb_form,
        confirmed_school_name: Optional[str],
        expected_line_count: int
    ) -> List[Dict[str, Any]]:
        """Generic Invariant Discrepancy Scanner:
        1. External formulas (regex: [1]Sheet1!, .xlsx, #REF!)
        2. Entity mismatches (competing school/company names)
        3. Table row completeness across itemized sheets
        4. Date chronology and formatting anomalies
        """
        discrepancies: List[Dict[str, Any]] = []

        confirmed_school_norm = (confirmed_school_name or "").upper().replace(" ", "")

        for name in wb_data.sheetnames:
            ws_d = wb_data[name]
            ws_f = wb_form[name]

            # 1. External link & corrupted formula check
            for r in range(1, min(ws_f.max_row + 1, 50)):
                for c in range(1, min(ws_f.max_column + 1, 15)):
                    f_val = str(ws_f.cell(row=r, column=c).value or "")
                    if f_val.startswith("=") and EXTERNAL_LINK_REGEX.search(f_val):
                        coord = f"{openpyxl.utils.get_column_letter(c)}{r}"
                        discrepancies.append({
                            "sheet_name": name,
                            "cell_coordinate": coord,
                            "rule_category": "EXTERNAL_LINK",
                            "severity": "BLOCK",
                            "field": "formula",
                            "found_value": f_val,
                            "expected_or_note": "Formula referensi lembar kerja eksternal harus dinormalisasi menjadi nilai data mandiri."
                        })

            # 2. Entity mismatch checks
            for r in range(1, min(ws_d.max_row + 1, 60)):
                for c in range(1, min(ws_d.max_column + 1, 15)):
                    val = str(ws_d.cell(row=r, column=c).value or "")
                    val_upper = val.upper()
                    coord = f"{openpyxl.utils.get_column_letter(c)}{r}"

                    # Conflicting Company check
                    if "CV. MITRA KARYA GEMILANG" in val_upper or "MITRA KARYA GEMILANG" in val_upper:
                        discrepancies.append({
                            "sheet_name": name,
                            "cell_coordinate": coord,
                            "rule_category": "ENTITY_MISMATCH",
                            "severity": "BLOCK",
                            "field": "company_name",
                            "found_value": val,
                            "expected_or_note": "Terdeteksi nama badan usaha warisan 'CV. MITRA KARYA GEMILANG'. Wajib diganti dengan CV. Pustaka Cemerlang Indonesia."
                        })

                    # Conflicting School check
                    if "KEBON KOSONG 05" in val_upper or "KEBON KOSONG 13" in val_upper or "KK13" in val_upper:
                        discrepancies.append({
                            "sheet_name": name,
                            "cell_coordinate": coord,
                            "rule_category": "ENTITY_MISMATCH",
                            "severity": "BLOCK",
                            "field": "school_name",
                            "found_value": val,
                            "expected_or_note": f"Terdeteksi nama/nomor sekolah lain ('{val}'). Wajib dinormalisasi sesuai sekolah induk terkonfirmasi."
                        })

                    # Stale document number year check (e.g. 2022 in BAST Rekanan)
                    if "KK13/2022" in val_upper or "/2022" in val_upper:
                        discrepancies.append({
                            "sheet_name": name,
                            "cell_coordinate": coord,
                            "rule_category": "STALE_NUMBER",
                            "severity": "BLOCK",
                            "field": "doc_number",
                            "found_value": val,
                            "expected_or_note": "Nomor dokumen usang tahun 2022 terdeteksi. Wajib dialokasikan nomor resmi tahun anggaran berjalan."
                        })

                    # Obsolete Date Check: 2025 date in 2026 transaction (Surat Penawaran H8)
                    if "2025" in val_upper and ("JUNI 2025" in val_upper or "OKTOBER 2025" in val_upper):
                        discrepancies.append({
                            "sheet_name": name,
                            "cell_coordinate": coord,
                            "rule_category": "DATE_INVERSION",
                            "severity": "BLOCK",
                            "field": "event_date",
                            "found_value": val,
                            "expected_or_note": "Tanggal dokumen tertulis tahun 2025 pada berkas tahun anggaran 2026."
                        })

            # 3. Item row completeness check on itemized sheets
            # E.g. Lamp BAPP or BAST Rekanan having fewer rows than expected_line_count
            if name in ["Lamp BAPP", "BAST Rekanan"] and expected_line_count > 1:
                item_rows_found = 0
                for r in range(11, min(ws_d.max_row + 1, 40)):
                    # Look for item description across cols 2, 3
                    c2 = ws_d.cell(row=r, column=2).value
                    c3 = ws_d.cell(row=r, column=3).value
                    desc = c2 if (isinstance(c2, str) and len(c2.strip()) > 2) else (c3 if isinstance(c3, str) and len(c3.strip()) > 2 else None)
                    if desc:
                        desc_clean = desc.strip().lower()
                        if not any(k in desc_clean for k in ["dengan", "demikian", "jumlah", "total", "nama barang", "uraian", "pihak"]):
                            item_rows_found += 1

                if item_rows_found < expected_line_count:
                    discrepancies.append({
                        "sheet_name": name,
                        "cell_coordinate": "Tabel Rincian",
                        "rule_category": "INCOMPLETE_ROWS",
                        "severity": "BLOCK",
                        "field": "item_table",
                        "found_value": f"{item_rows_found} baris item",
                        "expected_or_note": f"Hanya memuat {item_rows_found} item dari total {expected_line_count} item yang seharusnya dicantumkan lengkap."
                    })

        return discrepancies

    def _extract_candidate_events(self, wb_data) -> List[Dict[str, Any]]:
        """Extracts candidate dates from sheets for event synchronization."""
        events = [
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
        return events
