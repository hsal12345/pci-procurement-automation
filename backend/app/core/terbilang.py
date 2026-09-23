"""Indonesian currency terbilang algorithm.
Converts integer or decimal money amounts into formal Indonesian currency words.
Example:
    2536350 -> "Dua Juta Lima Ratus Tiga Puluh Enam Ribu Tiga Ratus Lima Puluh Rupiah"
    0 -> "Nol Rupiah"
"""
from decimal import Decimal
from typing import Union

UNITS = [
    "", "Satu", "Dua", "Tiga", "Empat", "Lima",
    "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"
]


def _spell_under_thousand(n: int) -> str:
    """Spells any integer 1 <= n < 1000 in Indonesian."""
    if n == 0:
        return ""
    if n < 12:
        return UNITS[n]
    if n < 20:
        return f"{UNITS[n - 10]} Belas"
    if n < 100:
        remainder = n % 10
        rem_str = f" {UNITS[remainder]}" if remainder > 0 else ""
        return f"{UNITS[n // 10]} Puluh{rem_str}"
    if n < 200:
        remainder = n - 100
        rem_str = f" {_spell_under_thousand(remainder)}" if remainder > 0 else ""
        return f"Seratus{rem_str}"
    if n < 1000:
        remainder = n % 100
        rem_str = f" {_spell_under_thousand(remainder)}" if remainder > 0 else ""
        return f"{UNITS[n // 100]} Ratus{rem_str}"
    return ""


def terbilang_number(n: int) -> str:
    """Spells an arbitrary non-negative integer into Indonesian text."""
    if n == 0:
        return "Nol"

    chunks = []
    
    # Triliun (10^12)
    if n >= 1_000_000_000_000:
        triliun = n // 1_000_000_000_000
        chunks.append(f"{_spell_under_thousand(triliun)} Triliun")
        n %= 1_000_000_000_000

    # Miliar (10^9)
    if n >= 1_000_000_000:
        miliar = n // 1_000_000_000
        chunks.append(f"{_spell_under_thousand(miliar)} Miliar")
        n %= 1_000_000_000

    # Juta (10^6)
    if n >= 1_000_000:
        juta = n // 1_000_000
        chunks.append(f"{_spell_under_thousand(juta)} Juta")
        n %= 1_000_000

    # Ribu (10^3)
    if n >= 1_000:
        ribu = n // 1_000
        if ribu == 1:
            chunks.append("Seribu")
        else:
            chunks.append(f"{_spell_under_thousand(ribu)} Ribu")
        n %= 1_000

    # Under 1,000
    if n > 0:
        chunks.append(_spell_under_thousand(n))

    return " ".join(chunks).strip()


def terbilang(amount: Union[int, float, Decimal, str]) -> str:
    """Converts a currency amount to Indonesian Rupiah words.
    Handles 0 explicitly as 'Nol Rupiah'.
    Rounds to nearest whole Rupiah per standard Indonesian procurement conventions.
    """
    if amount is None:
        return "Nol Rupiah"

    # Convert to Decimal for exact arithmetic
    try:
        val = Decimal(str(amount))
    except Exception:
        return "Nol Rupiah"

    # Explicit base condition for zero
    if val == 0:
        return "Nol Rupiah"

    # Check for negative
    prefix = ""
    if val < 0:
        prefix = "Minus "
        val = abs(val)

    # Round to nearest integer IDR
    rounded_val = int(val.quantize(Decimal("1")))
    
    if rounded_val == 0:
        return "Nol Rupiah"

    words = terbilang_number(rounded_val)
    return f"{prefix}{words} Rupiah".strip()
