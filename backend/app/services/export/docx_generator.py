"""Document generator for rendering all 13 official procurement & SPJ documents
as editable, high-fidelity Microsoft Word (.docx) files using docxtpl.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Inches

from app.services.export.template_builder import (
    TEMPLATES_DIR,
    build_all_templates,
)


def resolve_letterhead_image_path(path_str: Optional[str]) -> Optional[Path]:
    """Resolves local absolute or relative storage path of uploaded letterhead image."""
    if not path_str:
        return None
    p = Path(path_str)
    if p.is_file():
        return p
    clean = path_str.lstrip("/\\")
    backend_dir = Path(__file__).resolve().parent.parent.parent
    candidate = backend_dir / clean
    if candidate.is_file():
        return candidate
    ws_candidate = backend_dir.parent / clean
    if ws_candidate.is_file():
        return ws_candidate
    return None


DOCUMENT_MAP = {
    "D01": ("D01_HPS.docx", "01_HPS.docx"),
    "D02": ("D02_SPP.docx", "02_SPP.docx"),
    "D03": ("D03_S_PENAWARAN.docx", "03_SURAT_PENAWARAN.docx"),
    "D04": ("D04_S_NEGOSIASI.docx", "04_SURAT_NEGOSIASI.docx"),
    "D05": ("D05_SURAT_PESANAN.docx", "05_SURAT_PESANAN.docx"),
    "D06": ("D06_FAKTUR.docx", "06_FAKTUR.docx"),
    "D07": ("D07_KWITANSI.docx", "07_KWITANSI.docx"),
    "D08": ("D08_SURAT_JALAN.docx", "08_SURAT_JALAN.docx"),
    "D09": ("D09_BAPB.docx", "09_BAPB.docx"),
    "D10": ("D10_BAST.docx", "10_BAST.docx"),
    "D11": ("D11_BAPP.docx", "11_BAPP.docx"),
    "D12": ("D12_LAMP_BAPP.docx", "12_LAMP_BAPP.docx"),
    "D13": ("D13_BAST_REKANAN.docx", "13_BAST_REKANAN.docx"),
}


class DocxPackageGenerator:
    """Renders 13 individual .docx documents using docxtpl Jinja2 templates."""

    def __init__(self, context: Dict[str, Any]):
        self.context = context
        # Ensure templates exist
        if not TEMPLATES_DIR.exists() or not any(TEMPLATES_DIR.glob("*.docx")):
            build_all_templates()

    def _prepare_render_context(self, doc: DocxTemplate) -> Dict[str, Any]:
        """Prepares render context with docxtpl InlineImage instances bound to the document."""
        ctx = dict(self.context)

        school_path_raw = ctx.get("school", {}).get("letterhead_path")
        school_img_path = resolve_letterhead_image_path(school_path_raw)
        if school_img_path:
            ctx["school_has_letterhead_image"] = True
            ctx["school_letterhead_image"] = InlineImage(doc, str(school_img_path), width=Inches(6.75))
        else:
            ctx["school_has_letterhead_image"] = False
            ctx["school_letterhead_image"] = None

        company_path_raw = ctx.get("company", {}).get("logo_path")
        company_img_path = resolve_letterhead_image_path(company_path_raw)
        if company_img_path:
            ctx["company_has_letterhead_image"] = True
            ctx["company_letterhead_image"] = InlineImage(doc, str(company_img_path), width=Inches(6.75))
        else:
            ctx["company_has_letterhead_image"] = False
            ctx["company_letterhead_image"] = None

        return ctx

    def generate_all(self, output_dir: Path) -> Dict[str, Path]:
        """Renders all 13 documents into the specified output directory.
        Returns a dict mapping doc_code (e.g. 'D01') to the rendered Path.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        rendered_files: Dict[str, Path] = {}

        for doc_code, (tmpl_filename, out_filename) in DOCUMENT_MAP.items():
            tmpl_path = TEMPLATES_DIR / tmpl_filename
            if not tmpl_path.exists():
                # Re-bootstrap if single template was deleted
                build_all_templates()

            doc = DocxTemplate(str(tmpl_path))
            render_ctx = self._prepare_render_context(doc)
            doc.render(render_ctx)

            out_path = output_dir / out_filename
            doc.save(str(out_path))
            rendered_files[doc_code] = out_path

        return rendered_files

    def generate_single(self, doc_code: str, output_path: Path) -> Path:
        """Renders a single document by doc_code (e.g. 'D01') to output_path."""
        if doc_code not in DOCUMENT_MAP:
            raise ValueError(f"Unknown document code: {doc_code}")

        tmpl_filename, _ = DOCUMENT_MAP[doc_code]
        tmpl_path = TEMPLATES_DIR / tmpl_filename
        if not tmpl_path.exists():
            build_all_templates()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = DocxTemplate(str(tmpl_path))
        render_ctx = self._prepare_render_context(doc)
        doc.render(render_ctx)
        doc.save(str(output_path))
        return output_path
