"""Deterministic extractor for text & table-based PDF procurement documents."""
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pypdf import PdfReader

from app.services.extractors.base import (
    ExtractedSection,
    build_unified_document_payload,
    clean_cell_text,
)

try:
    import pdfplumber
except ImportError:  # pragma: no cover - fallback when optional package absent locally
    pdfplumber = None


PDF_MAGIC = b"%PDF-"
MAX_PDF_PAGES = 50


class PdfExtractor:
    """Validates PDF files, rejects image-only scans before AI, and extracts tables + context."""

    @staticmethod
    def validate_integrity(file_path: Path, max_size_bytes: int = 20 * 1024 * 1024) -> None:
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("Berkas PDF tidak ditemukan di penyimpanan sementara.")
        size = file_path.stat().st_size
        if size <= 0:
            raise ValueError("Berkas PDF kosong (0 byte) dan tidak dapat diproses.")
        if size > max_size_bytes:
            raise ValueError("Ukuran berkas PDF melebihi batas maksimal 20 MB.")

        with open(file_path, "rb") as f:
            magic = f.read(5)
        if magic != PDF_MAGIC:
            raise ValueError("Struktur berkas tidak valid atau rusak (bukan dokumen PDF yang sah).")

        try:
            reader = PdfReader(str(file_path))
            if reader.is_encrypted:
                raise ValueError("Berkas PDF dilindungi kata sandi dan tidak dapat dibaca.")
            page_count = len(reader.pages)
            if page_count == 0:
                raise ValueError("Berkas PDF tidak memiliki halaman sama sekali.")
            if page_count > MAX_PDF_PAGES:
                raise ValueError(f"Jumlah halaman PDF ({page_count}) melebihi batas maksimal {MAX_PDF_PAGES} halaman.")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Berkas PDF rusak atau tidak dapat dibuka: {exc}") from exc

    @staticmethod
    def _clean_pdf_table(raw_table: List[List[Optional[str]]]) -> List[List[Any]]:
        cleaned_rows: List[List[Any]] = []
        for row in raw_table or []:
            if not row:
                continue
            cleaned_row = [clean_cell_text(cell) for cell in row]
            if any(cleaned_row):
                cleaned_rows.append(cleaned_row)
        return cleaned_rows

    @staticmethod
    def _cluster_words_to_grid(words: List[Dict[str, Any]]) -> List[List[Any]]:
        """Groups borderless PDF words into 2D rows & columns using vertical/horizontal coordinates."""
        if not words:
            return []
        # Cluster by y (top) within ~4pt tolerance
        sorted_words = sorted(words, key=lambda w: (round(float(w["top"]) / 4.0) * 4.0, float(w["x0"])))
        lines_buckets: List[List[Dict[str, Any]]] = []
        current_top: Optional[float] = None
        for w in sorted_words:
            top = float(w["top"])
            if current_top is None or abs(top - current_top) > 5.0:
                lines_buckets.append([w])
                current_top = top
            else:
                lines_buckets[-1].append(w)

        grid: List[List[Any]] = []
        for bucket in lines_buckets:
            bucket.sort(key=lambda w: float(w["x0"]))
            cells: List[str] = []
            buf: List[str] = []
            prev_x1: Optional[float] = None
            for w in bucket:
                x0 = float(w["x0"])
                x1 = float(w["x1"])
                txt = clean_cell_text(w.get("text"))
                if not txt:
                    continue
                if prev_x1 is not None and (x0 - prev_x1) > 14.0:
                    cells.append(" ".join(buf))
                    buf = [txt]
                else:
                    buf.append(txt)
                prev_x1 = x1
            if buf:
                cells.append(" ".join(buf))
            if any(cells):
                grid.append(cells)

        # Normalize row lengths to rectangular shape
        max_len = max((len(r) for r in grid), default=0)
        return [r + [""] * (max_len - len(r)) for r in grid]

    @classmethod
    def _extract_with_pdfplumber(cls, file_path: Path) -> Tuple[List[ExtractedSection], List[str], int]:
        sections: List[ExtractedSection] = []
        context_lines: List[str] = []
        total_chars = 0

        with pdfplumber.open(str(file_path)) as pdf:
            page_count = len(pdf.pages)
            for page_idx, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                page_lines = [clean_cell_text(l) for l in page_text.splitlines() if clean_cell_text(l)]
                total_chars += sum(len(l) for l in page_lines)
                context_lines.extend(page_lines[:30])

                # 1. Ruled / line-based tables
                raw_tables = page.extract_tables() or []
                valid_tables = []
                for t in raw_tables:
                    cleaned = cls._clean_pdf_table(t)
                    if len(cleaned) >= 2 and max((len(r) for r in cleaned), default=0) >= 2:
                        valid_tables.append(cleaned)

                # 2. Fallback to text-strategy tables if no ruled table found
                if not valid_tables and page_lines:
                    text_tables = page.extract_tables(
                        table_settings={
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "intersection_tolerance": 5,
                        }
                    ) or []
                    for t in text_tables:
                        cleaned = cls._clean_pdf_table(t)
                        if len(cleaned) >= 2 and max((len(r) for r in cleaned), default=0) >= 3:
                            valid_tables.append(cleaned)

                if valid_tables:
                    for t_idx, grid in enumerate(valid_tables, start=1):
                        sections.append(
                            ExtractedSection(
                                name=f"Hal {page_idx} - Tabel {t_idx}",
                                grid=grid,
                                context_snippets=page_lines[:10],
                                page_number=page_idx,
                            )
                        )
                elif page_lines:
                    # 3. Coordinate word clustering fallback for semi-tabular borderless PDFs
                    words = page.extract_words() or []
                    clustered = cls._cluster_words_to_grid(words)
                    if clustered:
                        sections.append(
                            ExtractedSection(
                                name=f"Hal {page_idx} - Teks",
                                grid=clustered,
                                context_snippets=page_lines[:10],
                                page_number=page_idx,
                            )
                        )

        if total_chars < 25 and not sections:
            raise ValueError(
                "Berkas PDF tampaknya berupa hasil pindaian gambar (scan) tanpa teks yang dapat disalin. "
                "Unggah PDF berbasis teks, DOCX, atau XLSX."
            )

        return sections, context_lines, page_count

    @classmethod
    def _extract_with_pypdf_fallback(cls, file_path: Path) -> Tuple[List[ExtractedSection], List[str], int]:
        reader = PdfReader(str(file_path))
        page_count = len(reader.pages)
        sections: List[ExtractedSection] = []
        context_lines: List[str] = []
        total_chars = 0

        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            lines = [l for l in text.splitlines() if clean_cell_text(l)]
            total_chars += sum(len(clean_cell_text(l)) for l in lines)
            context_lines.extend(clean_cell_text(l) for l in lines[:30])

            grid: List[List[Any]] = []
            for line in lines:
                parts = [clean_cell_text(p) for p in re.split(r"\s{2,}|\|", line.strip()) if clean_cell_text(p)]
                if len(parts) >= 2:
                    grid.append(parts)
                elif clean_cell_text(line):
                    grid.append([clean_cell_text(line)])

            if grid:
                max_len = max((len(r) for r in grid), default=1)
                grid = [r + [""] * (max_len - len(r)) for r in grid]
                sections.append(
                    ExtractedSection(
                        name=f"Hal {page_idx} - Teks",
                        grid=grid,
                        context_snippets=[clean_cell_text(l) for l in lines[:10]],
                        page_number=page_idx,
                    )
                )

        if total_chars < 25 and not sections:
            raise ValueError(
                "Berkas PDF tampaknya berupa hasil pindaian gambar (scan) tanpa teks yang dapat disalin. "
                "Unggah PDF berbasis teks, DOCX, atau XLSX."
            )
        return sections, context_lines, page_count

    @classmethod
    def parse(
        cls,
        file_path: Path,
        *,
        column_mapping: Optional[Dict[str, int]] = None,
        section_name: Optional[str] = None,
        header_row_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        if pdfplumber is not None:
            sections, context_lines, page_count = cls._extract_with_pdfplumber(file_path)
            engine = "pdfplumber"
        else:
            sections, context_lines, page_count = cls._extract_with_pypdf_fallback(file_path)
            engine = "pypdf"

        return build_unified_document_payload(
            source_format="PDF",
            sections=sections,
            document_context_lines=context_lines,
            column_mapping=column_mapping,
            section_name=section_name,
            header_row_index=header_row_index,
            extraction_stats={
                "pages_count": page_count,
                "tables_count": sum(1 for s in sections if "Tabel" in s.name),
                "pdf_engine": engine,
            },
        )
