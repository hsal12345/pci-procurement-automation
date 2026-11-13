"""Router & facade for multi-format document integrity validation and deterministic extraction."""
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.extractors.doc_extractor import DocExtractor
from app.services.extractors.docx_extractor import DocxExtractor
from app.services.extractors.pdf_extractor import PdfExtractor

SUPPORTED_EXTENSIONS = {".xlsx", ".pdf", ".docx", ".doc"}


class DocumentExtractorRouter:
    """Dispatches validation & deterministic extraction across .xlsx, .pdf, .docx, and .doc."""

    @staticmethod
    def detect_format(file_path: Path) -> str:
        ext = file_path.suffix.lower()
        if ext == ".xls":
            raise ValueError(
                "Format lama .xls tidak didukung langsung. Silakan simpan ulang sebagai .xlsx terlebih dahulu."
            )
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                "Format berkas tidak didukung. Unggah berkas berekstensi .xlsx, .pdf, .docx, atau .doc."
            )
        return ext.lstrip(".").upper()

    @classmethod
    def validate_integrity(cls, file_path: Path, excel_service=None) -> str:
        """Validates format, magic bytes, container structure, and non-empty text/cells before AI."""
        fmt = cls.detect_format(file_path)
        if fmt == "XLSX":
            if excel_service is None:
                from app.services.import_service import ExcelImportService
                excel_service = ExcelImportService()
            excel_service.validate_workbook_integrity(file_path)
        elif fmt == "DOCX":
            DocxExtractor.validate_integrity(file_path)
        elif fmt == "DOC":
            DocExtractor.validate_integrity(file_path)
        elif fmt == "PDF":
            PdfExtractor.validate_integrity(file_path)
        return fmt

    @classmethod
    def parse_document(
        cls,
        file_path: Path,
        *,
        excel_service=None,
        column_mapping: Optional[Dict[str, int]] = None,
        section_name: Optional[str] = None,
        header_row_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        fmt = cls.detect_format(file_path)
        if fmt == "XLSX":
            if excel_service is None:
                from app.services.import_service import ExcelImportService
                excel_service = ExcelImportService()
            return excel_service.parse_workbook(
                file_path,
                column_mapping=column_mapping,
                sheet_name=section_name,
                header_row_index=header_row_index,
            )
        if fmt == "DOCX":
            return DocxExtractor.parse(
                file_path,
                source_format="DOCX",
                column_mapping=column_mapping,
                section_name=section_name,
                header_row_index=header_row_index,
            )
        if fmt == "DOC":
            return DocExtractor.parse(
                file_path,
                column_mapping=column_mapping,
                section_name=section_name,
                header_row_index=header_row_index,
            )
        if fmt == "PDF":
            return PdfExtractor.parse(
                file_path,
                column_mapping=column_mapping,
                section_name=section_name,
                header_row_index=header_row_index,
            )
        raise ValueError(f"Format tidak dikenali: {fmt}")
