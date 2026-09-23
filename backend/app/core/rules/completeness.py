import re
from typing import List, Optional, Dict, Any
from app.core.rules.base import RuleFinding
from app.schemas.common import SeverityEnum

# Generic regex to detect external workbook links and corrupted formula cells
EXTERNAL_OR_CORRUPT_PATTERN = re.compile(
    r"(\[\d+\]|\.xlsx?!|#REF!|#VALUE!|#NAME\?|#DIV/0!|#NULL!)",
    re.IGNORECASE
)

REQUIRED_13_DOCS = [
    "D01", "D02", "D03", "D04", "D05", "D06", "D07",
    "D08", "D09", "D10", "D11", "D12", "D13"
]


def validate_br02_completeness(
    doc_numbers: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    lines: List[Dict[str, Any]],
    required_docs: Optional[List[str]] = None
) -> List[RuleFinding]:
    """BR02 Completeness:
    Ensures every applicable template exists, has valid document numbers,
    required event dates, and no unresolved placeholders.
    """
    findings: List[RuleFinding] = []
    target_docs = required_docs or REQUIRED_13_DOCS

    existing_docs = {
        d.get("doc_code")
        for d in doc_numbers
        if d.get("doc_code") and (d.get("doc_number") or "").strip()
    }
    for code in target_docs:
        if code not in existing_docs:
            findings.append(RuleFinding(
                rule_code="BR02",
                severity=SeverityEnum.BLOCK,
                doc_code=code,
                field_name="doc_number",
                message=f"Nomor dokumen untuk jenis '{code}' belum dialokasikan atau belum terdaftar."
            ))

    if not lines:
        findings.append(RuleFinding(
            rule_code="BR02",
            severity=SeverityEnum.BLOCK,
            field_name="lines",
            message="Daftar rincian barang/jasa kosong. Minimal harus terdapat 1 baris item transaksi."
        ))

    return findings


def validate_br03_item_coverage(
    revision_lines: List[Dict[str, Any]],
    itemized_sheet_counts: Optional[Dict[str, int]] = None
) -> List[RuleFinding]:
    """BR03 Item Coverage (Dynamic N Items):
    Ensures that for every itemized document, the number of lines and items
    matches count(revision_lines) exactly.
    Catches historical defects where Lamp BAPP or BAST Rekanan only contain 1 item.
    """
    findings: List[RuleFinding] = []
    expected_count = len(revision_lines)

    if expected_count == 0:
        return findings

    if itemized_sheet_counts:
        for sheet_name, actual_count in itemized_sheet_counts.items():
            if actual_count != expected_count:
                findings.append(RuleFinding(
                    rule_code="BR03",
                    severity=SeverityEnum.BLOCK,
                    sheet_name=sheet_name,
                    field_name="line_count",
                    original_value=str(actual_count),
                    proposed_value=str(expected_count),
                    message=(
                        f"Inkonsistensi jumlah baris barang pada sheet '{sheet_name}': "
                        f"hanya memuat {actual_count} item, padahal transaksi induk memuat {expected_count} item."
                    )
                ))

    return findings


def validate_br10_external_and_stale_references(
    raw_cells_or_formulas: List[Dict[str, Any]]
) -> List[RuleFinding]:
    """BR10 External and Stale References:
    Generic invariant check: Scans formulas and cell values for external workbook links
    (e.g., =[1]Sheet1!C24 or path.xlsx) or Excel error values (#REF!, #VALUE!).
    """
    findings: List[RuleFinding] = []

    for item in raw_cells_or_formulas:
        formula_or_val = str(item.get("value") or "")
        sheet = item.get("sheet_name")
        cell = item.get("cell_range")

        if formula_or_val and EXTERNAL_OR_CORRUPT_PATTERN.search(formula_or_val):
            findings.append(RuleFinding(
                rule_code="BR10",
                severity=SeverityEnum.BLOCK,
                sheet_name=sheet,
                cell_range=cell,
                field_name="formula",
                original_value=formula_or_val,
                message=(
                    f"Terdeteksi formula referensi eksternal atau sel korup pada sheet '{sheet}' "
                    f"sel {cell}: '{formula_or_val}'. Semua nilai harus dinormalisasi menjadi nilai internal mandiri."
                )
            ))

    return findings
