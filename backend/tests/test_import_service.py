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
    assert lines[0]["hps_unit_price"] == 16000
    assert lines[0]["final_unit_price"] == 16000
    assert lines[0]["line_total"] == 240000

    # Check last item: pengharum kloset
    assert lines[7]["confirmed_description"] == "pengharum kloset"
    assert lines[7]["quantity"] == 10
    assert lines[7]["unit"] == "buah"
    assert lines[7]["hps_unit_price"] == 23000
    assert lines[7]["final_unit_price"] == 23000
    assert lines[7]["line_total"] == 230000

    # Total sum of lines
    total_goods = sum(l["line_total"] for l in lines)
    assert total_goods == 2285000

    # 2. Assert all 13 sheets are detected
    assert len(result["sheet_names"]) == 13

    # 3. Assert invariant discrepancies are detected
    disc = result["detected_discrepancies"]
    assert len(disc) > 0

    categories = {d["rule_category"] for d in disc}
    assert "EXTERNAL_LINK" in categories
    assert "ENTITY_MISMATCH" in categories
    assert "INCOMPLETE_ROWS" in categories
    assert "DATE_INVERSION" in categories
    assert "STALE_NUMBER" in categories


def test_import_template_with_harga_satuan_column():
    """Verifies that the standard template having 'Harga Satuan' maps to hps_unit_price,
    and 'Satuan' maps to unit, without any collision or misassignment.
    """
    svc = ExcelImportService()
    template_bytes = svc.generate_template_workbook()
    temp_file = Path("temp_template_test.xlsx")
    try:
        temp_file.write_bytes(template_bytes)
        result = svc.parse_workbook(temp_file)

        lines = result["candidate_lines"]
        assert len(lines) == 8, f"Expected 8 sample lines, got {len(lines)}"

        # Verify that 'Harga Satuan' (16000) correctly went to hps_unit_price, NOT unit
        item0 = lines[0]
        assert item0["confirmed_description"] == "glass cleaner"
        assert item0["quantity"] == 15
        assert item0["unit"] == "liter", f"Expected unit 'liter', got {item0['unit']}"
        assert item0["hps_unit_price"] == 16000.0, f"Expected hps_unit_price 16000, got {item0['hps_unit_price']}"
        assert item0["offer_unit_price"] == 16000.0
        assert item0["final_unit_price"] == 16000.0
        assert item0["line_total"] == 240000.0

        # Verify second item: hand soap (satuan: liter, harga satuan: 16000)
        item1 = lines[1]
        assert item1["confirmed_description"] == "hand soap"
        assert item1["unit"] == "liter"
        assert item1["hps_unit_price"] == 16000.0
        assert item1["final_unit_price"] == 16000.0
        assert item1["line_total"] == 240000.0

        # Verify item with different unit: sapu ijuk (satuan: buah, harga satuan: 20000)
        item6 = lines[6]
        assert item6["confirmed_description"] == "sapu ijuk"
        assert item6["unit"] == "buah"
        assert item6["hps_unit_price"] == 20000.0
        assert item6["final_unit_price"] == 20000.0
        assert item6["line_total"] == 240000.0

        total_goods = sum(l["line_total"] for l in lines)
        assert total_goods == 2285000.0
    finally:
        temp_file.unlink(missing_ok=True)


if __name__ == "__main__":
    test_import_kk09_reference()
    print("test_import_kk09_reference PASSED!")
    test_import_template_with_harga_satuan_column()
    print("test_import_template_with_harga_satuan_column PASSED!")
    print("All import tests passed successfully!")
