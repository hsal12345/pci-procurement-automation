"""Template Registry & Dynamic Token Processor service (FR-03 & UC-03).

Validates Jinja2/docxtpl variable syntax inside .docx templates, detects unknown
or missing required tokens (UC-03 Flow 4a), stores versioned template files
without mutating historical approved artifacts, and renders sample preview
simulations (UC-03 Step 5).
"""
import hashlib
import io
import re
import zipfile
from datetime import date
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from jinja2 import Environment, TemplateSyntaxError
from docxtpl import DocxTemplate
from docx import Document

from app.services.export.context_builder import build_generation_context
from app.services.export.docx_generator import DOCUMENT_MAP, ACTIVE_TEMPLATES_DIR
from app.services.export.template_builder import TEMPLATES_DIR, build_all_templates

TEMPLATES_VERSIONS_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "templates" / "versions"

# Root variable keys provided by build_generation_context + docxtpl loop variables
KNOWN_ROOT_TOKENS = {
    "is_draft",
    "draft_banner",
    "package",
    "school",
    "company",
    "officials",
    "events",
    "numbers",
    "items",
    "item",
    "totals",
    "school_snapshot",
    "company_snapshot",
    "tax_policy_snapshot",
    "officials_snapshot",
    "lines",
    "subtotal",
    "tax_total",
    "grand_total",
    "terbilang_grand_total",
    "school_has_letterhead_image",
    "school_letterhead_image",
    "company_has_letterhead_image",
    "company_letterhead_image",
    # Indonesian aliases per FR-03
    "nama_sekolah",
    "npsn_sekolah",
    "nama_perusahaan",
    "nilai_kontrak",
    "terbilang_kontrak",
    "nomor_paket",
    "tahun_anggaran",
    "triwulan",
    "loop",  # Jinja2 built-in loop helper
}


def build_sample_context(is_draft: bool = False) -> Dict[str, Any]:
    """Creates a realistic sample transaction context for UC-03 Step 5 simulation preview."""
    sample_revision = {
        "revision_number": 1,
        "package_number": "PKG/2026/Q2/SIMULASI",
        "fiscal_year": 2026,
        "quarter": 2,
        "school_snapshot": {
            "name": "SD NEGERI KEBON KOSONG 09",
            "npsn": "20101234",
            "address": "Jl. Dakota V No. 12",
            "subdistrict": "Kemayoran",
            "city": "Jakarta Pusat",
            "province": "DKI Jakarta",
            "postal_code": "10630",
            "phone": "021-4240000",
            "email": "sdnkebonkosong09@jakarta.go.id",
        },
        "company_snapshot": {
            "legal_name": "CV. PUSTAKA CEMERLANG INDONESIA",
            "director_name": "Bambang Solifian",
            "address": "Wisma Mitra Sunter Unit 3-03, Jl. Yos Sudarso Kav. 89",
            "city": "Jakarta Utara",
            "phone": "021-65301234",
            "npwp": "02.456.789.0-034.000",
            "bank_name": "Bank DKI",
            "bank_account_number": "10121008899",
            "bank_account_name": "CV. Pustaka Cemerlang Indonesia",
        },
        "officials_snapshot": [
            {"role": "KEPALA_SEKOLAH", "name": "Drs. H. Mulyadi, M.Pd", "nip": "196501011990031005", "position": "Kepala Sekolah"},
            {"role": "BENDAHARA", "name": "Siti Rahmawati, S.Pd", "nip": "198005122008012015", "position": "Bendahara BOS"},
            {"role": "PENGURUS_BARANG", "name": "Sulistiawati", "nip": "197909092022212008", "position": "Pengurus Barang"},
        ],
        "lines": [
            {
                "line_number": 1,
                "original_description": "Buku Teks Pendamping Bahasa Indonesia SD Kelas 4",
                "confirmed_description": "Buku Teks Pendamping Bahasa Indonesia SD Kelas 4",
                "specification": "HVS 70gr Full Color",
                "quantity": 100,
                "unit": "Eks",
                "hps_unit_price": 45000,
                "offer_unit_price": 44000,
                "final_unit_price": 43000,
                "discount": 0,
                "line_total": 4300000,
                "condition": "BAIK",
            },
            {
                "line_number": 2,
                "original_description": "Kertas HVS A4 80 gram",
                "confirmed_description": "Kertas HVS A4 80 gram Sinar Dunia",
                "specification": "A4 80gsm 500 lembar/rim",
                "quantity": 10,
                "unit": "Rim",
                "hps_unit_price": 58000,
                "offer_unit_price": 56000,
                "final_unit_price": 55000,
                "discount": 0,
                "line_total": 550000,
                "condition": "BAIK",
            },
        ],
        "events": [
            {"event_code": code, "event_date": date(2026, 4, 15).isoformat(), "location": "Jakarta"}
            for code in ["HPS", "SPP", "PENAWARAN", "NEGOSIASI", "PESANAN", "SURAT_JALAN", "BAPB", "BAST", "BAST_REKANAN", "BAPP", "FAKTUR", "KWITANSI"]
        ],
        "numbers": [
            {"doc_code": f"D{i:02d}", "doc_number": f"00{i}/SPJ/IV/2026", "issuer": "SCHOOL" if i in [1,2,4,5,7,9,10,11,12] else "COMPANY"}
            for i in range(1, 14)
        ],
        "subtotal": 4850000,
        "tax_total": 533500,
        "grand_total": 5383500,
    }
    return build_generation_context(sample_revision, is_draft=is_draft)


def extract_and_validate_docx_bytes(
    doc_code: str,
    filename: str,
    file_bytes: bytes,
    required_tokens: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Parses .docx zip archive, checks Jinja2 syntax and token validity (UC-03 Step 4 & 4a)."""
    required_tokens = required_tokens or []
    syntax_errors: List[str] = []
    detected_tokens_set = set()
    raw_expressions: List[str] = []

    if not zipfile.is_zipfile(io.BytesIO(file_bytes)):
        return {
            "doc_code": doc_code,
            "filename": filename,
            "is_valid": False,
            "detected_tokens": [],
            "missing_required_tokens": required_tokens,
            "unrecognized_tokens": [],
            "syntax_errors": ["Berkas bukan dokumen .docx yang valid (bukan arsip OOXML)."],
            "message": "Format berkas tidak valid. Harap unggah berkas Microsoft Word (.docx).",
        }

    env = Environment()
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
            xml_files = [n for n in zf.namelist() if n.startswith("word/") and n.endswith(".xml")]
            if "word/document.xml" not in xml_files:
                return {
                    "doc_code": doc_code,
                    "filename": filename,
                    "is_valid": False,
                    "detected_tokens": [],
                    "missing_required_tokens": required_tokens,
                    "unrecognized_tokens": [],
                    "syntax_errors": ["Berkas .docx tidak memiliki word/document.xml."],
                    "message": "Struktur dokumen Word rusak atau kosong.",
                }

            for name in xml_files:
                raw_xml = zf.read(name).decode("utf-8", errors="ignore")
                clean_text = re.sub(r"<[^>]+>", "", raw_xml)
                # Normalize docxtpl custom block tags for Jinja2 syntax verification
                normalized = re.sub(r"\{%(tr|tc|p|r)\s+", "{% ", clean_text)
                try:
                    env.parse(normalized)
                except TemplateSyntaxError as exc:
                    syntax_errors.append(f"{name} (baris {exc.lineno}): {exc.message}")

                for match in re.findall(r"\{\{\s*([^}]+?)\s*\}\}", clean_text):
                    expr = match.strip()
                    raw_expressions.append(expr)
                    # Extract primary variable identifier (before filters/operators)
                    var_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_.]*)", expr)
                    if var_match:
                        detected_tokens_set.add(var_match.group(1))
    except Exception as exc:
        syntax_errors.append(f"Gagal membaca struktur XML dokumen: {exc}")

    detected_tokens = sorted(detected_tokens_set)

    # Check unrecognized root tokens (UC-03 Flow 4a)
    unrecognized_tokens: List[str] = []
    for tok in detected_tokens:
        root_name = tok.split(".")[0]
        if root_name not in KNOWN_ROOT_TOKENS:
            unrecognized_tokens.append(tok)

    # Check missing required tokens (only warn if none of the aliases match)
    missing_required = []
    for req in required_tokens:
        if req not in detected_tokens and not any(d == req or d.startswith(f"{req}.") for d in detected_tokens):
            missing_required.append(req)

    is_valid = len(syntax_errors) == 0 and len(unrecognized_tokens) == 0

    if syntax_errors:
        message = "Gagal validasi sintaks Jinja2/docxtpl (UC-03 Alur 4a): Periksa kurung kurawal atau tag loop pada template."
    elif unrecognized_tokens:
        message = (
            f"Penanda Variabel Tidak Dikenali (UC-03 Alur 4a): Ditemukan {len(unrecognized_tokens)} "
            f"token tidak terdaftar ({', '.join(unrecognized_tokens[:5])}). Template ditolak untuk diaktifkan."
        )
    else:
        message = f"Validasi berhasil. Ditemukan {len(detected_tokens)} token variabel valid."

    return {
        "doc_code": doc_code,
        "filename": filename,
        "is_valid": is_valid,
        "detected_tokens": detected_tokens,
        "missing_required_tokens": missing_required,
        "unrecognized_tokens": unrecognized_tokens,
        "syntax_errors": syntax_errors,
        "message": message,
    }


def save_and_activate_template(doc_code: str, filename: str, file_bytes: bytes, new_version: int) -> Tuple[Path, str]:
    """Saves versioned copy and copies to active templates directory without modifying past artifacts."""
    if doc_code not in DOCUMENT_MAP:
        raise ValueError(f"Kode dokumen '{doc_code}' tidak dikenal.")
    tmpl_filename, _ = DOCUMENT_MAP[doc_code]

    TEMPLATES_VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    versioned_path = TEMPLATES_VERSIONS_DIR / f"{doc_code}_v{new_version}_{tmpl_filename}"
    active_path = ACTIVE_TEMPLATES_DIR / tmpl_filename

    versioned_path.write_bytes(file_bytes)
    active_path.write_bytes(file_bytes)
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    return active_path, sha256_hash


def get_effective_template_path(doc_code: str) -> Path:
    if doc_code not in DOCUMENT_MAP:
        raise ValueError(f"Kode dokumen '{doc_code}' tidak dikenal.")
    tmpl_filename, _ = DOCUMENT_MAP[doc_code]
    custom_path = ACTIVE_TEMPLATES_DIR / tmpl_filename
    if custom_path.is_file():
        return custom_path
    default_path = TEMPLATES_DIR / tmpl_filename
    if not default_path.is_file():
        build_all_templates()
    return default_path


def render_simulation_preview(doc_code: str, custom_bytes: Optional[bytes] = None) -> Dict[str, Any]:
    """Renders a simulation preview of the template with sample context (UC-03 Step 5)."""
    sample_ctx = build_sample_context(is_draft=False)
    sample_ctx["school_has_letterhead_image"] = False
    sample_ctx["school_letterhead_image"] = None
    sample_ctx["company_has_letterhead_image"] = False
    sample_ctx["company_letterhead_image"] = None

    if custom_bytes is not None:
        doc = DocxTemplate(io.BytesIO(custom_bytes))
    else:
        tmpl_path = get_effective_template_path(doc_code)
        doc = DocxTemplate(str(tmpl_path))

    doc.render(sample_ctx)
    out_buf = io.BytesIO()
    doc.save(out_buf)
    out_buf.seek(0)

    rendered_doc = Document(out_buf)
    paragraphs = [p.text.strip() for p in rendered_doc.paragraphs if p.text and p.text.strip()]
    tables_preview: List[List[List[str]]] = []
    for tbl in rendered_doc.tables:
        rows_data = []
        for row in tbl.rows[:15]:
            rows_data.append([cell.text.strip().replace("\n", " | ") for cell in row.cells])
        if rows_data:
            tables_preview.append(rows_data)

    return {
        "doc_code": doc_code,
        "sample_context_summary": {
            "nama_sekolah": sample_ctx["nama_sekolah"],
            "nama_perusahaan": sample_ctx["nama_perusahaan"],
            "nilai_kontrak": sample_ctx["nilai_kontrak"],
            "terbilang_kontrak": sample_ctx["terbilang_kontrak"],
            "nomor_paket": sample_ctx["nomor_paket"],
        },
        "paragraphs": paragraphs[:40],
        "tables": tables_preview[:5],
        "docx_bytes": out_buf.getvalue(),
    }
