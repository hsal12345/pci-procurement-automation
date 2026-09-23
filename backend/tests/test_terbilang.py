import pytest
from decimal import Decimal
from app.core.terbilang import terbilang, terbilang_number


def test_terbilang_zero():
    assert terbilang(0) == "Nol Rupiah"
    assert terbilang("0") == "Nol Rupiah"
    assert terbilang(Decimal("0.0000")) == "Nol Rupiah"


def test_terbilang_basic_units():
    assert terbilang(1) == "Satu Rupiah"
    assert terbilang(10) == "Sepuluh Rupiah"
    assert terbilang(11) == "Sebelas Rupiah"
    assert terbilang(12) == "Dua Belas Rupiah"
    assert terbilang(20) == "Dua Puluh Rupiah"
    assert terbilang(21) == "Dua Puluh Satu Rupiah"
    assert terbilang(100) == "Seratus Rupiah"
    assert terbilang(101) == "Seratus Satu Rupiah"
    assert terbilang(111) == "Seratus Sebelas Rupiah"
    assert terbilang(150) == "Seratus Lima Puluh Rupiah"
    assert terbilang(200) == "Dua Ratus Rupiah"


def test_terbilang_thousands():
    assert terbilang(1000) == "Seribu Rupiah"
    assert terbilang(1500) == "Seribu Lima Ratus Rupiah"
    assert terbilang(2000) == "Dua Ribu Rupiah"
    assert terbilang(10000) == "Sepuluh Ribu Rupiah"
    assert terbilang(11000) == "Sebelas Ribu Rupiah"
    assert terbilang(100000) == "Seratus Ribu Rupiah"


def test_terbilang_reference_kk09():
    # In 4 PCI KK09.xlsx sheet KWITANSI C14:
    # Dua Juta Lima Ratus Tiga Puluh Enam Ribu Tiga Ratus Lima Puluh Rupiah
    amount = 2536350
    expected = "Dua Juta Lima Ratus Tiga Puluh Enam Ribu Tiga Ratus Lima Puluh Rupiah"
    assert terbilang(amount) == expected
    assert terbilang(Decimal("2536350.0000")) == expected


def test_terbilang_large_numbers():
    assert terbilang(1000000) == "Satu Juta Rupiah"
    assert terbilang(1000000000) == "Satu Miliar Rupiah"
    assert terbilang(1000000000000) == "Satu Triliun Rupiah"
