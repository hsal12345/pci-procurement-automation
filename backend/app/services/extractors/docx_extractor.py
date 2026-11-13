"""Deterministic extractor for Word (.docx) procurement documents."""
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import docx
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.services.extractors.base import (
    ExtractedSection,
    build_unified_document_payload,
    clean_cell_text,
)


class DocxExtractor:
    """Validates and extracts paragraphs, headers, and structured tables from .docx files."""

    @staticmethod
    def validate_integrity(file_path: Path, max_size_bytes: int = 20 * 1024 * 1024) -> None:
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("Berkas Word (.docx) tidak ditemukan di penyimpanan sementara.")
        size = file_path.stat().st_size
        if size <= 0:
            raise ValueError("Berkas Word (.docx) kosong (0 byte) dan tidak dapat diproses.")
        if size > max_size_bytes:
            raise ValueError("Ukuran berkas Word (.docx) melebihi batas maksimal 20 MB.")
        if not zipfile.is_zipfile(file_path):
            raise ValueError("Struktur berkas tidak valid atau rusak (bukan kontainer .docx OpenXML yang sah).")

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                names = set(zf.namelist())
                if "word/document.xml" not in names:
                    raise ValueError("Berkas ZIP bukan dokumen Word (.docx) yang valid.")
            doc = docx.Document(str(file_path))
        except zipfile.BadZipFile as exc:
            raise ValueError(f"Berkas Word (.docx) rusak: {exc}") from exc
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Berkas Word (.docx) tidak dapat dibaca: {exc}") from exc

        has_text = any(clean_cell_text(p.text) for p in doc.paragraphs)
        has_table = any(
            clean_cell_text(cell.text)
            for tbl in doc.tables
            for row in tbl.rows
            for cell in row.cells
        )
        if not has_text and not has_table:
            raise ValueError("Dokumen Word (.docx) tidak berisi teks atau tabel yang dapat diekstrak.")

    @staticmethod
    def _extract_table_grid(table: Table) -> List[List[Any]]:
        grid: List[List[Any]] = []
        for row in table.rows:
            row_vals: List[Any] = []
            seen_tc = set()
            for cell in row.cells:
                tc_id = id(cell._tc)
                if tc_id in seen_tc:
                    # Preserve grid column width without repeating horizontally merged text
                    row_vals.append("")
                else:
                    seen_tc.add(tc_id)
                    row_vals.append(clean_cell_text(cell.text))
            if any(v != "" for v in row_vals):
                grid.append(row_vals)
        return grid

    @classmethod
    def _synthetic_grid_from_paragraphs(cls, paragraphs: List[str]) -> Optional[ExtractedSection]:
        """Fallback grid builder for .docx files that use tab/pipe/number lists instead of Word tables."""
        rows: List[List[Any]] = []
        for line in paragraphs:
            txt = clean_cell_text(line)
            if not txt:
                continue
            if "\t" in line:
                parts = [clean_cell_text(p) for p in line.split("\t") if clean_cell_text(p)]
                if len(parts) >= 2:
                    rows.append(parts)
                    continue
            if "|" in txt:
                parts = [clean_cell_text(p) for p in txt.split("|") if clean_cell_text(p)]
                if len(parts) >= 2:
                    rows.append(parts)
                    continue
            # Match multi-space columns (2+ spaces) in plain formatted documents
            raw_parts = [clean_cell_text(p) for p in re.split(r"\s{2,}", line.strip()) if clean_cell_text(p)]
            if len(raw_parts) >= 2:
                rows.append(raw_parts)

        if len(rows) < 2:
            # Build simple 2-column line listing so user & AI can inspect extracted text cleanly
            rows = [[idx, clean_cell_text(p)] for idx, p in enumerate(paragraphs[:80], start=1) if clean_cell_text(p)]
        if not rows:
            return None
        return ExtractedSection(name="Teks Dokumen", grid=rows, context_snippets=paragraphs[:15])

    @classmethod
    def parse(
        cls,
        file_path: Path,
        *,
        source_format: str = "DOCX",
        column_mapping: Optional[Dict[str, int]] = None,
        section_name: Optional[str] = None,
        header_row_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        doc = docx.Document(str(file_path))

        context_lines: List[str] = []
        raw_paragraphs: List[str] = []

        # Include document headers (kop surat) if present
        for sec in doc.sections:
            try:
                for p in sec.header.paragraphs:
                    txt = clean_cell_text(p.text)
                    if txt and txt not in context_lines:
                        context_lines.append(txt)
            except Exception:
                pass

        sections: List[ExtractedSection] = []
        recent_headings: List[str] = []
        table_counter = 0

        for child in doc.element.body.iterchildren():
            if isinstance(child, CT_P):
                para = Paragraph(child, doc)
                raw_text = para.text or ""
                cleaned = clean_cell_text(raw_text)
                if cleaned:
                    context_lines.append(cleaned)
                    raw_paragraphs.append(raw_text)
                    recent_headings.append(cleaned)
                    recent_headings = recent_headings[-3:]
            elif isinstance(child, CT_Tbl):
                table = Table(child, doc)
                grid = cls._extract_table_grid(table)
                if not grid:
                    continue
                table_counter += 1
                # If table looks like key-value metadata (2 cols, <= 6 rows, no header tokens), add its pairs to context too
                max_cols = max((len(r) for r in grid), default=0)
                if max_cols <= 3 and len(grid) <= 8:
                    for r in grid:
                        joined = " ".join(c for c in r if c)
                        if joined and joined not in context_lines:
                            context_lines.append(joined)

                heading_hint = recent_headings[-1][:28].strip() if recent_headings else ""
                if heading_hint and not any(ch in heading_hint for ch in (":", "=")):
                    sec_label = f"Tabel {table_counter} ({heading_hint})"
                else:
                    sec_label = f"Tabel {table_counter}"

                # Ensure unique section names
                existing_names = {s.name for s in sections}
                if sec_label in existing_names:
                    sec_label = f"Tabel {table_counter}"

                sections.append(
                    ExtractedSection(
                        name=sec_label,
                        grid=grid,
                        context_snippets=list(recent_headings),
                    )
                )

        if not sections:
            synthetic = cls._synthetic_grid_from_paragraphs(raw_paragraphs or context_lines)
            if synthetic:
                sections.append(synthetic)

        return build_unified_document_payload(
            source_format=source_format,
            sections=sections,
            document_context_lines=context_lines,
            column_mapping=column_mapping,
            section_name=section_name,
            header_row_index=header_row_index,
            extraction_stats={
                "paragraphs_count": len(raw_paragraphs),
                "tables_count": table_counter,
            },
        )
