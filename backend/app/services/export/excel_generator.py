import io
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
import xlsxwriter

from app.services.export.date_helpers import (
    format_date_id,
    format_day_date_id,
    format_formal_narrative_date,
    format_idr,
)
from app.core.terbilang import terbilang


def to_excel_num(val: Union[Decimal, float, int, str, None]) -> float:
    """Converts a Decimal or numeric value to float safely for XlsxWriter."""
    if val is None:
        return 0.0
    try:
        return float(Decimal(str(val)))
    except Exception:
        return 0.0


class ExcelPackageGenerator:
    """Generates a link-free, formula-safe, multi-sheet workbook containing all 13
    official procurement and SPJ document sheets (D01-D13) using XlsxWriter.
    """

    def __init__(self, revision_data: Dict[str, Any], is_draft: bool = False):
        self.rev = revision_data
        self.is_draft = is_draft
        self.school = revision_data.get("school_snapshot") or revision_data.get("school") or {}
        self.company = revision_data.get("company_snapshot") or revision_data.get("company") or {}
        self.taxes = revision_data.get("tax_policy_snapshot") or []
        
        raw_officials = revision_data.get("officials_snapshot") or revision_data.get("officials") or {}
        if isinstance(raw_officials, dict):
            self.officials = raw_officials
        else:
            self.officials = {o.get("role"): o for o in raw_officials if isinstance(o, dict)}

        self.lines = revision_data.get("lines") or []

        raw_events = revision_data.get("events") or {}
        if isinstance(raw_events, dict):
            self.events = raw_events
        else:
            self.events = {e.get("event_code"): e for e in raw_events if isinstance(e, dict)}

        raw_numbers = revision_data.get("numbers") or {}
        if isinstance(raw_numbers, dict):
            self.numbers = raw_numbers
        else:
            self.numbers = {n.get("doc_code"): n for n in raw_numbers if isinstance(n, dict)}

        self.subtotal = Decimal(str(revision_data.get("subtotal") or 0))
        self.tax_total = Decimal(str(revision_data.get("tax_total") or 0))
        self.grand_total = Decimal(str(revision_data.get("grand_total") or 0))

    def generate_workbook(self, output_path: Optional[Path] = None) -> Union[Path, bytes]:
        """Renders all 13 reference sheets and saves to disk or returns bytes buffer."""
        if output_path:
            wb = xlsxwriter.Workbook(str(output_path), {'constant_memory': False})
        else:
            buffer = io.BytesIO()
            wb = xlsxwriter.Workbook(buffer, {'in_memory': True})

        formats = self._init_formats(wb)

        # Render 13 sheets in exact reference order
        self._render_d01_hps(wb, formats)
        self._render_d02_spp(wb, formats)
        self._render_d03_penawaran(wb, formats)
        self._render_d04_negosiasi(wb, formats)
        self._render_d05_pesanan(wb, formats)
        self._render_d06_faktur(wb, formats)
        self._render_d07_kwitansi(wb, formats)
        self._render_d08_surat_jalan(wb, formats)
        self._render_d09_bapb(wb, formats)
        self._render_d10_bast(wb, formats)
        self._render_d11_bapp(wb, formats)
        self._render_d12_lamp_bapp(wb, formats)
        self._render_d13_bast_rekanan(wb, formats)

        wb.close()

        if output_path:
            return output_path
        else:
            buffer.seek(0)
            return buffer.getvalue()

    def _init_formats(self, wb: xlsxwriter.Workbook) -> Dict[str, Any]:
        """Initializes reusable XlsxWriter format styles."""
        return {
            "title_gov": wb.add_format({'font_name': 'Arial', 'font_size': 11, 'bold': True, 'align': 'center'}),
            "title_dept": wb.add_format({'font_name': 'Arial', 'font_size': 11, 'bold': True, 'align': 'center'}),
            "title_school": wb.add_format({'font_name': 'Arial', 'font_size': 12, 'bold': True, 'align': 'center'}),
            "title_address": wb.add_format({'font_name': 'Arial', 'font_size': 9, 'align': 'center'}),
            "doc_title": wb.add_format({'font_name': 'Arial', 'font_size': 12, 'bold': True, 'align': 'center', 'underline': True}),
            "meta_key": wb.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True}),
            "meta_val": wb.add_format({'font_name': 'Arial', 'font_size': 10}),
            "tbl_hdr": wb.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#E8EEF5'}),
            "tbl_cell": wb.add_format({'font_name': 'Arial', 'font_size': 10, 'border': 1, 'valign': 'vcenter'}),
            "tbl_cell_center": wb.add_format({'font_name': 'Arial', 'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 1}),
            "tbl_cell_num": wb.add_format({'font_name': 'Arial', 'font_size': 10, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'num_format': '#,##0'}),
            "tbl_total_lbl": wb.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'align': 'right', 'border': 1, 'valign': 'vcenter'}),
            "tbl_total_val": wb.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'align': 'right', 'border': 1, 'valign': 'vcenter', 'num_format': '#,##0'}),
            "sign_role": wb.add_format({'font_name': 'Arial', 'font_size': 10, 'align': 'center', 'bold': True}),
            "sign_name": wb.add_format({'font_name': 'Arial', 'font_size': 10, 'align': 'center', 'bold': True, 'underline': True}),
            "sign_nip": wb.add_format({'font_name': 'Arial', 'font_size': 9, 'align': 'center'}),
        }

    def _write_school_kop(self, ws, fmt, max_col: int = 6):
        ws.merge_range(0, 0, 0, max_col - 1, "PEMERINTAH PROVINSI DAERAH KHUSUS IBUKOTA JAKARTA", fmt["title_gov"])
        ws.merge_range(1, 0, 1, max_col - 1, "DINAS PENDIDIKAN", fmt["title_dept"])
        ws.merge_range(2, 0, 2, max_col - 1, self.school.get("name", "SEKOLAH DASAR NEGERI"), fmt["title_school"])
        address_line = f"{self.school.get('address', '')} email: {self.school.get('email', '')}"
        ws.merge_range(3, 0, 3, max_col - 1, address_line, fmt["title_address"])

    # ==================== D01: HPS ====================
    def _render_d01_hps(self, wb, fmt):
        ws = wb.add_worksheet("HPS")
        ws.set_column(0, 0, 5)   # No
        ws.set_column(1, 1, 28)  # Nama Barang
        ws.set_column(2, 2, 10)  # Volume
        ws.set_column(3, 3, 10)  # Satuan
        ws.set_column(4, 4, 25)  # Spesifikasi
        ws.set_column(5, 5, 14)  # Harga
        ws.set_column(6, 6, 16)  # Total

        self._write_school_kop(ws, fmt, 7)
        ws.merge_range(5, 0, 5, 6, "HARGA PERKIRAAN SENDIRI", fmt["doc_title"])

        # Metadata
        ws.write(7, 1, "Kegiatan :", fmt["meta_key"])
        ws.write(7, 2, "Pemeliharaan Sarana dan Prasarana Sekolah", fmt["meta_val"])
        ws.write(8, 1, "Rincian Kegiatan :", fmt["meta_key"])
        ws.write(8, 2, "Pembelian Bahan Kebersihan Sekolah", fmt["meta_val"])
        ws.write(9, 1, "Kode Rekening :", fmt["meta_key"])
        ws.write(9, 2, "Bahan-bahan lainnya", fmt["meta_val"])
        ws.write(10, 1, "Tahun Anggaran :", fmt["meta_key"])
        ws.write(10, 2, 2026, fmt["meta_val"])

        # Table Header
        headers = ["NO", "NAMA BARANG", "Volume", "Satuan", "Spesifikasi", "Harga", "Total"]
        for col, h in enumerate(headers):
            ws.write(12, col, h, fmt["tbl_hdr"])

        # Dynamic Lines
        curr_row = 13
        for idx, line in enumerate(self.lines, start=1):
            qty = to_excel_num(line.get("quantity", 1))
            hps_price = to_excel_num(line.get("hps_unit_price", 0))
            line_tot = qty * hps_price

            ws.write(curr_row, 0, idx, fmt["tbl_cell_center"])
            ws.write(curr_row, 1, line.get("confirmed_description", ""), fmt["tbl_cell"])
            ws.write(curr_row, 2, qty, fmt["tbl_cell_center"])
            ws.write(curr_row, 3, line.get("unit", ""), fmt["tbl_cell_center"])
            ws.write(curr_row, 4, line.get("specification", ""), fmt["tbl_cell"])
            ws.write_number(curr_row, 5, hps_price, fmt["tbl_cell_num"])
            ws.write_formula(curr_row, 6, f"=C{curr_row+1}*F{curr_row+1}", fmt["tbl_cell_num"], value=line_tot)
            curr_row += 1

        # Subtotal & Taxes
        ws.merge_range(curr_row, 0, curr_row, 5, "Jumlah", fmt["tbl_total_lbl"])
        ws.write_formula(curr_row, 6, f"=SUM(G14:G{curr_row})", fmt["tbl_total_val"], value=to_excel_num(self.subtotal))
        curr_row += 1

        # Additive tax PPN
        ppn_rate = 0.11
        ppn_amt = to_excel_num(self.subtotal) * ppn_rate
        ws.merge_range(curr_row, 0, curr_row, 5, "PPN 11%", fmt["tbl_total_lbl"])
        ws.write_formula(curr_row, 6, f"=G{curr_row}*0.11", fmt["tbl_total_val"], value=ppn_amt)
        curr_row += 1

        # Total
        ws.merge_range(curr_row, 0, curr_row, 5, "Total", fmt["tbl_total_lbl"])
        ws.write_formula(curr_row, 6, f"=G{curr_row-1}+G{curr_row}", fmt["tbl_total_val"], value=to_excel_num(self.grand_total))
        curr_row += 2

        # Signatures
        hps_event = self.events.get("HPS") or {}
        hps_date_str = format_date_id(hps_event.get("event_date"))
        ws.merge_range(curr_row, 4, curr_row, 6, f"Jakarta, {hps_date_str}", fmt["meta_val"])
        curr_row += 1
        ws.write(curr_row, 1, "Mengetahui,", fmt["meta_val"])
        curr_row += 1
        ws.write(curr_row, 1, "Kepala Sekolah", fmt["sign_role"])
        ws.merge_range(curr_row, 4, curr_row, 6, "Bendahara Sekolah", fmt["sign_role"])
        curr_row += 4
        kepsek = self.officials.get("KEPALA_SEKOLAH") or {}
        bendahara = self.officials.get("BENDAHARA") or {}
        ws.write(curr_row, 1, kepsek.get("person_name", "Kepala Sekolah"), fmt["sign_name"])
        ws.merge_range(curr_row, 4, curr_row, 6, bendahara.get("person_name", "Bendahara"), fmt["sign_name"])
        curr_row += 1
        ws.write(curr_row, 1, f"NIP. {kepsek.get('nip', '-')}", fmt["sign_nip"])
        ws.merge_range(curr_row, 4, curr_row, 6, f"NIP. {bendahara.get('nip', '-')}", fmt["sign_nip"])

    # ==================== D02: SPP ====================
    def _render_d02_spp(self, wb, fmt):
        ws = wb.add_worksheet("SPP")
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 30)
        ws.set_column(2, 2, 12)
        ws.set_column(3, 3, 12)
        ws.set_column(4, 4, 30)

        self._write_school_kop(ws, fmt, 5)
        ws.merge_range(5, 0, 5, 4, "SURAT PERMINTAAN PENAWARAN (SPP)", fmt["doc_title"])

        spp_doc = self.numbers.get("D02") or {}
        spp_event = self.events.get("SPP") or {}
        ws.write(7, 0, f"Nomor : {spp_doc.get('doc_number', '-/PK.03.00')}", fmt["meta_val"])
        ws.write(7, 3, f"Jakarta, {format_date_id(spp_event.get('event_date'))}", fmt["meta_val"])
        ws.write(8, 0, f"Kepada Yth: {self.company.get('legal_name', 'CV Penyedia')}", fmt["meta_val"])
        ws.write(9, 0, "Di Jakarta", fmt["meta_val"])

        ws.write(11, 0, "Dengan hormat, sehubungan dengan kebutuhan kegiatan sekolah, kami meminta penawaran harga untuk:", fmt["meta_val"])

        headers = ["NO", "NAMA BARANG", "Volume", "Satuan", "Spesifikasi"]
        for col, h in enumerate(headers):
            ws.write(13, col, h, fmt["tbl_hdr"])

        curr_row = 14
        for idx, line in enumerate(self.lines, start=1):
            ws.write(curr_row, 0, idx, fmt["tbl_cell_center"])
            ws.write(curr_row, 1, line.get("confirmed_description", ""), fmt["tbl_cell"])
            ws.write(curr_row, 2, to_excel_num(line.get("quantity", 1)), fmt["tbl_cell_center"])
            ws.write(curr_row, 3, line.get("unit", ""), fmt["tbl_cell_center"])
            ws.write(curr_row, 4, line.get("specification", ""), fmt["tbl_cell"])
            curr_row += 1

        curr_row += 2
        kepsek = self.officials.get("KEPALA_SEKOLAH") or {}
        ws.merge_range(curr_row, 3, curr_row, 4, "Kepala Sekolah", fmt["sign_role"])
        curr_row += 4
        ws.merge_range(curr_row, 3, curr_row, 4, kepsek.get("person_name", "Kepala Sekolah"), fmt["sign_name"])
        curr_row += 1
        ws.merge_range(curr_row, 3, curr_row, 4, f"NIP. {kepsek.get('nip', '-')}", fmt["sign_nip"])

    # ==================== D03: SURAT PENAWARAN ====================
    def _render_d03_penawaran(self, wb, fmt):
        ws = wb.add_worksheet("SURAT PENAWARAN")
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 28)
        ws.set_column(2, 2, 10)
        ws.set_column(3, 3, 10)
        ws.set_column(4, 4, 25)
        ws.set_column(5, 5, 14)
        ws.set_column(6, 6, 16)

        # Company Header
        ws.merge_range(0, 0, 0, 6, self.company.get("legal_name", "CV. PUSTAKA CEMERLANG INDONESIA"), fmt["title_school"])
        ws.merge_range(1, 0, 1, 6, self.company.get("address", "Jakarta"), fmt["title_address"])
        ws.merge_range(3, 0, 3, 6, "SURAT PENAWARAN HARGA", fmt["doc_title"])

        doc_num = self.numbers.get("D03") or {}
        ev = self.events.get("PENAWARAN") or {}
        ws.write(5, 0, f"No: {doc_num.get('doc_number', '-')}", fmt["meta_val"])
        ws.write(5, 4, f"Jakarta, {format_date_id(ev.get('event_date'))}", fmt["meta_val"])
        ws.write(6, 0, f"Kepada Yth: Kepala {self.school.get('name', 'Sekolah')}", fmt["meta_val"])

        headers = ["NO", "NAMA BARANG", "Volume", "Satuan", "Spesifikasi", "Harga Penawaran", "Total"]
        for col, h in enumerate(headers):
            ws.write(8, col, h, fmt["tbl_hdr"])

        curr_row = 9
        for idx, line in enumerate(self.lines, start=1):
            qty = to_excel_num(line.get("quantity", 1))
            offer_price = to_excel_num(line.get("offer_unit_price", 0))
            line_tot = qty * offer_price

            ws.write(curr_row, 0, idx, fmt["tbl_cell_center"])
            ws.write(curr_row, 1, line.get("confirmed_description", ""), fmt["tbl_cell"])
            ws.write(curr_row, 2, qty, fmt["tbl_cell_center"])
            ws.write(curr_row, 3, line.get("unit", ""), fmt["tbl_cell_center"])
            ws.write(curr_row, 4, line.get("specification", ""), fmt["tbl_cell"])
            ws.write_number(curr_row, 5, offer_price, fmt["tbl_cell_num"])
            ws.write_formula(curr_row, 6, f"=C{curr_row+1}*F{curr_row+1}", fmt["tbl_cell_num"], value=line_tot)
            curr_row += 1

        ws.merge_range(curr_row, 0, curr_row, 5, "Jumlah Penawaran", fmt["tbl_total_lbl"])
        ws.write_formula(curr_row, 6, f"=SUM(G10:G{curr_row})", fmt["tbl_total_val"], value=to_excel_num(self.subtotal))
        curr_row += 3

        ws.merge_range(curr_row, 4, curr_row, 6, self.company.get("legal_name", "CV Penyedia"), fmt["sign_role"])
        curr_row += 4
        ws.merge_range(curr_row, 4, curr_row, 6, self.company.get("director_name", "Direktur"), fmt["sign_name"])
        curr_row += 1
        ws.merge_range(curr_row, 4, curr_row, 6, self.company.get("director_title", "Direktur"), fmt["sign_nip"])

    # ==================== D04: SURAT NEGOSIASI (2) ====================
    def _render_d04_negosiasi(self, wb, fmt):
        ws = wb.add_worksheet("SURAT NEGOSIASI (2)")
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 24)
        ws.set_column(2, 2, 8)
        ws.set_column(3, 3, 8)
        ws.set_column(4, 4, 14)
        ws.set_column(5, 5, 14)
        ws.set_column(6, 6, 14)

        self._write_school_kop(ws, fmt, 7)
        ws.merge_range(5, 0, 5, 6, "BERITA ACARA HASIL NEGOSIASI HARGA", fmt["doc_title"])

        ev = self.events.get("NEGOSIASI") or {}
        ws.merge_range(7, 0, 7, 6, format_formal_narrative_date(ev.get("event_date")), fmt["meta_val"])

        headers = ["NO", "NAMA BARANG", "Vol", "Satuan", "Harga Penawaran", "Harga Negosiasi", "Total Final"]
        for col, h in enumerate(headers):
            ws.write(9, col, h, fmt["tbl_hdr"])

        curr_row = 10
        for idx, line in enumerate(self.lines, start=1):
            qty = to_excel_num(line.get("quantity", 1))
            offer = to_excel_num(line.get("offer_unit_price", 0))
            final = to_excel_num(line.get("final_unit_price", 0))
            line_tot = qty * final

            ws.write(curr_row, 0, idx, fmt["tbl_cell_center"])
            ws.write(curr_row, 1, line.get("confirmed_description", ""), fmt["tbl_cell"])
            ws.write(curr_row, 2, qty, fmt["tbl_cell_center"])
            ws.write(curr_row, 3, line.get("unit", ""), fmt["tbl_cell_center"])
            ws.write_number(curr_row, 4, offer, fmt["tbl_cell_num"])
            ws.write_number(curr_row, 5, final, fmt["tbl_cell_num"])
            ws.write_formula(curr_row, 6, f"=C{curr_row+1}*F{curr_row+1}", fmt["tbl_cell_num"], value=line_tot)
            curr_row += 1

        ws.merge_range(curr_row, 0, curr_row, 5, "Total Kesepakatan", fmt["tbl_total_lbl"])
        ws.write_formula(curr_row, 6, f"=SUM(G11:G{curr_row})", fmt["tbl_total_val"], value=to_excel_num(self.subtotal))
        curr_row += 3

        # Dual signoff
        ws.write(curr_row, 1, "Pihak Perusahaan,", fmt["sign_role"])
        ws.merge_range(curr_row, 4, curr_row, 6, "Pejabat Pengadaan Sekolah,", fmt["sign_role"])
        curr_row += 4
        ws.write(curr_row, 1, self.company.get("director_name", "Direktur"), fmt["sign_name"])
        kepsek = self.officials.get("KEPALA_SEKOLAH") or {}
        ws.merge_range(curr_row, 4, curr_row, 6, kepsek.get("person_name", "Kepala Sekolah"), fmt["sign_name"])

    # ==================== D05: SURAT PESANAN (2) ====================
    def _render_d05_pesanan(self, wb, fmt):
        ws = wb.add_worksheet("SURAT PESANAN (2)")
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 28)
        ws.set_column(2, 2, 8)
        ws.set_column(3, 3, 10)
        ws.set_column(4, 4, 14)
        ws.set_column(5, 5, 16)

        self._write_school_kop(ws, fmt, 6)
        ws.merge_range(5, 0, 5, 5, "SURAT PESANAN (SP)", fmt["doc_title"])

        doc_num = self.numbers.get("D05") or {}
        ev = self.events.get("PESANAN") or {}
        ws.write(7, 0, f"Nomor: {doc_num.get('doc_number', '-')}", fmt["meta_val"])
        ws.write(7, 4, f"Jakarta, {format_date_id(ev.get('event_date'))}", fmt["meta_val"])
        ws.write(8, 0, f"Penyedia: {self.company.get('legal_name', '')}", fmt["meta_val"])

        headers = ["NO", "NAMA BARANG", "Volume", "Satuan", "Harga Final", "Total"]
        for col, h in enumerate(headers):
            ws.write(10, col, h, fmt["tbl_hdr"])

        curr_row = 11
        for idx, line in enumerate(self.lines, start=1):
            qty = to_excel_num(line.get("quantity", 1))
            final = to_excel_num(line.get("final_unit_price", 0))
            line_tot = qty * final

            ws.write(curr_row, 0, idx, fmt["tbl_cell_center"])
            ws.write(curr_row, 1, line.get("confirmed_description", ""), fmt["tbl_cell"])
            ws.write(curr_row, 2, qty, fmt["tbl_cell_center"])
            ws.write(curr_row, 3, line.get("unit", ""), fmt["tbl_cell_center"])
            ws.write_number(curr_row, 4, final, fmt["tbl_cell_num"])
            ws.write_formula(curr_row, 5, f"=C{curr_row+1}*E{curr_row+1}", fmt["tbl_cell_num"], value=line_tot)
            curr_row += 1

        ws.merge_range(curr_row, 0, curr_row, 4, "Total Barang", fmt["tbl_total_lbl"])
        ws.write_formula(curr_row, 5, f"=SUM(F12:F{curr_row})", fmt["tbl_total_val"], value=to_excel_num(self.subtotal))
        curr_row += 3

        kepsek = self.officials.get("KEPALA_SEKOLAH") or {}
        ws.merge_range(curr_row, 3, curr_row, 5, "Kepala Sekolah (Pejabat Pembuat Komitmen)", fmt["sign_role"])
        curr_row += 4
        ws.merge_range(curr_row, 3, curr_row, 5, kepsek.get("person_name", "Kepala Sekolah"), fmt["sign_name"])

    # ==================== D06: FAKTUR ====================
    def _render_d06_faktur(self, wb, fmt):
        ws = wb.add_worksheet("FAKTUR")
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 26)
        ws.set_column(2, 2, 8)
        ws.set_column(3, 3, 14)
        ws.set_column(4, 4, 16)
        ws.set_column(5, 5, 14)

        ws.merge_range(0, 0, 0, 5, self.company.get("legal_name", ""), fmt["title_school"])
        ws.merge_range(1, 0, 1, 5, "SALES INVOICE / FAKTUR PENJUALAN", fmt["doc_title"])

        doc_num = self.numbers.get("D06") or {}
        ev = self.events.get("FAKTUR") or {}
        ws.write(3, 0, f"Invoice No : {doc_num.get('doc_number', '-')}", fmt["meta_val"])
        ws.write(3, 3, f"Invoice Date : {format_date_id(ev.get('event_date'))}", fmt["meta_val"])
        ws.write(4, 0, f"Bill/Ship To: {self.school.get('name', '')}", fmt["meta_val"])

        headers = ["Item", "Description", "Qty", "Unit Price", "Total", "PPN (11%)"]
        for col, h in enumerate(headers):
            ws.write(6, col, h, fmt["tbl_hdr"])

        curr_row = 7
        for idx, line in enumerate(self.lines, start=1):
            qty = to_excel_num(line.get("quantity", 1))
            final = to_excel_num(line.get("final_unit_price", 0))
            line_tot = qty * final
            ppn_line = line_tot * 0.11

            ws.write(curr_row, 0, idx, fmt["tbl_cell_center"])
            ws.write(curr_row, 1, line.get("confirmed_description", ""), fmt["tbl_cell"])
            ws.write(curr_row, 2, qty, fmt["tbl_cell_center"])
            ws.write_number(curr_row, 3, final, fmt["tbl_cell_num"])
            ws.write_formula(curr_row, 4, f"=C{curr_row+1}*D{curr_row+1}", fmt["tbl_cell_num"], value=line_tot)
            ws.write_formula(curr_row, 5, f"=E{curr_row+1}*0.11", fmt["tbl_cell_num"], value=ppn_line)
            curr_row += 1

        ws.merge_range(curr_row, 0, curr_row, 3, "Subtotal", fmt["tbl_total_lbl"])
        ws.write_formula(curr_row, 4, f"=SUM(E8:E{curr_row})", fmt["tbl_total_val"], value=to_excel_num(self.subtotal))
        ws.write_formula(curr_row, 5, f"=SUM(F8:F{curr_row})", fmt["tbl_total_val"], value=to_excel_num(self.tax_total))
        curr_row += 1

        ws.merge_range(curr_row, 0, curr_row, 3, "Grand Total", fmt["tbl_total_lbl"])
        ws.write_formula(curr_row, 4, f"=E{curr_row}+F{curr_row}", fmt["tbl_total_val"], value=to_excel_num(self.grand_total))
        curr_row += 3

        ws.write(curr_row, 1, "Approved By:", fmt["sign_role"])
        ws.write(curr_row, 4, "Received By:", fmt["sign_role"])
        curr_row += 4
        ws.write(curr_row, 1, self.company.get("director_name", "Direktur"), fmt["sign_name"])
        kepsek = self.officials.get("KEPALA_SEKOLAH") or {}
        ws.write(curr_row, 4, kepsek.get("person_name", "Kepala Sekolah"), fmt["sign_name"])

    # ==================== D07: KWITANSI ====================
    def _render_d07_kwitansi(self, wb, fmt):
        ws = wb.add_worksheet("KWITANSI")
        ws.set_column(0, 0, 15)
        ws.set_column(1, 1, 3)
        ws.set_column(2, 2, 55)

        ws.merge_range(0, 0, 0, 2, self.company.get("legal_name", ""), fmt["title_school"])
        ws.merge_range(1, 0, 1, 2, self.company.get("address", ""), fmt["title_address"])
        ws.merge_range(3, 0, 3, 2, "KWITANSI / BUKTI PEMBAYARAN", fmt["doc_title"])

        doc_num = self.numbers.get("D07") or {}
        ev = self.events.get("KWITANSI") or {}
        ws.write(5, 0, "No", fmt["meta_key"])
        ws.write(5, 1, ":", fmt["meta_val"])
        ws.write(5, 2, doc_num.get("doc_number", "-"), fmt["meta_val"])

        ws.write(6, 0, "Telah terima dari", fmt["meta_key"])
        ws.write(6, 1, ":", fmt["meta_val"])
        ws.write(6, 2, f"Bendahara {self.school.get('name', '')}", fmt["meta_val"])

        ws.write(7, 0, "Jumlah Uang", fmt["meta_key"])
        ws.write(7, 1, ":", fmt["meta_val"])
        ws.write(7, 2, format_idr(self.grand_total), fmt["meta_key"])

        ws.write(8, 0, "Terbilang", fmt["meta_key"])
        ws.write(8, 1, ":", fmt["meta_val"])
        ws.write(8, 2, terbilang(self.grand_total), fmt["tbl_cell"])

        ws.write(10, 0, "Untuk Pembayaran", fmt["meta_key"])
        ws.write(10, 1, ":", fmt["meta_val"])
        ws.write(10, 2, "Pembelian Bahan Kebersihan Sekolah", fmt["meta_val"])

        curr_row = 13
        ws.write(curr_row, 2, f"Jakarta, {format_date_id(ev.get('event_date'))}", fmt["meta_val"])
        curr_row += 1
        ws.write(curr_row, 2, self.company.get("legal_name", ""), fmt["sign_role"])
        curr_row += 4
        ws.write(curr_row, 2, self.company.get("director_name", "Direktur"), fmt["sign_name"])

    # ==================== D08: SURAT JALAN ====================
    def _render_d08_surat_jalan(self, wb, fmt):
        ws = wb.add_worksheet("SURAT JALAN")
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 28)
        ws.set_column(2, 2, 10)
        ws.set_column(3, 3, 10)
        ws.set_column(4, 4, 30)

        ws.merge_range(0, 0, 0, 4, self.company.get("legal_name", ""), fmt["title_school"])
        ws.merge_range(1, 0, 1, 4, "SURAT JALAN PENGIRIMAN BARANG", fmt["doc_title"])

        doc_num = self.numbers.get("D08") or {}
        ev = self.events.get("SURAT_JALAN") or {}
        ws.write(3, 0, f"Delivery No: {doc_num.get('doc_number', '-')}", fmt["meta_val"])
        ws.write(3, 3, f"Tanggal: {format_date_id(ev.get('event_date'))}", fmt["meta_val"])
        ws.write(4, 0, f"Tujuan: {self.school.get('name', '')}", fmt["meta_val"])

        headers = ["NO", "NAMA BARANG", "Volume", "Satuan", "Spesifikasi"]
        for col, h in enumerate(headers):
            ws.write(6, col, h, fmt["tbl_hdr"])

        curr_row = 7
        for idx, line in enumerate(self.lines, start=1):
            ws.write(curr_row, 0, idx, fmt["tbl_cell_center"])
            ws.write(curr_row, 1, line.get("confirmed_description", ""), fmt["tbl_cell"])
            ws.write(curr_row, 2, to_excel_num(line.get("quantity", 1)), fmt["tbl_cell_center"])
            ws.write(curr_row, 3, line.get("unit", ""), fmt["tbl_cell_center"])
            ws.write(curr_row, 4, line.get("specification", ""), fmt["tbl_cell"])
            curr_row += 1

        curr_row += 2
        ws.write(curr_row, 1, "Pengirim (Logistik),", fmt["sign_role"])
        ws.write(curr_row, 3, "Penerima Barang,", fmt["sign_role"])
        curr_row += 4
        ws.write(curr_row, 1, "Bagian Gudang", fmt["sign_name"])
        pengurus = self.officials.get("PENGURUS_BARANG") or {}
        ws.write(curr_row, 3, pengurus.get("person_name", "Pengurus Barang"), fmt["sign_name"])

    # ==================== D09: BAPB ====================
    def _render_d09_bapb(self, wb, fmt):
        ws = wb.add_worksheet("BAPB")
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 28)
        ws.set_column(2, 2, 10)
        ws.set_column(3, 3, 10)
        ws.set_column(4, 4, 15)

        self._write_school_kop(ws, fmt, 5)
        ws.merge_range(5, 0, 5, 4, "BERITA ACARA PEMERIKSAAN BARANG (BAPB)", fmt["doc_title"])

        ev = self.events.get("BAPB") or {}
        ws.merge_range(7, 0, 7, 4, format_formal_narrative_date(ev.get("event_date")), fmt["meta_val"])

        headers = ["NO", "NAMA BARANG", "Volume", "Satuan", "Kondisi"]
        for col, h in enumerate(headers):
            ws.write(9, col, h, fmt["tbl_hdr"])

        curr_row = 10
        for idx, line in enumerate(self.lines, start=1):
            ws.write(curr_row, 0, idx, fmt["tbl_cell_center"])
            ws.write(curr_row, 1, line.get("confirmed_description", ""), fmt["tbl_cell"])
            ws.write(curr_row, 2, to_excel_num(line.get("quantity", 1)), fmt["tbl_cell_center"])
            ws.write(curr_row, 3, line.get("unit", ""), fmt["tbl_cell_center"])
            ws.write(curr_row, 4, line.get("condition", "Baik"), fmt["tbl_cell_center"])
            curr_row += 1

        curr_row += 2
        pengurus = self.officials.get("PENGURUS_BARANG") or {}
        ws.merge_range(curr_row, 2, curr_row, 4, "Petugas Pemeriksa Barang,", fmt["sign_role"])
        curr_row += 4
        ws.merge_range(curr_row, 2, curr_row, 4, pengurus.get("person_name", "Pengurus Barang"), fmt["sign_name"])

    # ==================== D10: BAST ====================
    def _render_d10_bast(self, wb, fmt):
        ws = wb.add_worksheet("BAST")
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 28)
        ws.set_column(2, 2, 10)
        ws.set_column(3, 3, 10)
        ws.set_column(4, 4, 15)

        self._write_school_kop(ws, fmt, 5)
        ws.merge_range(5, 0, 5, 4, "BERITA ACARA SERAH TERIMA BARANG (BAST)", fmt["doc_title"])

        ev = self.events.get("BAST") or {}
        ws.merge_range(7, 0, 7, 4, format_formal_narrative_date(ev.get("event_date")), fmt["meta_val"])

        headers = ["NO", "NAMA BARANG", "Volume", "Satuan", "Keterangan"]
        for col, h in enumerate(headers):
            ws.write(9, col, h, fmt["tbl_hdr"])

        curr_row = 10
        for idx, line in enumerate(self.lines, start=1):
            ws.write(curr_row, 0, idx, fmt["tbl_cell_center"])
            ws.write(curr_row, 1, line.get("confirmed_description", ""), fmt["tbl_cell"])
            ws.write(curr_row, 2, to_excel_num(line.get("quantity", 1)), fmt["tbl_cell_center"])
            ws.write(curr_row, 3, line.get("unit", ""), fmt["tbl_cell_center"])
            ws.write(curr_row, 4, "Lengkap", fmt["tbl_cell_center"])
            curr_row += 1

        curr_row += 2
        ws.write(curr_row, 1, "Yang Menyerahkan (Pihak Kedua),", fmt["sign_role"])
        ws.write(curr_row, 3, "Yang Menerima (Pihak Pertama),", fmt["sign_role"])
        curr_row += 4
        ws.write(curr_row, 1, self.company.get("director_name", "Direktur"), fmt["sign_name"])
        kepsek = self.officials.get("KEPALA_SEKOLAH") or {}
        ws.write(curr_row, 3, kepsek.get("person_name", "Kepala Sekolah"), fmt["sign_name"])

    # ==================== D11: BAPP ====================
    def _render_d11_bapp(self, wb, fmt):
        ws = wb.add_worksheet("BAPP")
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 35)
        ws.set_column(2, 2, 35)

        self._write_school_kop(ws, fmt, 3)
        ws.merge_range(5, 0, 5, 2, "BERITA ACARA PENYELESAIAN PEKERJAAN (BAPP)", fmt["doc_title"])

        ev = self.events.get("BAPP") or {}
        ws.merge_range(7, 0, 7, 2, format_formal_narrative_date(ev.get("event_date")), fmt["meta_val"])
        ws.merge_range(9, 0, 9, 2, "Menyatakan bahwa pekerjaan pengadaan sarana kebersihan telah selesai 100% dan diterima dalam kondisi baik.", fmt["meta_val"])

        curr_row = 12
        ws.write(curr_row, 1, "Pihak Penyedia,", fmt["sign_role"])
        ws.write(curr_row, 2, "Pengguna Anggaran / Kepala Sekolah,", fmt["sign_role"])
        curr_row += 4
        ws.write(curr_row, 1, self.company.get("director_name", "Direktur"), fmt["sign_name"])
        kepsek = self.officials.get("KEPALA_SEKOLAH") or {}
        ws.write(curr_row, 2, kepsek.get("person_name", "Kepala Sekolah"), fmt["sign_name"])

    # ==================== D12: Lamp BAPP ====================
    def _render_d12_lamp_bapp(self, wb, fmt):
        ws = wb.add_worksheet("Lamp BAPP")
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 28)
        ws.set_column(2, 2, 8)
        ws.set_column(3, 3, 10)
        ws.set_column(4, 4, 14)
        ws.set_column(5, 5, 16)
        ws.set_column(6, 6, 12)

        ws.merge_range(0, 0, 0, 6, "LAMPIRAN BERITA ACARA PENYELESAIAN PEKERJAAN", fmt["doc_title"])
        headers = ["NO", "Uraian Barang", "Volume", "Satuan", "Harga", "Jumlah", "Kondisi"]
        for col, h in enumerate(headers):
            ws.write(3, col, h, fmt["tbl_hdr"])

        curr_row = 4
        for idx, line in enumerate(self.lines, start=1):
            qty = to_excel_num(line.get("quantity", 1))
            final = to_excel_num(line.get("final_unit_price", 0))
            line_tot = qty * final

            ws.write(curr_row, 0, idx, fmt["tbl_cell_center"])
            ws.write(curr_row, 1, line.get("confirmed_description", ""), fmt["tbl_cell"])
            ws.write(curr_row, 2, qty, fmt["tbl_cell_center"])
            ws.write(curr_row, 3, line.get("unit", ""), fmt["tbl_cell_center"])
            ws.write_number(curr_row, 4, final, fmt["tbl_cell_num"])
            ws.write_formula(curr_row, 5, f"=C{curr_row+1}*E{curr_row+1}", fmt["tbl_cell_num"], value=line_tot)
            ws.write(curr_row, 6, line.get("condition", "Baik"), fmt["tbl_cell_center"])
            curr_row += 1

        ws.merge_range(curr_row, 0, curr_row, 4, "Total Akhir", fmt["tbl_total_lbl"])
        ws.write_formula(curr_row, 5, f"=SUM(F5:F{curr_row})", fmt["tbl_total_val"], value=to_excel_num(self.subtotal))

    # ==================== D13: BAST Rekanan ====================
    def _render_d13_bast_rekanan(self, wb, fmt):
        ws = wb.add_worksheet("BAST Rekanan")
        ws.set_column(0, 0, 5)
        ws.set_column(1, 1, 28)
        ws.set_column(2, 2, 10)
        ws.set_column(3, 3, 10)
        ws.set_column(4, 4, 15)

        ws.merge_range(0, 0, 0, 4, self.company.get("legal_name", ""), fmt["title_school"])
        ws.merge_range(1, 0, 1, 4, "BERITA ACARA SERAH TERIMA HASIL PEKERJAAN (REKANAN)", fmt["doc_title"])

        doc_num = self.numbers.get("D13") or {}
        ev = self.events.get("BAST_REKANAN") or {}
        ws.write(3, 0, f"Nomor: {doc_num.get('doc_number', '-')}", fmt["meta_val"])
        ws.write(3, 3, f"Tanggal: {format_date_id(ev.get('event_date'))}", fmt["meta_val"])

        headers = ["NO", "Nama Barang / Jasa", "Kuantitas", "Satuan", "Kondisi Barang"]
        for col, h in enumerate(headers):
            ws.write(5, col, h, fmt["tbl_hdr"])

        curr_row = 6
        for idx, line in enumerate(self.lines, start=1):
            ws.write(curr_row, 0, idx, fmt["tbl_cell_center"])
            ws.write(curr_row, 1, line.get("confirmed_description", ""), fmt["tbl_cell"])
            ws.write(curr_row, 2, to_excel_num(line.get("quantity", 1)), fmt["tbl_cell_center"])
            ws.write(curr_row, 3, line.get("unit", ""), fmt["tbl_cell_center"])
            ws.write(curr_row, 4, line.get("condition", "Baik"), fmt["tbl_cell_center"])
            curr_row += 1

        curr_row += 2
        ws.write(curr_row, 1, "Yang Menyerahkan (Penyedia),", fmt["sign_role"])
        ws.write(curr_row, 3, "Yang Menerima (Sekolah),", fmt["sign_role"])
        curr_row += 4
        ws.write(curr_row, 1, self.company.get("director_name", "Direktur"), fmt["sign_name"])
        pengurus = self.officials.get("PENGURUS_BARANG") or {}
        ws.write(curr_row, 3, pengurus.get("person_name", "Pengurus Barang"), fmt["sign_name"])
