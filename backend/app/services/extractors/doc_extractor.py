"""Deterministic extractor for legacy Word (.doc) via LibreOffice conversion to .docx."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import settings
from app.services.extractors.docx_extractor import DocxExtractor

OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class DocExtractor:
    """Validates OLE2 .doc files, converts deterministically via LibreOffice, and parses as .docx."""

    @staticmethod
    def _find_soffice() -> Optional[str]:
        candidates = [
            getattr(settings, "LIBREOFFICE_PATH", None),
            os.environ.get("LIBREOFFICE_PATH"),
            "/usr/bin/soffice",
            shutil.which("soffice"),
            shutil.which("libreoffice"),
        ]
        for cand in candidates:
            if cand and Path(cand).exists():
                return str(cand)
        return None

    @classmethod
    def validate_integrity(cls, file_path: Path, max_size_bytes: int = 20 * 1024 * 1024) -> None:
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("Berkas Word (.doc) tidak ditemukan di penyimpanan sementara.")
        size = file_path.stat().st_size
        if size <= 0:
            raise ValueError("Berkas Word (.doc) kosong (0 byte) dan tidak dapat diproses.")
        if size > max_size_bytes:
            raise ValueError("Ukuran berkas Word (.doc) melebihi batas maksimal 20 MB.")

        with open(file_path, "rb") as f:
            header = f.read(8)
        if header != OLE2_MAGIC:
            raise ValueError(
                "Struktur berkas tidak valid atau rusak (bukan dokumen biner Word .doc OLE2 yang sah)."
            )

        if not cls._find_soffice():
            raise ValueError(
                "Konverter LibreOffice (soffice) tidak tersedia untuk membaca berkas .doc lama. Simpan ulang sebagai .docx."
            )

    @classmethod
    def convert_to_docx(cls, file_path: Path, output_dir: Path) -> Path:
        soffice = cls._find_soffice()
        if not soffice:
            raise ValueError(
                "Konverter LibreOffice (soffice) tidak tersedia untuk membaca berkas .doc lama."
            )

        profile_dir = output_dir / "lo_profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            soffice,
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--headless",
            "--norestore",
            "--convert-to",
            "docx",
            "--outdir",
            str(output_dir),
            str(file_path),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=35,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Waktu konversi berkas .doc melebihi batas (35 detik).") from exc

        converted = output_dir / f"{file_path.stem}.docx"
        if proc.returncode != 0 or not converted.exists():
            stderr_msg = (proc.stderr or proc.stdout or "").strip()
            raise ValueError(
                f"Gagal mengonversi berkas .doc ke format terstruktur: {stderr_msg or 'exit code ' + str(proc.returncode)}"
            )
        return converted

    @classmethod
    def parse(
        cls,
        file_path: Path,
        *,
        column_mapping: Optional[Dict[str, int]] = None,
        section_name: Optional[str] = None,
        header_row_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="pci_doc_conv_") as tmp_str:
            tmp_dir = Path(tmp_str)
            converted_docx = cls.convert_to_docx(file_path, tmp_dir)
            DocxExtractor.validate_integrity(converted_docx)
            payload = DocxExtractor.parse(
                converted_docx,
                source_format="DOC",
                column_mapping=column_mapping,
                section_name=section_name,
                header_row_index=header_row_index,
            )
            stats = payload.setdefault("extraction_stats", {})
            stats["converted_via"] = "libreoffice"
            return payload
