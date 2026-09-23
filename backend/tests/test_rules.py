import pytest
from decimal import Decimal
from datetime import date
from app.core.rules.engine import run_deterministic_validation
from app.schemas.common import SeverityEnum


@pytest.fixture
def base_school():
    return {
        "name": "SEKOLAH DASAR NEGERI KEBON KOSONG 09",
        "npsn": "20100123",
        "level": "SD",
        "address": "Jl. Kemayoran Gempol no.32"
    }


@pytest.fixture
def base_company():
    return {
        "legal_name": "CV. PUSTAKA CEMERLANG INDONESIA",
        "npwp": "01.234.567.8-012.000",
        "address": "Wisma Mitra Sunter Unit 3-03",
        "director_name": "Bambang Solifian"
    }


@pytest.fixture
def base_tax_policy():
    return [
        {
            "tax_type": "PPN",
            "rate": Decimal("0.11"),
            "is_inclusive": False,
            "withholding_rule": "NONE",
            "rounding_rule": "ROUND_HALF_UP"
        },
        {
            "tax_type": "PPH22",
            "rate": Decimal("0.015"),
            "is_inclusive": False,
            "withholding_rule": "WITHHOLD_FROM_PAYABLE",
            "rounding_rule": "ROUND_HALF_UP"
        }
    ]


@pytest.fixture
def base_officials():
    return [
        {"role": "KEPALA_SEKOLAH", "person_name": "Drs. H. Mulyadi, M.Pd", "nip": "196501011990031005"},
        {"role": "BENDAHARA", "person_name": "Siti Rahmawati, S.Pd", "nip": "198005122008012015"},
        {"role": "PENGURUS_BARANG", "person_name": "Sulistiawati", "nip": "197909092022212008"},
    ]


@pytest.fixture
def base_doc_numbers():
    return [
        {"doc_code": f"D{i:02d}", "doc_number": f"{i:02d}/PCI/2026"} for i in range(1, 14)
    ]


@pytest.fixture
def base_events():
    return [
        {"event_code": "HPS", "event_date": date(2026, 6, 2)},
        {"event_code": "SPP", "event_date": date(2026, 6, 2)},
        {"event_code": "PENAWARAN", "event_date": date(2026, 6, 5)},
        {"event_code": "NEGOSIASI", "event_date": date(2026, 6, 10)},
        {"event_code": "PESANAN", "event_date": date(2026, 6, 12)},
        {"event_code": "SURAT_JALAN", "event_date": date(2026, 6, 16)},
        {"event_code": "BAPB", "event_date": date(2026, 6, 16)},
        {"event_code": "BAST", "event_date": date(2026, 6, 16)},
        {"event_code": "BAST_REKANAN", "event_date": date(2026, 6, 16)},
        {"event_code": "BAPP", "event_date": date(2026, 6, 16)},
        {"event_code": "FAKTUR", "event_date": date(2026, 6, 16)},
        {"event_code": "KWITANSI", "event_date": date(2026, 6, 16)},
    ]


def test_dynamic_n_items_kk09_eight_items(base_school, base_company, base_tax_policy, base_officials, base_doc_numbers, base_events):
    """Test validation with the 8 items from the KK09 reference."""
    lines = [
        {"line_number": 1, "confirmed_description": "glass cleaner", "quantity": Decimal("15"), "unit": "liter", "hps_unit_price": Decimal("16000"), "offer_unit_price": Decimal("16000"), "final_unit_price": Decimal("16000"), "discount": Decimal("0"), "line_total": Decimal("240000"), "condition": "BAIK"},
        {"line_number": 2, "confirmed_description": "dust cleaner", "quantity": Decimal("3"), "unit": "galon", "hps_unit_price": Decimal("185000"), "offer_unit_price": Decimal("185000"), "final_unit_price": Decimal("185000"), "discount": Decimal("0"), "line_total": Decimal("555000"), "condition": "BAIK"},
        {"line_number": 3, "confirmed_description": "karbol", "quantity": Decimal("5"), "unit": "botol", "hps_unit_price": Decimal("23000"), "offer_unit_price": Decimal("23000"), "final_unit_price": Decimal("23000"), "discount": Decimal("0"), "line_total": Decimal("115000"), "condition": "BAIK"},
        {"line_number": 4, "confirmed_description": "sabun cuci piring", "quantity": Decimal("3"), "unit": "jerigen", "hps_unit_price": Decimal("79000"), "offer_unit_price": Decimal("79000"), "final_unit_price": Decimal("79000"), "discount": Decimal("0"), "line_total": Decimal("237000"), "condition": "BAIK"},
        {"line_number": 5, "confirmed_description": "pembersih porselin", "quantity": Decimal("3"), "unit": "galon", "hps_unit_price": Decimal("106000"), "offer_unit_price": Decimal("106000"), "final_unit_price": Decimal("106000"), "discount": Decimal("0"), "line_total": Decimal("318000"), "condition": "BAIK"},
        {"line_number": 6, "confirmed_description": "sabun cuci tangan cair", "quantity": Decimal("6"), "unit": "liter", "hps_unit_price": Decimal("45000"), "offer_unit_price": Decimal("45000"), "final_unit_price": Decimal("45000"), "discount": Decimal("0"), "line_total": Decimal("270000"), "condition": "BAIK"},
        {"line_number": 7, "confirmed_description": "kamper", "quantity": Decimal("5"), "unit": "bungkus", "hps_unit_price": Decimal("64000"), "offer_unit_price": Decimal("64000"), "final_unit_price": Decimal("64000"), "discount": Decimal("0"), "line_total": Decimal("320000"), "condition": "BAIK"},
        {"line_number": 8, "confirmed_description": "pengharum kloset", "quantity": Decimal("10"), "unit": "buah", "hps_unit_price": Decimal("23000"), "offer_unit_price": Decimal("23000"), "final_unit_price": Decimal("23000"), "discount": Decimal("0"), "line_total": Decimal("230000"), "condition": "BAIK"},
    ]
    subtotal = Decimal("2285000")
    tax_total = Decimal("251350")  # PPN 11% = 251,350
    grand_total = Decimal("2536350")

    result = run_deterministic_validation(
        school_snapshot=base_school,
        company_snapshot=base_company,
        tax_policy_snapshot=base_tax_policy,
        officials_snapshot=base_officials,
        lines=lines,
        events=base_events,
        doc_numbers=base_doc_numbers,
        subtotal=subtotal,
        tax_total=tax_total,
        grand_total=grand_total,
        fiscal_year=2026
    )

    assert result.passed is True
    assert result.error_count == 0


def test_dynamic_n_items_one_and_fifty(base_school, base_company, base_tax_policy, base_officials, base_doc_numbers, base_events):
    """PRD AT11: Tests dynamic item scaling (N=1 and N=50)."""
    # 1 Item test
    single_line = [
        {"line_number": 1, "confirmed_description": "Kertas HVS A4", "quantity": Decimal("10"), "unit": "rim", "hps_unit_price": Decimal("50000"), "offer_unit_price": Decimal("50000"), "final_unit_price": Decimal("50000"), "discount": Decimal("0"), "line_total": Decimal("500000"), "condition": "BAIK"}
    ]
    sub_1 = Decimal("500000")
    tax_1 = Decimal("55000")
    gt_1 = Decimal("555000")
    res_1 = run_deterministic_validation(
        school_snapshot=base_school,
        company_snapshot=base_company,
        tax_policy_snapshot=base_tax_policy,
        officials_snapshot=base_officials,
        lines=single_line,
        events=base_events,
        doc_numbers=base_doc_numbers,
        subtotal=sub_1,
        tax_total=tax_1,
        grand_total=gt_1,
        fiscal_year=2026
    )
    assert res_1.passed is True

    # 50 Items test
    fifty_lines = []
    tot = Decimal("0")
    for i in range(1, 51):
        line_tot = Decimal(i * 10000)
        tot += line_tot
        fifty_lines.append({
            "line_number": i,
            "confirmed_description": f"Item Alat Tulis {i}",
            "quantity": Decimal("1"),
            "unit": "buah",
            "hps_unit_price": line_tot,
            "offer_unit_price": line_tot,
            "final_unit_price": line_tot,
            "discount": Decimal("0"),
            "line_total": line_tot,
            "condition": "BAIK"
        })
    ppn_50 = Decimal(round(tot * Decimal("0.11")))
    gt_50 = tot + ppn_50
    res_50 = run_deterministic_validation(
        school_snapshot=base_school,
        company_snapshot=base_company,
        tax_policy_snapshot=base_tax_policy,
        officials_snapshot=base_officials,
        lines=fifty_lines,
        events=base_events,
        doc_numbers=base_doc_numbers,
        subtotal=tot,
        tax_total=ppn_50,
        grand_total=gt_50,
        fiscal_year=2026
    )
    assert res_50.passed is True


def test_entity_mismatch_br01(base_school, base_company, base_tax_policy, base_officials, base_doc_numbers, base_events):
    """Flags historical entity mismatch: CV Mitra Karya Gemilang detected on BAST/BAPP."""
    lines = [
        {"line_number": 1, "confirmed_description": "glass cleaner", "quantity": Decimal("1"), "unit": "liter", "hps_unit_price": Decimal("10000"), "offer_unit_price": Decimal("10000"), "final_unit_price": Decimal("10000"), "discount": Decimal("0"), "line_total": Decimal("10000"), "condition": "BAIK"}
    ]
    detected_entities = [
        {"type": "COMPANY", "name": "CV. MITRA KARYA GEMILANG", "sheet_name": "BAST", "cell_range": "B26"}
    ]
    res = run_deterministic_validation(
        school_snapshot=base_school,
        company_snapshot=base_company,
        tax_policy_snapshot=base_tax_policy,
        officials_snapshot=base_officials,
        lines=lines,
        events=base_events,
        doc_numbers=base_doc_numbers,
        subtotal=Decimal("10000"),
        tax_total=Decimal("1100"),
        grand_total=Decimal("11100"),
        fiscal_year=2026,
        detected_entities=detected_entities
    )
    assert res.passed is False
    assert any(f.rule_code == "BR01" and "MITRA KARYA GEMILANG" in f.original_value for f in res.findings)


def test_external_link_regex_br10(base_school, base_company, base_tax_policy, base_officials, base_doc_numbers, base_events):
    """Generic regex flags external workbook reference =[1]Sheet1!C24."""
    lines = [
        {"line_number": 1, "confirmed_description": "glass cleaner", "quantity": Decimal("1"), "unit": "liter", "hps_unit_price": Decimal("10000"), "offer_unit_price": Decimal("10000"), "final_unit_price": Decimal("10000"), "discount": Decimal("0"), "line_total": Decimal("10000"), "condition": "BAIK"}
    ]
    raw_formulas = [
        {"sheet_name": "HPS", "cell_range": "C17", "value": "=[1]Sheet1!C24"}
    ]
    res = run_deterministic_validation(
        school_snapshot=base_school,
        company_snapshot=base_company,
        tax_policy_snapshot=base_tax_policy,
        officials_snapshot=base_officials,
        lines=lines,
        events=base_events,
        doc_numbers=base_doc_numbers,
        subtotal=Decimal("10000"),
        tax_total=Decimal("1100"),
        grand_total=Decimal("11100"),
        fiscal_year=2026,
        raw_cells_or_formulas=raw_formulas
    )
    assert res.passed is False
    assert any(f.rule_code == "BR10" and "=[1]Sheet1!C24" in f.original_value for f in res.findings)


def test_date_chronology_br07(base_school, base_company, base_tax_policy, base_officials, base_doc_numbers):
    """Flags inverted date: Surat Pesanan dated 25 June 2026 after Surat Jalan 16 June 2026."""
    lines = [
        {"line_number": 1, "confirmed_description": "glass cleaner", "quantity": Decimal("1"), "unit": "liter", "hps_unit_price": Decimal("10000"), "offer_unit_price": Decimal("10000"), "final_unit_price": Decimal("10000"), "discount": Decimal("0"), "line_total": Decimal("10000"), "condition": "BAIK"}
    ]
    inverted_events = [
        {"event_code": "PESANAN", "event_date": date(2026, 6, 25)},
        {"event_code": "SURAT_JALAN", "event_date": date(2026, 6, 16)},
    ]
    res = run_deterministic_validation(
        school_snapshot=base_school,
        company_snapshot=base_company,
        tax_policy_snapshot=base_tax_policy,
        officials_snapshot=base_officials,
        lines=lines,
        events=inverted_events,
        doc_numbers=base_doc_numbers,
        subtotal=Decimal("10000"),
        tax_total=Decimal("1100"),
        grand_total=Decimal("11100"),
        fiscal_year=2026
    )
    assert res.passed is False
    assert any(f.rule_code == "BR07" for f in res.findings)
