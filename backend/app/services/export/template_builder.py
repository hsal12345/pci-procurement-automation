"""Programmatic Word template builder for creating standard, high-fidelity,
formally aligned docxtpl Word templates for all 13 official procurement & SPJ documents (D01-D13).

Features:
- Dynamic multi-row repetition using docxtpl row loops ({%tr for item in items %} ... {%tr endfor %})
- Explicit column widths matching standard 6.75 inch A4 text boundaries
- Professional table styling: vertical centering, cell padding, repeating headers (tblHeader), cantSplit
- Built-in table summary rows (Subtotal, PPN, Grand Total)
- Formal 2-column and 3-column borderless signature blocks with stamp space
- Official Indonesian government & corporate Kop Surat headers with double divider lines
"""
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "docx"

# Color Palette for Formal Documents
COLOR_BORDER = "A0AEC0"       # Subtle slate border
COLOR_HDR_BG = "EDF2F7"       # Soft grey/slate background
COLOR_PRIMARY = RGBColor(26, 54, 93)   # Deep Navy for Kop
COLOR_DARK = RGBColor(45, 55, 72)      # Charcoal for Body text
COLOR_DRAFT = RGBColor(197, 48, 48)    # Crimson for draft banner


def set_cell_margins(cell, top=120, bottom=120, left=140, right=140):
    """Sets cell padding in twips (1/20 of a pt; 120 twips = 6 pt, 140 = 7 pt)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def set_cell_shading(cell, color_hex=COLOR_HDR_BG):
    """Sets background fill color of a cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)


def set_cell_width(cell, width_in_inches):
    """Explicitly assigns column width in dxa so Word tables never shrink or distort."""
    cell.width = Inches(width_in_inches)
    tcPr = cell._tc.get_or_add_tcPr()
    tcW = OxmlElement('w:tcW')
    tcW.set(qn('w:w'), str(int(width_in_inches * 1440)))
    tcW.set(qn('w:type'), 'dxa')
    tcPr.append(tcW)


def set_cell_v_align(cell, align="center"):
    """Vertically aligns content in table cell (top, center, bottom)."""
    tcPr = cell._tc.get_or_add_tcPr()
    vAlign = OxmlElement('w:vAlign')
    vAlign.set(qn('w:val'), align)
    tcPr.append(vAlign)


def set_table_borders(table, color=COLOR_BORDER, sz="4", val="single"):
    """Applies clean, subtle borders across all table cells."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def set_row_height(row, height_pt=20):
    """Sets row minimum height in points."""
    trPr = row._tr.get_or_add_trPr()
    trHeight = OxmlElement('w:trHeight')
    trHeight.set(qn('w:val'), str(int(height_pt * 20)))
    trHeight.set(qn('w:hRule'), 'atLeast')
    trPr.append(trHeight)


def mark_row_header(row):
    """Sets w:tblHeader so table headers repeat cleanly across page splits."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(OxmlElement('w:tblHeader'))


def mark_row_cant_split(row):
    """Sets w:cantSplit to avoid awkward row cutoffs across page breaks."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(OxmlElement('w:cantSplit'))


def add_draft_banner(doc):
    """Adds a conditional draft warning paragraph at the very top."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("{{ draft_banner }}")
    run.font.name = "Arial"
    run.font.size = Pt(8.5)
    run.font.bold = True
    run.font.color.rgb = COLOR_DRAFT


def add_school_kop(doc):
    """Standardized Kop Surat Pemerintah Provinsi DKI Jakarta / Dinas Pendidikan."""
    p_img = doc.add_paragraph()
    p_img.paragraph_format.space_before = Pt(0)
    p_img.paragraph_format.space_after = Pt(4)
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_img = p_img.add_run("{% if school_has_letterhead_image %}{{ school_letterhead_image }}{% else %}")
    r_img.font.name = "Arial"

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    r1 = p.add_run("PEMERINTAH PROVINSI DAERAH KHUSUS IBUKOTA JAKARTA\nDINAS PENDIDIKAN\n")
    r1.font.name = "Arial"
    r1.font.size = Pt(10)
    r1.font.bold = True
    r1.font.color.rgb = COLOR_PRIMARY

    r2 = p.add_run("{{ school.name }}\n")
    r2.font.name = "Arial"
    r2.font.size = Pt(12)
    r2.font.bold = True
    r2.font.color.rgb = COLOR_PRIMARY

    r3 = p.add_run("{{ school.address }} | Telp: {{ school.phone }} | Email: {{ school.email }}\n")
    r3.font.name = "Arial"
    r3.font.size = Pt(8.5)
    r3.font.italic = True
    r3.font.color.rgb = COLOR_DARK

    p_line = doc.add_paragraph()
    p_line.paragraph_format.space_before = Pt(0)
    p_line.paragraph_format.space_after = Pt(8)
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_line = p_line.add_run("=" * 68 + "{% endif %}")
    r_line.font.name = "Arial"
    r_line.font.bold = True
    r_line.font.size = Pt(9.5)
    r_line.font.color.rgb = COLOR_PRIMARY


def add_company_kop(doc):
    """Standardized Kop Surat CV. Pustaka Cemerlang Indonesia."""
    p_img = doc.add_paragraph()
    p_img.paragraph_format.space_before = Pt(0)
    p_img.paragraph_format.space_after = Pt(4)
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_img = p_img.add_run("{% if company_has_letterhead_image %}{{ company_letterhead_image }}{% else %}")
    r_img.font.name = "Arial"

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    r1 = p.add_run("{{ company.legal_name }}\n")
    r1.font.name = "Arial"
    r1.font.size = Pt(12)
    r1.font.bold = True
    r1.font.color.rgb = COLOR_PRIMARY

    r2 = p.add_run("Penyedia Pengadaan Barang & Jasa Sekolah, Alat Tulis Kantor, dan Percetakan\n")
    r2.font.name = "Arial"
    r2.font.size = Pt(9)
    r2.font.color.rgb = COLOR_DARK

    r3 = p.add_run("{{ company.address }} | Telp: {{ company.phone }} | NPWP: {{ company.npwp }}\n")
    r3.font.name = "Arial"
    r3.font.size = Pt(8.5)
    r3.font.italic = True
    r3.font.color.rgb = COLOR_DARK

    p_line = doc.add_paragraph()
    p_line.paragraph_format.space_before = Pt(0)
    p_line.paragraph_format.space_after = Pt(8)
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_line = p_line.add_run("=" * 68 + "{% endif %}")
    r_line.font.name = "Arial"
    r_line.font.bold = True
    r_line.font.size = Pt(9.5)
    r_line.font.color.rgb = COLOR_PRIMARY


def add_signatures_2col(
    doc: Document,
    left_title: str,
    left_role: str,
    left_name: str,
    left_nip: str,
    right_title: str,
    right_role: str,
    right_name: str,
    right_nip: str,
    date_str: str = None
):
    """Adds a formal borderless 2-column signature block that never splits across pages."""
    tbl = doc.add_table(rows=1, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Clear borders
    tblPr = tbl._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="none"/><w:bottom w:val="none"/><w:left w:val="none"/><w:right w:val="none"/>'
        f'  <w:insideH w:val="none"/><w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

    row = tbl.rows[0]
    mark_row_cant_split(row)

    c_left = row.cells[0]
    c_right = row.cells[1]
    set_cell_width(c_left, 3.35)
    set_cell_width(c_right, 3.35)
    set_cell_margins(c_left, top=100, bottom=100, left=40, right=40)
    set_cell_margins(c_right, top=100, bottom=100, left=40, right=40)

    # Left Cell
    p_l = c_left.paragraphs[0]
    p_l.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_l.paragraph_format.line_spacing = 1.2
    p_l.paragraph_format.keep_with_next = True
    r_lt = p_l.add_run(f"{left_title}\n{left_role}\n\n\n\n\n")
    r_lt.font.name = "Arial"
    r_ln = p_l.add_run(f"{left_name}\n")
    r_ln.font.name = "Arial"
    r_ln.font.bold = True
    r_ln.underline = True
    if left_nip:
        r_lp = p_l.add_run(f"NIP: {left_nip}")
        r_lp.font.name = "Arial"

    # Right Cell
    p_r = c_right.paragraphs[0]
    p_r.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_r.paragraph_format.line_spacing = 1.2
    p_r.paragraph_format.keep_with_next = True
    top_line = f"Jakarta, {date_str}\n" if date_str else ""
    r_rt = p_r.add_run(f"{top_line}{right_title}\n{right_role}\n\n\n\n\n")
    r_rt.font.name = "Arial"
    r_rn = p_r.add_run(f"{right_name}\n")
    r_rn.font.name = "Arial"
    r_rn.font.bold = True
    r_rn.underline = True
    if right_nip:
        r_rp = p_r.add_run(f"NIP: {right_nip}")
        r_rp.font.name = "Arial"


def add_signatures_pphp(
    doc: Document,
    school_name_var: str,
    pphp_ketua_name_var: str,
    pphp_ketua_nip_var: str,
    pphp_sekre_name_var: str,
    pphp_sekre_nip_var: str,
    pphp_anggo_name_var: str,
    pphp_anggo_nip_var: str,
    company_name_var: str,
    director_name_var: str
):
    """Adds formal multi-party signature block for PPHP examination documents."""
    p_intro = doc.add_paragraph()
    p_intro.paragraph_format.space_before = Pt(8)
    p_intro.paragraph_format.space_after = Pt(4)
    p_intro.paragraph_format.keep_with_next = True
    r_in = p_intro.add_run("Tim Pemeriksa Hasil Pekerjaan (PPHP):\n")
    r_in.font.name = "Arial"
    r_in.font.bold = True

    tbl = doc.add_table(rows=3, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Clear borders
    tblPr = tbl._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="none"/><w:bottom w:val="none"/><w:left w:val="none"/><w:right w:val="none"/>'
        f'  <w:insideH w:val="none"/><w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

    for r in tbl.rows:
        mark_row_cant_split(r)
        set_cell_width(r.cells[0], 4.2)
        set_cell_width(r.cells[1], 2.5)
        set_cell_margins(r.cells[0], top=40, bottom=40)
        set_cell_margins(r.cells[1], top=40, bottom=40)

    # Ketua
    p1 = tbl.rows[0].cells[0].paragraphs[0]
    p1.paragraph_format.keep_with_next = True
    r1 = p1.add_run(f"1. Ketua      : {pphp_ketua_name_var} (NIP: {pphp_ketua_nip_var})")
    r1.font.name = "Arial"
    p1_r = tbl.rows[0].cells[1].paragraphs[0]
    p1_r.paragraph_format.keep_with_next = True
    r1_r = p1_r.add_run("( 1. ................................ )")
    r1_r.font.name = "Arial"

    # Sekretaris
    p2 = tbl.rows[1].cells[0].paragraphs[0]
    p2.paragraph_format.keep_with_next = True
    r2 = p2.add_run(f"2. Sekretaris : {pphp_sekre_name_var} (NIP: {pphp_sekre_nip_var})")
    r2.font.name = "Arial"
    p2_r = tbl.rows[1].cells[1].paragraphs[0]
    p2_r.paragraph_format.keep_with_next = True
    r2_r = p2_r.add_run("( 2. ................................ )")
    r2_r.font.name = "Arial"

    # Anggota
    p3 = tbl.rows[2].cells[0].paragraphs[0]
    p3.paragraph_format.keep_with_next = True
    r3 = p3.add_run(f"3. Anggota    : {pphp_anggo_name_var} (NIP: {pphp_anggo_nip_var})")
    r3.font.name = "Arial"
    p3_r = tbl.rows[2].cells[1].paragraphs[0]
    p3_r.paragraph_format.keep_with_next = True
    r3_r = p3_r.add_run("( 3. ................................ )")
    r3_r.font.name = "Arial"

    p_ven = doc.add_paragraph()
    p_ven.paragraph_format.space_before = Pt(10)
    p_ven.paragraph_format.space_after = Pt(2)
    p_ven.paragraph_format.keep_with_next = True
    r_v = p_ven.add_run(f"Penyedia Barang ({company_name_var}):\n\n\n\n")
    r_v.font.name = "Arial"
    r_d = p_ven.add_run(f"{director_name_var}\n")
    r_d.font.name = "Arial"
    r_d.font.bold = True
    r_d.underline = True
    r_dir = p_ven.add_run("Direktur")
    r_dir.font.name = "Arial"


def build_all_templates():
    """Generates all 13 canonical .docx templates with dynamic row repetition and formal layouts."""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    builders = {
        "D01_HPS.docx": _build_d01_hps,
        "D02_SPP.docx": _build_d02_spp,
        "D03_S_PENAWARAN.docx": _build_d03_penawaran,
        "D04_S_NEGOSIASI.docx": _build_d04_negosiasi,
        "D05_SURAT_PESANAN.docx": _build_d05_pesanan,
        "D06_FAKTUR.docx": _build_d06_faktur,
        "D07_KWITANSI.docx": _build_d07_kwitansi,
        "D08_SURAT_JALAN.docx": _build_d08_surat_jalan,
        "D09_BAPB.docx": _build_d09_bapb,
        "D10_BAST.docx": _build_d10_bast,
        "D11_BAPP.docx": _build_d11_bapp,
        "D12_LAMP_BAPP.docx": _build_d12_lamp_bapp,
        "D13_BAST_REKANAN.docx": _build_d13_bast_rekanan,
    }

    created = []
    for filename, builder_func in builders.items():
        file_path = TEMPLATES_DIR / filename
        doc = Document()
        normal_style = doc.styles['Normal']
        normal_style.font.name = 'Arial'
        normal_style.font.size = Pt(9.5)

        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)

        builder_func(doc)
        doc.save(str(file_path))
        created.append(filename)

    return created


# ---------------------------------------------------------------------------
# Individual Template Builders (D01 - D13)
# ---------------------------------------------------------------------------

def _build_d01_hps(doc: Document):
    add_draft_banner(doc)
    add_school_kop(doc)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("HARGA PERKIRAAN SENDIRI (HPS)\n")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(11.5)
    r_title.font.bold = True
    r_title.underline = True

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_after = Pt(6)
    p_meta.paragraph_format.line_spacing = 1.15
    p_meta.add_run("Pekerjaan       : Pengadaan Kebutuhan Operasional Sekolah\n")
    p_meta.add_run("Satuan Kerja    : {{ school.name }}\n")
    p_meta.add_run("Tahun Anggaran  : {{ package.fiscal_year }}\n")

    col_widths = [0.35, 2.65, 0.55, 0.60, 1.25, 1.35]
    tbl = doc.add_table(rows=7, cols=6)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    # Row 0: Headers
    headers = ["No", "Nama Barang / Spesifikasi", "Vol", "Sat", "Harga HPS (Rp)", "Total HPS (Rp)"]
    hdr_row = tbl.rows[0]
    mark_row_header(hdr_row)
    mark_row_cant_split(hdr_row)
    set_row_height(hdr_row, 22)
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=120, bottom=120)
        set_cell_shading(cell)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9)

    # Row 1: Loop start
    tbl.rows[1].cells[0].text = "{%tr for item in items %}"

    # Row 2: Dynamic Data Row
    data_row = tbl.rows[2]
    mark_row_cant_split(data_row)
    set_row_height(data_row, 18)
    tags = [
        "{{ item.no }}",
        "{{ item.name }}\n{{ item.spec }}",
        "{{ item.volume }}",
        "{{ item.unit }}",
        "{{ item.hps_price_formatted }}",
        "{{ item.hps_total_formatted }}"
    ]
    for i, t in enumerate(tags):
        cell = data_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=90, bottom=90)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 2, 3] else (WD_ALIGN_PARAGRAPH.RIGHT if i >= 4 else WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run(t)
        r.font.size = Pt(9)

    # Row 3: Loop end
    tbl.rows[3].cells[0].text = "{%tr endfor %}"

    # Row 4: Subtotal
    r_sub = tbl.rows[4]
    mark_row_cant_split(r_sub)
    set_row_height(r_sub, 18)
    r_sub.cells[0].merge(r_sub.cells[4])
    set_cell_margins(r_sub.cells[0], top=80, bottom=80)
    set_cell_margins(r_sub.cells[5], top=80, bottom=80)
    p_sl = r_sub.cells[0].paragraphs[0]
    p_sl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sl.add_run("Jumlah Subtotal")
    r.font.bold = True
    r.font.size = Pt(9)
    p_sr = r_sub.cells[5].paragraphs[0]
    p_sr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sr.add_run("{{ totals.subtotal_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9)

    # Row 5: PPN
    r_tax = tbl.rows[5]
    mark_row_cant_split(r_tax)
    set_row_height(r_tax, 18)
    r_tax.cells[0].merge(r_tax.cells[4])
    set_cell_margins(r_tax.cells[0], top=80, bottom=80)
    set_cell_margins(r_tax.cells[5], top=80, bottom=80)
    p_tl = r_tax.cells[0].paragraphs[0]
    p_tl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tl.add_run("PPN (11%)")
    r.font.bold = True
    r.font.size = Pt(9)
    p_tr = r_tax.cells[5].paragraphs[0]
    p_tr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tr.add_run("{{ totals.tax_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9)

    # Row 6: Grand Total
    r_gt = tbl.rows[6]
    mark_row_cant_split(r_gt)
    set_row_height(r_gt, 20)
    r_gt.cells[0].merge(r_gt.cells[4])
    set_cell_margins(r_gt.cells[0], top=90, bottom=90)
    set_cell_margins(r_gt.cells[5], top=90, bottom=90)
    set_cell_shading(r_gt.cells[0], "F7FAFC")
    set_cell_shading(r_gt.cells[5], "F7FAFC")
    p_gl = r_gt.cells[0].paragraphs[0]
    p_gl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gl.add_run("Total HPS")
    r.font.bold = True
    r.font.size = Pt(9.5)
    p_gr = r_gt.cells[5].paragraphs[0]
    p_gr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gr.add_run("{{ totals.grand_total_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9.5)

    # Terbilang
    p_tb = doc.add_paragraph()
    p_tb.paragraph_format.space_before = Pt(6)
    p_tb.paragraph_format.space_after = Pt(12)
    p_tb.paragraph_format.keep_with_next = True
    r = p_tb.add_run("Terbilang: ")
    r.font.bold = True
    r.font.size = Pt(9)
    r_tb = p_tb.add_run("{{ totals.terbilang }}")
    r_tb.font.italic = True
    r_tb.font.size = Pt(9)

    # Signatures
    add_signatures_2col(
        doc,
        left_title="Mengetahui,",
        left_role="Kepala Sekolah",
        left_name="{{ school.principal_name }}",
        left_nip="{{ school.principal_nip }}",
        right_title="Pejabat Pengadaan,",
        right_role="{{ school.name }}",
        right_name="{{ officials.pejabat_pengadaan.name }}",
        right_nip="{{ officials.pejabat_pengadaan.nip }}",
        date_str="{{ events.HPS.date_id }}"
    )


def _build_d02_spp(doc: Document):
    add_draft_banner(doc)
    add_school_kop(doc)

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.line_spacing = 1.15
    p_meta.paragraph_format.space_after = Pt(6)
    p_meta.add_run("Nomor    : {{ numbers.D02.doc_number }}\n")
    p_meta.add_run("Sifat    : Biasa\n")
    p_meta.add_run("Lampiran : 1 (satu) Berkas\n")
    p_meta.add_run("Hal      : Permintaan Penawaran Harga Pengadaan\n\n")

    p_to = doc.add_paragraph()
    p_to.paragraph_format.line_spacing = 1.15
    p_to.add_run("Kepada Yth.\n")
    p_to.add_run("Pimpinan {{ company.legal_name }}\n")
    p_to.add_run("Di Tempat\n\n")

    p_body = doc.add_paragraph()
    p_body.paragraph_format.line_spacing = 1.15
    p_body.paragraph_format.space_after = Pt(8)
    p_body.add_run(
        "Dengan hormat,\n"
        "Dalam rangka pelaksanaan kegiatan operasional pada {{ school.name }} Tahun Anggaran {{ package.fiscal_year }}, "
        "kami mohon kesediaan Saudara untuk mengajukan Surat Penawaran Harga untuk daftar kebutuhan barang sebagai berikut:\n"
    )

    col_widths = [0.35, 4.40, 1.00, 1.00]
    tbl = doc.add_table(rows=4, cols=4)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    hdr_row = tbl.rows[0]
    mark_row_header(hdr_row)
    mark_row_cant_split(hdr_row)
    set_row_height(hdr_row, 22)
    for i, h in enumerate(["No", "Nama Barang / Spesifikasi", "Volume", "Satuan"]):
        cell = hdr_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=120, bottom=120)
        set_cell_shading(cell)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9)

    tbl.rows[1].cells[0].text = "{%tr for item in items %}"

    data_row = tbl.rows[2]
    mark_row_cant_split(data_row)
    set_row_height(data_row, 18)
    tags = [
        "{{ item.no }}",
        "{{ item.name }}\n{{ item.spec }}",
        "{{ item.volume }}",
        "{{ item.unit }}"
    ]
    for i, t in enumerate(tags):
        cell = data_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=90, bottom=90)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 2, 3] else WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(t)
        r.font.size = Pt(9)

    tbl.rows[3].cells[0].text = "{%tr endfor %}"

    p_close = doc.add_paragraph()
    p_close.paragraph_format.space_before = Pt(8)
    p_close.paragraph_format.space_after = Pt(12)
    p_close.paragraph_format.keep_with_next = True
    p_close.add_run("Demikian surat permintaan penawaran ini disampaikan, atas perhatian dan kerjasamanya kami ucapkan terima kasih.\n")

    add_signatures_2col(
        doc,
        left_title="",
        left_role="",
        left_name="",
        left_nip="",
        right_title="Pejabat Pengadaan,",
        right_role="{{ school.name }}",
        right_name="{{ officials.pejabat_pengadaan.name }}",
        right_nip="{{ officials.pejabat_pengadaan.nip }}",
        date_str="{{ events.SPP.date_id }}"
    )


def _build_d03_penawaran(doc: Document):
    add_draft_banner(doc)
    add_company_kop(doc)

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.line_spacing = 1.15
    p_meta.paragraph_format.space_after = Pt(6)
    p_meta.add_run("Nomor    : {{ numbers.D03.doc_number }}\n")
    p_meta.add_run("Lampiran : 1 (satu) Berkas\n")
    p_meta.add_run("Hal      : Penawaran Harga Pengadaan Barang\n\n")

    p_to = doc.add_paragraph()
    p_to.paragraph_format.line_spacing = 1.15
    p_to.add_run("Kepada Yth.\n")
    p_to.add_run("Pejabat Pengadaan {{ school.name }}\n")
    p_to.add_run("Di Tempat\n\n")

    p_body = doc.add_paragraph()
    p_body.paragraph_format.line_spacing = 1.15
    p_body.paragraph_format.space_after = Pt(8)
    p_body.add_run(
        "Sehubungan dengan Surat Permintaan Penawaran Harga Nomor: {{ numbers.D02.doc_number }}, "
        "dengan ini kami mengajukan penawaran harga pengadaan barang sebagai berikut:\n"
    )

    col_widths = [0.35, 2.65, 0.55, 0.60, 1.25, 1.35]
    tbl = doc.add_table(rows=7, cols=6)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    headers = ["No", "Nama Barang / Spesifikasi", "Vol", "Sat", "Harga Penawaran (Rp)", "Total (Rp)"]
    hdr_row = tbl.rows[0]
    mark_row_header(hdr_row)
    mark_row_cant_split(hdr_row)
    set_row_height(hdr_row, 22)
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=120, bottom=120)
        set_cell_shading(cell)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9)

    tbl.rows[1].cells[0].text = "{%tr for item in items %}"

    data_row = tbl.rows[2]
    mark_row_cant_split(data_row)
    set_row_height(data_row, 18)
    tags = [
        "{{ item.no }}",
        "{{ item.name }}\n{{ item.spec }}",
        "{{ item.volume }}",
        "{{ item.unit }}",
        "{{ item.offer_price_formatted }}",
        "{{ item.offer_total_formatted }}"
    ]
    for i, t in enumerate(tags):
        cell = data_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=90, bottom=90)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 2, 3] else (WD_ALIGN_PARAGRAPH.RIGHT if i >= 4 else WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run(t)
        r.font.size = Pt(9)

    tbl.rows[3].cells[0].text = "{%tr endfor %}"

    # Subtotal
    r_sub = tbl.rows[4]
    mark_row_cant_split(r_sub)
    set_row_height(r_sub, 18)
    r_sub.cells[0].merge(r_sub.cells[4])
    set_cell_margins(r_sub.cells[0], top=80, bottom=80)
    set_cell_margins(r_sub.cells[5], top=80, bottom=80)
    p_sl = r_sub.cells[0].paragraphs[0]
    p_sl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sl.add_run("Jumlah Subtotal")
    r.font.bold = True
    r.font.size = Pt(9)
    p_sr = r_sub.cells[5].paragraphs[0]
    p_sr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sr.add_run("{{ totals.subtotal_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9)

    # PPN
    r_tax = tbl.rows[5]
    mark_row_cant_split(r_tax)
    set_row_height(r_tax, 18)
    r_tax.cells[0].merge(r_tax.cells[4])
    set_cell_margins(r_tax.cells[0], top=80, bottom=80)
    set_cell_margins(r_tax.cells[5], top=80, bottom=80)
    p_tl = r_tax.cells[0].paragraphs[0]
    p_tl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tl.add_run("PPN (11%)")
    r.font.bold = True
    r.font.size = Pt(9)
    p_tr = r_tax.cells[5].paragraphs[0]
    p_tr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tr.add_run("{{ totals.tax_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9)

    # Grand Total
    r_gt = tbl.rows[6]
    mark_row_cant_split(r_gt)
    set_row_height(r_gt, 20)
    r_gt.cells[0].merge(r_gt.cells[4])
    set_cell_margins(r_gt.cells[0], top=90, bottom=90)
    set_cell_margins(r_gt.cells[5], top=90, bottom=90)
    set_cell_shading(r_gt.cells[0], "F7FAFC")
    set_cell_shading(r_gt.cells[5], "F7FAFC")
    p_gl = r_gt.cells[0].paragraphs[0]
    p_gl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gl.add_run("Total Penawaran")
    r.font.bold = True
    r.font.size = Pt(9.5)
    p_gr = r_gt.cells[5].paragraphs[0]
    p_gr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gr.add_run("{{ totals.grand_total_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9.5)

    p_tb = doc.add_paragraph()
    p_tb.paragraph_format.space_before = Pt(6)
    p_tb.paragraph_format.space_after = Pt(12)
    p_tb.paragraph_format.keep_with_next = True
    r = p_tb.add_run("Terbilang: ")
    r.font.bold = True
    r.font.size = Pt(9)
    r_tb = p_tb.add_run("{{ totals.terbilang }}")
    r_tb.font.italic = True
    r_tb.font.size = Pt(9)

    add_signatures_2col(
        doc,
        left_title="",
        left_role="",
        left_name="",
        left_nip="",
        right_title="Hormat kami,",
        right_role="{{ company.legal_name }}",
        right_name="{{ company.director_name }}",
        right_nip="",
        date_str="{{ events.PENAWARAN.date_id }}"
    )


def _build_d04_negosiasi(doc: Document):
    add_draft_banner(doc)
    add_school_kop(doc)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_title.add_run("BERITA ACARA KLARIFIKASI DAN NEGOSIASI HARGA\n")
    r.font.name = "Arial"
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.underline = True
    p_title.add_run("Nomor: {{ numbers.D04.doc_number }}\n")

    p_narr = doc.add_paragraph()
    p_narr.paragraph_format.line_spacing = 1.15
    p_narr.paragraph_format.space_after = Pt(8)
    p_narr.add_run(
        "{{ events.NEGOSIASI.narrative_id }}, bertempat di {{ events.NEGOSIASI.location }}, "
        "telah dilaksanakan rapat klarifikasi teknis dan negosiasi biaya/harga antara Pejabat Pengadaan {{ school.name }} "
        "dengan {{ company.legal_name }} perihal pengadaan kebutuhan sekolah, dengan rincian kesepakatan sebagai berikut:\n"
    )

    col_widths = [0.35, 2.15, 0.50, 0.55, 1.05, 1.05, 1.10]
    tbl = doc.add_table(rows=7, cols=7)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    headers = ["No", "Nama Barang", "Vol", "Sat", "Penawaran (Rp)", "Negosiasi (Rp)", "Jumlah (Rp)"]
    hdr_row = tbl.rows[0]
    mark_row_header(hdr_row)
    mark_row_cant_split(hdr_row)
    set_row_height(hdr_row, 22)
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=120, bottom=120)
        set_cell_shading(cell)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(8.5)

    tbl.rows[1].cells[0].text = "{%tr for item in items %}"

    data_row = tbl.rows[2]
    mark_row_cant_split(data_row)
    set_row_height(data_row, 18)
    tags = [
        "{{ item.no }}",
        "{{ item.name }}",
        "{{ item.volume }}",
        "{{ item.unit }}",
        "{{ item.offer_price_formatted }}",
        "{{ item.final_price_formatted }}",
        "{{ item.line_total_formatted }}"
    ]
    for i, t in enumerate(tags):
        cell = data_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=90, bottom=90)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 2, 3] else (WD_ALIGN_PARAGRAPH.RIGHT if i >= 4 else WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run(t)
        r.font.size = Pt(8.5)

    tbl.rows[3].cells[0].text = "{%tr endfor %}"

    # Subtotal
    r_sub = tbl.rows[4]
    mark_row_cant_split(r_sub)
    set_row_height(r_sub, 18)
    r_sub.cells[0].merge(r_sub.cells[5])
    set_cell_margins(r_sub.cells[0], top=80, bottom=80)
    set_cell_margins(r_sub.cells[6], top=80, bottom=80)
    p_sl = r_sub.cells[0].paragraphs[0]
    p_sl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sl.add_run("Jumlah Subtotal")
    r.font.bold = True
    r.font.size = Pt(8.5)
    p_sr = r_sub.cells[6].paragraphs[0]
    p_sr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sr.add_run("{{ totals.subtotal_formatted }}")
    r.font.bold = True
    r.font.size = Pt(8.5)

    # PPN
    r_tax = tbl.rows[5]
    mark_row_cant_split(r_tax)
    set_row_height(r_tax, 18)
    r_tax.cells[0].merge(r_tax.cells[5])
    set_cell_margins(r_tax.cells[0], top=80, bottom=80)
    set_cell_margins(r_tax.cells[6], top=80, bottom=80)
    p_tl = r_tax.cells[0].paragraphs[0]
    p_tl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tl.add_run("PPN (11%)")
    r.font.bold = True
    r.font.size = Pt(8.5)
    p_tr = r_tax.cells[6].paragraphs[0]
    p_tr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tr.add_run("{{ totals.tax_formatted }}")
    r.font.bold = True
    r.font.size = Pt(8.5)

    # Grand Total
    r_gt = tbl.rows[6]
    mark_row_cant_split(r_gt)
    set_row_height(r_gt, 20)
    r_gt.cells[0].merge(r_gt.cells[5])
    set_cell_margins(r_gt.cells[0], top=90, bottom=90)
    set_cell_margins(r_gt.cells[6], top=90, bottom=90)
    set_cell_shading(r_gt.cells[0], "F7FAFC")
    set_cell_shading(r_gt.cells[6], "F7FAFC")
    p_gl = r_gt.cells[0].paragraphs[0]
    p_gl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gl.add_run("Grand Total Negosiasi")
    r.font.bold = True
    r.font.size = Pt(9)
    p_gr = r_gt.cells[6].paragraphs[0]
    p_gr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gr.add_run("{{ totals.grand_total_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9)

    p_tb = doc.add_paragraph()
    p_tb.paragraph_format.space_before = Pt(6)
    p_tb.paragraph_format.space_after = Pt(12)
    p_tb.paragraph_format.keep_with_next = True
    r = p_tb.add_run("Terbilang: ")
    r.font.bold = True
    r.font.size = Pt(9)
    r_tb = p_tb.add_run("{{ totals.terbilang }}")
    r_tb.font.italic = True
    r_tb.font.size = Pt(9)

    add_signatures_2col(
        doc,
        left_title="Pihak Pertama,",
        left_role="Pejabat Pengadaan {{ school.name }}",
        left_name="{{ officials.pejabat_pengadaan.name }}",
        left_nip="{{ officials.pejabat_pengadaan.nip }}",
        right_title="Pihak Kedua,",
        right_role="Direktur {{ company.legal_name }}",
        right_name="{{ company.director_name }}",
        right_nip="",
        date_str="{{ events.NEGOSIASI.date_id }}"
    )


def _build_d05_pesanan(doc: Document):
    add_draft_banner(doc)
    add_school_kop(doc)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_title.add_run("SURAT PESANAN (SP)\n")
    r.font.name = "Arial"
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.underline = True
    p_title.add_run("Nomor: {{ numbers.D05.doc_number }}\n")
    p_title.add_run("Tanggal: {{ events.PESANAN.date_id }}\n")

    p_to = doc.add_paragraph()
    p_to.paragraph_format.line_spacing = 1.15
    p_to.paragraph_format.space_after = Pt(8)
    p_to.add_run("Kepada Yth.\n{{ company.legal_name }}\n{{ company.address }}\n\n")
    p_to.add_run("Bersama ini diperintahkan untuk mengirimkan barang pesanan berikut sesuai spesifikasi dan harga yang disepakati:\n")

    col_widths = [0.35, 2.65, 0.55, 0.60, 1.25, 1.35]
    tbl = doc.add_table(rows=7, cols=6)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    headers = ["No", "Nama Barang / Spesifikasi", "Vol", "Sat", "Harga Sepakat (Rp)", "Total (Rp)"]
    hdr_row = tbl.rows[0]
    mark_row_header(hdr_row)
    mark_row_cant_split(hdr_row)
    set_row_height(hdr_row, 22)
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=120, bottom=120)
        set_cell_shading(cell)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9)

    tbl.rows[1].cells[0].text = "{%tr for item in items %}"

    data_row = tbl.rows[2]
    mark_row_cant_split(data_row)
    set_row_height(data_row, 18)
    tags = [
        "{{ item.no }}",
        "{{ item.name }}\n{{ item.spec }}",
        "{{ item.volume }}",
        "{{ item.unit }}",
        "{{ item.final_price_formatted }}",
        "{{ item.line_total_formatted }}"
    ]
    for i, t in enumerate(tags):
        cell = data_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=90, bottom=90)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 2, 3] else (WD_ALIGN_PARAGRAPH.RIGHT if i >= 4 else WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run(t)
        r.font.size = Pt(9)

    tbl.rows[3].cells[0].text = "{%tr endfor %}"

    # Subtotal
    r_sub = tbl.rows[4]
    mark_row_cant_split(r_sub)
    set_row_height(r_sub, 18)
    r_sub.cells[0].merge(r_sub.cells[4])
    set_cell_margins(r_sub.cells[0], top=80, bottom=80)
    set_cell_margins(r_sub.cells[5], top=80, bottom=80)
    p_sl = r_sub.cells[0].paragraphs[0]
    p_sl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sl.add_run("Jumlah Subtotal")
    r.font.bold = True
    r.font.size = Pt(9)
    p_sr = r_sub.cells[5].paragraphs[0]
    p_sr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sr.add_run("{{ totals.subtotal_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9)

    # PPN
    r_tax = tbl.rows[5]
    mark_row_cant_split(r_tax)
    set_row_height(r_tax, 18)
    r_tax.cells[0].merge(r_tax.cells[4])
    set_cell_margins(r_tax.cells[0], top=80, bottom=80)
    set_cell_margins(r_tax.cells[5], top=80, bottom=80)
    p_tl = r_tax.cells[0].paragraphs[0]
    p_tl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tl.add_run("PPN (11%)")
    r.font.bold = True
    r.font.size = Pt(9)
    p_tr = r_tax.cells[5].paragraphs[0]
    p_tr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tr.add_run("{{ totals.tax_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9)

    # Grand Total
    r_gt = tbl.rows[6]
    mark_row_cant_split(r_gt)
    set_row_height(r_gt, 20)
    r_gt.cells[0].merge(r_gt.cells[4])
    set_cell_margins(r_gt.cells[0], top=90, bottom=90)
    set_cell_margins(r_gt.cells[5], top=90, bottom=90)
    set_cell_shading(r_gt.cells[0], "F7FAFC")
    set_cell_shading(r_gt.cells[5], "F7FAFC")
    p_gl = r_gt.cells[0].paragraphs[0]
    p_gl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gl.add_run("Total Pesanan")
    r.font.bold = True
    r.font.size = Pt(9.5)
    p_gr = r_gt.cells[5].paragraphs[0]
    p_gr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gr.add_run("{{ totals.grand_total_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9.5)

    p_tb = doc.add_paragraph()
    p_tb.paragraph_format.space_before = Pt(6)
    p_tb.paragraph_format.space_after = Pt(12)
    p_tb.paragraph_format.keep_with_next = True
    r = p_tb.add_run("Terbilang: ")
    r.font.bold = True
    r.font.size = Pt(9)
    r_tb = p_tb.add_run("{{ totals.terbilang }}")
    r_tb.font.italic = True
    r_tb.font.size = Pt(9)

    add_signatures_2col(
        doc,
        left_title="Menerima dan Menyetujui,",
        left_role="Direktur {{ company.legal_name }}",
        left_name="{{ company.director_name }}",
        left_nip="",
        right_title="Pejabat Pembuat Komitmen / Kepala Sekolah,",
        right_role="{{ school.name }}",
        right_name="{{ school.principal_name }}",
        right_nip="{{ school.principal_nip }}",
        date_str="{{ events.PESANAN.date_id }}"
    )


def _build_d06_faktur(doc: Document):
    add_draft_banner(doc)
    add_company_kop(doc)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_title.add_run("FAKTUR / INVOICE\n")
    r.font.name = "Arial"
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.underline = True

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.line_spacing = 1.15
    p_meta.paragraph_format.space_after = Pt(8)
    p_meta.add_run("Nomor Faktur : {{ numbers.D06.doc_number }}\n")
    p_meta.add_run("Tanggal      : {{ events.FAKTUR.date_id }}\n")
    p_meta.add_run("Kepada Yth.  : Kepala {{ school.name }}\n")
    p_meta.add_run("Alamat       : {{ school.address }}\n")

    col_widths = [0.35, 2.65, 0.55, 0.60, 1.25, 1.35]
    tbl = doc.add_table(rows=7, cols=6)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    headers = ["No", "Deskripsi Barang / Spesifikasi", "Kuantitas", "Satuan", "Harga Satuan (Rp)", "Jumlah (Rp)"]
    hdr_row = tbl.rows[0]
    mark_row_header(hdr_row)
    mark_row_cant_split(hdr_row)
    set_row_height(hdr_row, 22)
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=120, bottom=120)
        set_cell_shading(cell)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9)

    tbl.rows[1].cells[0].text = "{%tr for item in items %}"

    data_row = tbl.rows[2]
    mark_row_cant_split(data_row)
    set_row_height(data_row, 18)
    tags = [
        "{{ item.no }}",
        "{{ item.name }}\n{{ item.spec }}",
        "{{ item.volume }}",
        "{{ item.unit }}",
        "{{ item.final_price_formatted }}",
        "{{ item.line_total_formatted }}"
    ]
    for i, t in enumerate(tags):
        cell = data_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=90, bottom=90)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 2, 3] else (WD_ALIGN_PARAGRAPH.RIGHT if i >= 4 else WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run(t)
        r.font.size = Pt(9)

    tbl.rows[3].cells[0].text = "{%tr endfor %}"

    # Subtotal
    r_sub = tbl.rows[4]
    mark_row_cant_split(r_sub)
    set_row_height(r_sub, 18)
    r_sub.cells[0].merge(r_sub.cells[4])
    set_cell_margins(r_sub.cells[0], top=80, bottom=80)
    set_cell_margins(r_sub.cells[5], top=80, bottom=80)
    p_sl = r_sub.cells[0].paragraphs[0]
    p_sl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sl.add_run("Jumlah Subtotal")
    r.font.bold = True
    r.font.size = Pt(9)
    p_sr = r_sub.cells[5].paragraphs[0]
    p_sr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sr.add_run("{{ totals.subtotal_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9)

    # PPN
    r_tax = tbl.rows[5]
    mark_row_cant_split(r_tax)
    set_row_height(r_tax, 18)
    r_tax.cells[0].merge(r_tax.cells[4])
    set_cell_margins(r_tax.cells[0], top=80, bottom=80)
    set_cell_margins(r_tax.cells[5], top=80, bottom=80)
    p_tl = r_tax.cells[0].paragraphs[0]
    p_tl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tl.add_run("PPN (11%)")
    r.font.bold = True
    r.font.size = Pt(9)
    p_tr = r_tax.cells[5].paragraphs[0]
    p_tr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tr.add_run("{{ totals.tax_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9)

    # Grand Total
    r_gt = tbl.rows[6]
    mark_row_cant_split(r_gt)
    set_row_height(r_gt, 20)
    r_gt.cells[0].merge(r_gt.cells[4])
    set_cell_margins(r_gt.cells[0], top=90, bottom=90)
    set_cell_margins(r_gt.cells[5], top=90, bottom=90)
    set_cell_shading(r_gt.cells[0], "F7FAFC")
    set_cell_shading(r_gt.cells[5], "F7FAFC")
    p_gl = r_gt.cells[0].paragraphs[0]
    p_gl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gl.add_run("Total Pembayaran")
    r.font.bold = True
    r.font.size = Pt(9.5)
    p_gr = r_gt.cells[5].paragraphs[0]
    p_gr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gr.add_run("{{ totals.grand_total_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9.5)

    p_tb = doc.add_paragraph()
    p_tb.paragraph_format.space_before = Pt(6)
    p_tb.paragraph_format.space_after = Pt(8)
    r = p_tb.add_run("Terbilang: ")
    r.font.bold = True
    r.font.size = Pt(9)
    r_tb = p_tb.add_run("{{ totals.terbilang }}")
    r_tb.font.italic = True
    r_tb.font.size = Pt(9)

    p_bank = doc.add_paragraph()
    p_bank.paragraph_format.line_spacing = 1.15
    p_bank.paragraph_format.space_after = Pt(12)
    p_bank.paragraph_format.keep_with_next = True
    p_bank.add_run("Pembayaran dapat ditransfer ke rekening:\n")
    p_bank.add_run("Bank           : {{ company.bank_name }}\n")
    p_bank.add_run("Nomor Rekening : {{ company.bank_account_number }}\n")
    p_bank.add_run("Atas Nama      : {{ company.bank_account_name }}\n")

    add_signatures_2col(
        doc,
        left_title="",
        left_role="",
        left_name="",
        left_nip="",
        right_title="Hormat kami,",
        right_role="{{ company.legal_name }}",
        right_name="{{ company.director_name }}",
        right_nip="",
        date_str="{{ events.FAKTUR.date_id }}"
    )


def _build_d07_kwitansi(doc: Document):
    add_draft_banner(doc)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_title.add_run("KWITANSI PEMBAYARAN\n")
    r.font.name = "Arial"
    r.font.size = Pt(13)
    r.font.bold = True
    r.underline = True
    p_title.add_run("Nomor: {{ numbers.D07.doc_number }}\n\n")

    # Formal bordered receipt box
    tbl = doc.add_table(rows=4, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl, color="718096", sz="6")

    set_cell_width(tbl.rows[0].cells[0], 2.2)
    set_cell_width(tbl.rows[0].cells[1], 4.5)
    set_cell_width(tbl.rows[1].cells[0], 2.2)
    set_cell_width(tbl.rows[1].cells[1], 4.5)
    set_cell_width(tbl.rows[2].cells[0], 2.2)
    set_cell_width(tbl.rows[2].cells[1], 4.5)
    set_cell_width(tbl.rows[3].cells[0], 2.2)
    set_cell_width(tbl.rows[3].cells[1], 4.5)

    for row in tbl.rows:
        set_row_height(row, 24)
        for c in row.cells:
            set_cell_margins(c, top=100, bottom=100, left=120, right=120)
            set_cell_v_align(c, "center")

    tbl.rows[0].cells[0].paragraphs[0].add_run("Sudah Terima Dari").font.bold = True
    tbl.rows[0].cells[1].paragraphs[0].add_run("Kepala {{ school.name }}")

    tbl.rows[1].cells[0].paragraphs[0].add_run("Uang Sejumlah").font.bold = True
    r_tb = tbl.rows[1].cells[1].paragraphs[0].add_run("{{ totals.terbilang }}")
    r_tb.font.italic = True
    r_tb.font.bold = True

    tbl.rows[2].cells[0].paragraphs[0].add_run("Untuk Pembayaran").font.bold = True
    tbl.rows[2].cells[1].paragraphs[0].add_run(
        "Pembayaran Pengadaan Kebutuhan Operasional Sekolah Tahun Anggaran {{ package.fiscal_year }}"
    )

    tbl.rows[3].cells[0].paragraphs[0].add_run("Jumlah Uang").font.bold = True
    r_tot = tbl.rows[3].cells[1].paragraphs[0].add_run("Rp {{ totals.grand_total_formatted }}")
    r_tot.font.bold = True
    r_tot.font.size = Pt(11)

    p_spc = doc.add_paragraph()
    p_spc.paragraph_format.space_before = Pt(12)
    p_spc.paragraph_format.keep_with_next = True

    add_signatures_2col(
        doc,
        left_title="Setuju Dibayar,",
        left_role="Kepala Sekolah {{ school.name }}",
        left_name="{{ school.principal_name }}",
        left_nip="{{ school.principal_nip }}",
        right_title="Yang Menerima,",
        right_role="Direktur {{ company.legal_name }}",
        right_name="{{ company.director_name }}",
        right_nip="",
        date_str="{{ events.KWITANSI.date_id }}"
    )


def _build_d08_surat_jalan(doc: Document):
    add_draft_banner(doc)
    add_company_kop(doc)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_title.add_run("SURAT JALAN / PENGIRIMAN BARANG\n")
    r.font.name = "Arial"
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.underline = True

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.line_spacing = 1.15
    p_meta.paragraph_format.space_after = Pt(8)
    p_meta.add_run("Nomor   : {{ numbers.D08.doc_number }}\n")
    p_meta.add_run("Tanggal : {{ events.SURAT_JALAN.date_id }}\n")
    p_meta.add_run("Kepada  : Pengurus Barang / Kepala {{ school.name }}\n")
    p_meta.add_run("Alamat  : {{ school.address }}\n")

    col_widths = [0.35, 3.40, 0.90, 0.90, 1.20]
    tbl = doc.add_table(rows=4, cols=5)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    headers = ["No", "Nama Barang / Spesifikasi", "Kuantitas", "Satuan", "Kondisi Barang"]
    hdr_row = tbl.rows[0]
    mark_row_header(hdr_row)
    mark_row_cant_split(hdr_row)
    set_row_height(hdr_row, 22)
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=120, bottom=120)
        set_cell_shading(cell)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9)

    tbl.rows[1].cells[0].text = "{%tr for item in items %}"

    data_row = tbl.rows[2]
    mark_row_cant_split(data_row)
    set_row_height(data_row, 18)
    tags = [
        "{{ item.no }}",
        "{{ item.name }}\n{{ item.spec }}",
        "{{ item.volume }}",
        "{{ item.unit }}",
        "{{ item.condition }}"
    ]
    for i, t in enumerate(tags):
        cell = data_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=90, bottom=90)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 2, 3, 4] else WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(t)
        r.font.size = Pt(9)

    tbl.rows[3].cells[0].text = "{%tr endfor %}"

    p_spc = doc.add_paragraph()
    p_spc.paragraph_format.space_before = Pt(12)
    p_spc.paragraph_format.keep_with_next = True

    add_signatures_2col(
        doc,
        left_title="Yang Menerima,",
        left_role="Pengurus Barang {{ school.name }}",
        left_name="{{ officials.pengurus_barang.name }}",
        left_nip="{{ officials.pengurus_barang.nip }}",
        right_title="Yang Menyerahkan,",
        right_role="Pengirim {{ company.legal_name }}",
        right_name="{{ company.director_name }}",
        right_nip="",
        date_str="{{ events.SURAT_JALAN.date_id }}"
    )


def _build_d09_bapb(doc: Document):
    add_draft_banner(doc)
    add_school_kop(doc)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_title.add_run("BERITA ACARA PEMERIKSAAN HASIL PEKERJAAN (BAPB)\n")
    r.font.name = "Arial"
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.underline = True
    p_title.add_run("Nomor: {{ numbers.D09.doc_number }}\n")

    p_narr = doc.add_paragraph()
    p_narr.paragraph_format.line_spacing = 1.15
    p_narr.paragraph_format.space_after = Pt(8)
    p_narr.add_run(
        "{{ events.BAPB.narrative_id }}, Panitia / Pejabat Penerima Hasil Pekerjaan (PPHP) "
        "pada {{ school.name }} telah melakukan pemeriksaan fisik terhadap barang yang diserahkan oleh {{ company.legal_name }} "
        "berdasarkan Surat Pesanan Nomor: {{ numbers.D05.doc_number }}. Hasil pemeriksaan dicatat sebagai berikut:\n"
    )

    col_widths = [0.35, 3.40, 0.90, 0.90, 1.20]
    tbl = doc.add_table(rows=4, cols=5)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    headers = ["No", "Nama Barang / Spesifikasi", "Kuantitas", "Satuan", "Hasil Pemeriksaan"]
    hdr_row = tbl.rows[0]
    mark_row_header(hdr_row)
    mark_row_cant_split(hdr_row)
    set_row_height(hdr_row, 22)
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=120, bottom=120)
        set_cell_shading(cell)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9)

    tbl.rows[1].cells[0].text = "{%tr for item in items %}"

    data_row = tbl.rows[2]
    mark_row_cant_split(data_row)
    set_row_height(data_row, 18)
    tags = [
        "{{ item.no }}",
        "{{ item.name }}\n{{ item.spec }}",
        "{{ item.volume }}",
        "{{ item.unit }}",
        "Baik / Sesuai"
    ]
    for i, t in enumerate(tags):
        cell = data_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=90, bottom=90)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 2, 3, 4] else WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(t)
        r.font.size = Pt(9)

    tbl.rows[3].cells[0].text = "{%tr endfor %}"

    p_conc = doc.add_paragraph()
    p_conc.paragraph_format.space_before = Pt(8)
    p_conc.paragraph_format.space_after = Pt(8)
    p_conc.paragraph_format.keep_with_next = True
    p_conc.add_run("Kesimpulan: Seluruh barang yang dikirim dalam kondisi 100% baik, lengkap, dan memenuhi spesifikasi teknis yang disepakati.\n")

    add_signatures_pphp(
        doc,
        school_name_var="{{ school.name }}",
        pphp_ketua_name_var="{{ officials.pphp_ketua.name }}",
        pphp_ketua_nip_var="{{ officials.pphp_ketua.nip }}",
        pphp_sekre_name_var="{{ officials.pphp_sekretaris.name }}",
        pphp_sekre_nip_var="{{ officials.pphp_sekretaris.nip }}",
        pphp_anggo_name_var="{{ officials.pphp_anggota.name }}",
        pphp_anggo_nip_var="{{ officials.pphp_anggota.nip }}",
        company_name_var="{{ company.legal_name }}",
        director_name_var="{{ company.director_name }}"
    )


def _build_d10_bast(doc: Document):
    add_draft_banner(doc)
    add_school_kop(doc)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_title.add_run("BERITA ACARA SERAH TERIMA HASIL PEKERJAAN (BAST)\n")
    r.font.name = "Arial"
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.underline = True
    p_title.add_run("Nomor: {{ numbers.D10.doc_number }}\n")

    p_narr = doc.add_paragraph()
    p_narr.paragraph_format.line_spacing = 1.2
    p_narr.paragraph_format.space_after = Pt(12)
    p_narr.paragraph_format.keep_with_next = True
    p_narr.add_run(
        "{{ events.BAST.narrative_id }}, bertempat di {{ events.BAST.location }}, yang bertanda tangan di bawah ini:\n"
        "1. Nama     : {{ company.director_name }}\n"
        "   Jabatan  : Direktur {{ company.legal_name }}\n"
        "   Alamat   : {{ company.address }}\n"
        "   Selanjutnya disebut sebagai PIHAK PERTAMA (Penyedia).\n\n"
        "2. Nama     : {{ school.principal_name }}\n"
        "   NIP      : {{ school.principal_nip }}\n"
        "   Jabatan  : Kepala {{ school.name }}\n"
        "   Alamat   : {{ school.address }}\n"
        "   Selanjutnya disebut sebagai PIHAK KEDUA (Pihak Sekolah).\n\n"
        "Kedua belah pihak telah sepakat mengadakan serah terima hasil pekerjaan dengan ketentuan:\n"
        "- PIHAK PERTAMA telah menyerahkan seluruh pekerjaan pengadaan barang kepada PIHAK KEDUA "
        "sesuai dengan Surat Pesanan Nomor: {{ numbers.D05.doc_number }} dan Berita Acara Pemeriksaan Hasil Pekerjaan Nomor: {{ numbers.D09.doc_number }}.\n"
        "- PIHAK KEDUA telah menerima penyerahan barang tersebut dalam jumlah lengkap dan kondisi baik.\n"
    )

    add_signatures_2col(
        doc,
        left_title="PIHAK PERTAMA (Penyedia),",
        left_role="{{ company.legal_name }}",
        left_name="{{ company.director_name }}",
        left_nip="",
        right_title="PIHAK KEDUA,",
        right_role="Kepala Sekolah {{ school.name }}",
        right_name="{{ school.principal_name }}",
        right_nip="{{ school.principal_nip }}",
        date_str="{{ events.BAST.date_id }}"
    )


def _build_d11_bapp(doc: Document):
    add_draft_banner(doc)
    add_school_kop(doc)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_title.add_run("BERITA ACARA PEMBAYARAN (BAPP)\n")
    r.font.name = "Arial"
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.underline = True
    p_title.add_run("Nomor: {{ numbers.D11.doc_number }}\n")

    p_narr = doc.add_paragraph()
    p_narr.paragraph_format.line_spacing = 1.2
    p_narr.paragraph_format.space_after = Pt(8)
    p_narr.add_run(
        "{{ events.BAPP.narrative_id }}, bertempat di {{ events.BAPP.location }}, "
        "berdasarkan Berita Acara Serah Terima (BAST) Nomor: {{ numbers.D10.doc_number }} "
        "dan Surat Pesanan Nomor: {{ numbers.D05.doc_number }}, dengan ini disepakati pembayaran prestasi pekerjaan dengan rincian:\n"
    )

    # Formal summary table
    tbl = doc.add_table(rows=3, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)
    set_cell_width(tbl.rows[0].cells[0], 4.2)
    set_cell_width(tbl.rows[0].cells[1], 2.5)
    set_cell_width(tbl.rows[1].cells[0], 4.2)
    set_cell_width(tbl.rows[1].cells[1], 2.5)
    set_cell_width(tbl.rows[2].cells[0], 4.2)
    set_cell_width(tbl.rows[2].cells[1], 2.5)

    for r in tbl.rows:
        set_row_height(r, 20)
        set_cell_margins(r.cells[0], top=80, bottom=80, left=100, right=100)
        set_cell_margins(r.cells[1], top=80, bottom=80, left=100, right=100)
        set_cell_v_align(r.cells[0], "center")
        set_cell_v_align(r.cells[1], "center")

    tbl.rows[0].cells[0].paragraphs[0].add_run("1. Jumlah Nilai Tagihan (Subtotal)")
    tbl.rows[0].cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    tbl.rows[0].cells[1].paragraphs[0].add_run("Rp {{ totals.subtotal_formatted }}")

    tbl.rows[1].cells[0].paragraphs[0].add_run("2. Pajak Pertambahan Nilai (PPN 11%)")
    tbl.rows[1].cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    tbl.rows[1].cells[1].paragraphs[0].add_run("Rp {{ totals.tax_formatted }}")

    tbl.rows[2].cells[0].paragraphs[0].add_run("3. Jumlah Bersih yang Harus Dibayarkan").font.bold = True
    tbl.rows[2].cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_g = tbl.rows[2].cells[1].paragraphs[0].add_run("Rp {{ totals.grand_total_formatted }}")
    r_g.font.bold = True
    set_cell_shading(tbl.rows[2].cells[0], "F7FAFC")
    set_cell_shading(tbl.rows[2].cells[1], "F7FAFC")

    p_tb = doc.add_paragraph()
    p_tb.paragraph_format.space_before = Pt(6)
    p_tb.paragraph_format.space_after = Pt(12)
    p_tb.paragraph_format.keep_with_next = True
    r = p_tb.add_run("Terbilang: ")
    r.font.bold = True
    r.font.size = Pt(9)
    r_tb = p_tb.add_run("{{ totals.terbilang }}")
    r_tb.font.italic = True
    r_tb.font.size = Pt(9)

    add_signatures_2col(
        doc,
        left_title="PIHAK PERTAMA (Penyedia),",
        left_role="{{ company.legal_name }}",
        left_name="{{ company.director_name }}",
        left_nip="",
        right_title="PIHAK KEDUA,",
        right_role="Kepala Sekolah {{ school.name }}",
        right_name="{{ school.principal_name }}",
        right_nip="{{ school.principal_nip }}",
        date_str="{{ events.BAPP.date_id }}"
    )


def _build_d12_lamp_bapp(doc: Document):
    add_draft_banner(doc)
    add_school_kop(doc)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_title.add_run("LAMPIRAN BERITA ACARA PEMBAYARAN\n")
    r.font.name = "Arial"
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.underline = True
    p_title.add_run("Nomor: {{ numbers.D12.doc_number }}\n")

    col_widths = [0.35, 2.65, 0.55, 0.60, 1.25, 1.35]
    tbl = doc.add_table(rows=7, cols=6)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    headers = ["No", "Nama Barang / Spesifikasi", "Vol", "Sat", "Harga Satuan (Rp)", "Total (Rp)"]
    hdr_row = tbl.rows[0]
    mark_row_header(hdr_row)
    mark_row_cant_split(hdr_row)
    set_row_height(hdr_row, 22)
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=120, bottom=120)
        set_cell_shading(cell)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9)

    tbl.rows[1].cells[0].text = "{%tr for item in items %}"

    data_row = tbl.rows[2]
    mark_row_cant_split(data_row)
    set_row_height(data_row, 18)
    tags = [
        "{{ item.no }}",
        "{{ item.name }}\n{{ item.spec }}",
        "{{ item.volume }}",
        "{{ item.unit }}",
        "{{ item.final_price_formatted }}",
        "{{ item.line_total_formatted }}"
    ]
    for i, t in enumerate(tags):
        cell = data_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=90, bottom=90)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 2, 3] else (WD_ALIGN_PARAGRAPH.RIGHT if i >= 4 else WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run(t)
        r.font.size = Pt(9)

    tbl.rows[3].cells[0].text = "{%tr endfor %}"

    # Subtotal
    r_sub = tbl.rows[4]
    mark_row_cant_split(r_sub)
    set_row_height(r_sub, 18)
    r_sub.cells[0].merge(r_sub.cells[4])
    set_cell_margins(r_sub.cells[0], top=80, bottom=80)
    set_cell_margins(r_sub.cells[5], top=80, bottom=80)
    p_sl = r_sub.cells[0].paragraphs[0]
    p_sl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sl.add_run("Jumlah Subtotal")
    r.font.bold = True
    r.font.size = Pt(9)
    p_sr = r_sub.cells[5].paragraphs[0]
    p_sr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_sr.add_run("{{ totals.subtotal_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9)

    # PPN
    r_tax = tbl.rows[5]
    mark_row_cant_split(r_tax)
    set_row_height(r_tax, 18)
    r_tax.cells[0].merge(r_tax.cells[4])
    set_cell_margins(r_tax.cells[0], top=80, bottom=80)
    set_cell_margins(r_tax.cells[5], top=80, bottom=80)
    p_tl = r_tax.cells[0].paragraphs[0]
    p_tl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tl.add_run("PPN (11%)")
    r.font.bold = True
    r.font.size = Pt(9)
    p_tr = r_tax.cells[5].paragraphs[0]
    p_tr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_tr.add_run("{{ totals.tax_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9)

    # Grand Total
    r_gt = tbl.rows[6]
    mark_row_cant_split(r_gt)
    set_row_height(r_gt, 20)
    r_gt.cells[0].merge(r_gt.cells[4])
    set_cell_margins(r_gt.cells[0], top=90, bottom=90)
    set_cell_margins(r_gt.cells[5], top=90, bottom=90)
    set_cell_shading(r_gt.cells[0], "F7FAFC")
    set_cell_shading(r_gt.cells[5], "F7FAFC")
    p_gl = r_gt.cells[0].paragraphs[0]
    p_gl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gl.add_run("Grand Total")
    r.font.bold = True
    r.font.size = Pt(9.5)
    p_gr = r_gt.cells[5].paragraphs[0]
    p_gr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p_gr.add_run("{{ totals.grand_total_formatted }}")
    r.font.bold = True
    r.font.size = Pt(9.5)

    p_tb = doc.add_paragraph()
    p_tb.paragraph_format.space_before = Pt(6)
    p_tb.paragraph_format.space_after = Pt(12)
    p_tb.paragraph_format.keep_with_next = True
    r = p_tb.add_run("Terbilang: ")
    r.font.bold = True
    r.font.size = Pt(9)
    r_tb = p_tb.add_run("{{ totals.terbilang }}")
    r_tb.font.italic = True
    r_tb.font.size = Pt(9)

    add_signatures_2col(
        doc,
        left_title="Pihak Penyedia,",
        left_role="{{ company.legal_name }}",
        left_name="{{ company.director_name }}",
        left_nip="",
        right_title="Mengetahui,",
        right_role="Kepala Sekolah {{ school.name }}",
        right_name="{{ school.principal_name }}",
        right_nip="{{ school.principal_nip }}",
        date_str="{{ events.BAPP.date_id }}"
    )


def _build_d13_bast_rekanan(doc: Document):
    add_draft_banner(doc)
    add_company_kop(doc)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_title.add_run("BERITA ACARA SERAH TERIMA REKANAN\n")
    r.font.name = "Arial"
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.underline = True
    p_title.add_run("Nomor: {{ numbers.D13.doc_number }}\n")
    p_title.add_run("Tanggal: {{ events.BAST_REKANAN.date_id }}\n\n")

    p_narr = doc.add_paragraph()
    p_narr.paragraph_format.line_spacing = 1.15
    p_narr.paragraph_format.space_after = Pt(8)
    p_narr.add_run(
        "Pada hari ini bertempat di {{ school.name }}, kami yang bertanda tangan di bawah ini:\n"
        "Nama: {{ company.director_name }}, Selaku Direktur {{ company.legal_name }}, menyerahkan barang pesanan sesuai "
        "Surat Pesanan Nomor: {{ numbers.D05.doc_number }} kepada pihak {{ school.name }} dengan kondisi baik dan lengkap sebagai berikut:\n"
    )

    col_widths = [0.35, 3.40, 0.90, 0.90, 1.20]
    tbl = doc.add_table(rows=4, cols=5)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    headers = ["No", "Nama Barang / Spesifikasi", "Volume", "Satuan", "Kondisi"]
    hdr_row = tbl.rows[0]
    mark_row_header(hdr_row)
    mark_row_cant_split(hdr_row)
    set_row_height(hdr_row, 22)
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=120, bottom=120)
        set_cell_shading(cell)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9)

    tbl.rows[1].cells[0].text = "{%tr for item in items %}"

    data_row = tbl.rows[2]
    mark_row_cant_split(data_row)
    set_row_height(data_row, 18)
    tags = [
        "{{ item.no }}",
        "{{ item.name }}\n{{ item.spec }}",
        "{{ item.volume }}",
        "{{ item.unit }}",
        "{{ item.condition }}"
    ]
    for i, t in enumerate(tags):
        cell = data_row.cells[i]
        set_cell_width(cell, col_widths[i])
        set_cell_margins(cell, top=90, bottom=90)
        set_cell_v_align(cell, "center")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 2, 3, 4] else WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(t)
        r.font.size = Pt(9)

    tbl.rows[3].cells[0].text = "{%tr endfor %}"

    p_spc = doc.add_paragraph()
    p_spc.paragraph_format.space_before = Pt(12)
    p_spc.paragraph_format.keep_with_next = True

    add_signatures_2col(
        doc,
        left_title="Yang Menyerahkan,",
        left_role="Direktur {{ company.legal_name }}",
        left_name="{{ company.director_name }}",
        left_nip="",
        right_title="Yang Menerima,",
        right_role="Kepala Sekolah {{ school.name }}",
        right_name="{{ school.principal_name }}",
        right_nip="{{ school.principal_nip }}",
        date_str="{{ events.BAST_REKANAN.date_id }}"
    )


if __name__ == "__main__":
    created = build_all_templates()
    print(f"Generated {len(created)} Word templates in {TEMPLATES_DIR}")
