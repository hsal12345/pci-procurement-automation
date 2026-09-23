"""Headless LibreOffice PDF conversion and merging service.
Features:
- Windows concurrency isolation using temporary user profiles (-env:UserInstallation)
- Low-opacity DRAFT watermark stamping (fillAlpha=0.10) using ReportLab and pypdf
- Consolidated PDF package merger (00_PAKET_LENGKAP.pdf) in exact canonical order
"""
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from app.config import settings


CANONICAL_PDF_ORDER = [
    ("D01", "01_HPS.pdf"),
    ("D02", "02_SPP.pdf"),
    ("D03", "03_SURAT_PENAWARAN.pdf"),
    ("D04", "04_SURAT_NEGOSIASI.pdf"),
    ("D05", "05_SURAT_PESANAN.pdf"),
    ("D06", "06_FAKTUR.pdf"),
    ("D07", "07_KWITANSI.pdf"),
    ("D08", "08_SURAT_JALAN.pdf"),
    ("D09", "09_BAPB.pdf"),
    ("D10", "10_BAST.pdf"),
    ("D11", "11_BAPP.pdf"),
    ("D12", "12_LAMP_BAPP.pdf"),
    ("D13", "13_BAST_REKANAN.pdf"),
]


class PdfService:
    """Handles conversion from DOCX to PDF, watermark application, and PDF merging."""

    def __init__(self, libreoffice_path: Optional[str] = None):
        self.lo_path = libreoffice_path or settings.LIBREOFFICE_PATH
        if not Path(self.lo_path).exists():
            raise FileNotFoundError(
                f"Headless LibreOffice binary not found at '{self.lo_path}'. "
                "Please configure LIBREOFFICE_PATH in .env."
            )

    def convert_docx_to_pdf(self, docx_path: Path, output_dir: Path) -> Path:
        """Converts a single .docx file to .pdf using an isolated LibreOffice profile."""
        output_dir.mkdir(parents=True, exist_ok=True)
        unique_profile_dir = tempfile.mkdtemp(prefix="lo_profile_")
        profile_uri = Path(unique_profile_dir).as_uri()

        cmd = [
            self.lo_path,
            f"-env:UserInstallation={profile_uri}",
            "--headless",
            "--invisible",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            "--convert-to", "pdf:writer_pdf_Export",
            "--outdir", str(output_dir),
            str(docx_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(
                    f"LibreOffice conversion failed for {docx_path.name}: "
                    f"return code {result.returncode}, stderr: {result.stderr}"
                )
        finally:
            shutil.rmtree(unique_profile_dir, ignore_errors=True)

        expected_pdf = output_dir / f"{docx_path.stem}.pdf"
        if not expected_pdf.exists():
            raise FileNotFoundError(f"Expected converted PDF not found at {expected_pdf}")

        return expected_pdf

    def convert_batch_docx(
        self,
        docx_map: Dict[str, Path],
        output_dir: Path,
        is_draft: bool = False
    ) -> Dict[str, Path]:
        """Converts all generated .docx files to .pdf, applies draft watermark if required,
        merges them into 00_PAKET_LENGKAP.pdf, and returns a mapping of doc_code -> Path.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_map: Dict[str, Path] = {}

        # 1. Convert each DOCX
        for doc_code, docx_path in docx_map.items():
            raw_pdf = self.convert_docx_to_pdf(docx_path, output_dir)
            if is_draft:
                watermarked_pdf = output_dir / f"{raw_pdf.stem}_wm.pdf"
                self.apply_draft_watermark(raw_pdf, watermarked_pdf)
                # Overwrite raw with watermarked
                raw_pdf.unlink()
                watermarked_pdf.rename(raw_pdf)

            pdf_map[doc_code] = raw_pdf

        # 2. Merge all documents into 00_PAKET_LENGKAP.pdf in canonical order
        merged_path = output_dir / "00_PAKET_LENGKAP.pdf"
        merger = PdfWriter()

        for doc_code, expected_name in CANONICAL_PDF_ORDER:
            if doc_code in pdf_map and pdf_map[doc_code].exists():
                merger.append(str(pdf_map[doc_code]))

        with open(merged_path, "wb") as f_merged:
            merger.write(f_merged)
        merger.close()

        pdf_map["ALL"] = merged_path
        return pdf_map

    def apply_draft_watermark(
        self,
        input_pdf: Path,
        output_pdf: Path,
        text: str = "DRAFT - BELUM DISETUJUI"
    ) -> Path:
        """Applies a subtle 10% opacity diagonal watermark so monetary values remain legible."""
        reader = PdfReader(str(input_pdf))
        writer = PdfWriter()

        for page in reader.pages:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)

            # Generate overlay canvas
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=(width, height))
            c.saveState()
            c.setFont("Helvetica-Bold", 40)
            c.setFillColorRGB(0.85, 0.1, 0.1, alpha=0.10)  # Strictly 10% alpha (PRD 4.2)
            c.translate(width / 2.0, height / 2.0)
            c.rotate(45)
            c.drawCentredString(0, 0, text)
            c.restoreState()
            c.save()

            packet.seek(0)
            watermark_pdf = PdfReader(packet)
            watermark_page = watermark_pdf.pages[0]

            page.merge_page(watermark_page)
            writer.add_page(page)

        with open(output_pdf, "wb") as f_out:
            writer.write(f_out)

        return output_pdf
