import pytest
from pathlib import Path
from app.services.import_service import ExcelImportService


def test_import_kk09_reference():
    file_path = Path("4 PCI KK09.xlsx").resolve()
    if not file_path.exists():
        # check parent directory
        file_path = Path("..") / "4 PCI KK09.xlsx"
    
    assert file_path.exists(), f"Reference file {file_path} not found"

    svc = ExcelImportService()
    result = svc.parse_workbook(file_path)

    # 1. Assert exactly 8 candidate line items are extracted from HPS
    lines = result["candidate_lines"]
    assert len(lines) == 8, f"Expected 8 lines, got {len(lines)}"

    # Check first item: glass cleaner
    assert lines[0]["confirmed_description"] == "glass cleaner"
    assert lines[0]["quantity"] == 15
    assert lines[0]["unit"] == "liter"
    assert lines[0]["final_unit_price"] == 16000
    assert lines[0]["line_total"] == 240000

    # Check last item: pengharum kloset
    assert lines[7]["confirmed_description"] == "pengharum kloset"
    assert lines[7]["quantity"] == 10
    assert lines[7]["unit"] == "buah"
    assert lines[7]["final_unit_price"] == 23000
    assert lines[7]["line_total"] == 230000

    # Total sum of lines
    total_goods = sum(l["line_total"] for l in lines)
    assert total_goods == 2285000

    # 2. Assert all 13 sheets are detected
    assert len(result["sheet_names"]) == 13

    # 3. Assert invariant discrepancies are detected:
    # - External links =[1]Sheet1!
    # - Entity mismatch (CV MITRA KARYA GEMILANG)
    # - Entity mismatch (SDN Kebon Kosong 05 / 13)
    # - Incomplete rows on Lamp BAPP / BAST Rekanan
    # - Stale number / 2022
    # - 2025 date anomaly
    disc = result["detected_discrepancies"]
    assert len(disc) > 0

    categories = {d["rule_category"] for d in disc}
    assert "EXTERNAL_LINK" in categories
    assert "ENTITY_MISMATCH" in categories
    assert "INCOMPLETE_ROWS" in categories
    assert "DATE_INVERSION" in categories
    assert "STALE_NUMBER" in categories
