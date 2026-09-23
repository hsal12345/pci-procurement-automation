"""OS-Agnostic, thread-safe Indonesian date and currency formatting utilities."""
from datetime import date, datetime
from decimal import Decimal
from typing import Union
from app.core.terbilang import terbilang_number

BULAN_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

HARI_ID = {
    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
    4: "Jumat", 5: "Sabtu", 6: "Minggu"
}


def parse_date(d: Union[date, datetime, str, None]) -> date:
    """Safely converts date, datetime, or ISO string to date object."""
    if d is None:
        return date.today()
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        # handle "2026-06-25" or "2026-06-25T00:00:00"
        clean = d.split("T")[0].split(" ")[0]
        try:
            return date.fromisoformat(clean)
        except ValueError:
            return date.today()
    return date.today()


def format_date_id(d: Union[date, datetime, str, None]) -> str:
    """Formats date to standard Indonesian convention, e.g. '25 Juni 2026'."""
    dt = parse_date(d)
    return f"{dt.day} {BULAN_ID[dt.month]} {dt.year}"


def format_day_date_id(d: Union[date, datetime, str, None]) -> str:
    """Formats date with Indonesian day name, e.g. 'Kamis, 25 Juni 2026'."""
    dt = parse_date(d)
    return f"{HARI_ID[dt.weekday()]}, {dt.day} {BULAN_ID[dt.month]} {dt.year}"


def format_formal_narrative_date(d: Union[date, datetime, str, None]) -> str:
    """Formats date into official Indonesian legal opening text:
    'Pada hari ini, [Hari] Tanggal [Terbilang Hari] bulan [Bulan] Tahun [Terbilang Tahun]'
    Example:
    'Pada hari ini, Selasa Tanggal Enam Belas bulan Juni Tahun Dua Ribu Dua Puluh Enam'
    """
    dt = parse_date(d)
    day_name = HARI_ID[dt.weekday()]
    day_words = terbilang_number(dt.day)
    month_name = BULAN_ID[dt.month]
    year_words = terbilang_number(dt.year)
    return f"Pada hari ini, {day_name} Tanggal {day_words} bulan {month_name} Tahun {year_words}"


def format_idr(
    amount: Union[Decimal, float, int, str, None],
    with_prefix: bool = True,
    with_cents: bool = False
) -> str:
    """Formats numeric value as standard Indonesian currency string:
    e.g. 'Rp 2.536.350' or '2.536.350'.
    """
    if amount is None:
        val = Decimal("0")
    else:
        try:
            val = Decimal(str(amount))
        except Exception:
            val = Decimal("0")

    if with_cents:
        # e.g. 2.536.350,00
        integer_part = int(val)
        cents = int((abs(val) - abs(integer_part)) * 100)
        formatted_int = f"{integer_part:,}".replace(",", ".")
        res = f"{formatted_int},{cents:02d}"
    else:
        # round to nearest Rupiah
        integer_part = int(val.quantize(Decimal("1")))
        res = f"{integer_part:,}".replace(",", ".")

    prefix = "Rp " if with_prefix else ""
    return f"{prefix}{res}"
