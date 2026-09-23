from datetime import date
from typing import List, Dict, Any, Optional
from app.core.rules.base import RuleFinding
from app.schemas.common import SeverityEnum

# Standard Indonesian Government Procurement Chronology DAG
# Stage index order (lower index means earlier or same-day event)
EVENT_STAGE_ORDER = {
    "HPS": 1,
    "SPP": 1,
    "PENAWARAN": 2,
    "NEGOSIASI": 3,
    "PESANAN": 4,
    "SURAT_JALAN": 5,
    "BAPB": 6,
    "BAST": 7,
    "BAST_REKANAN": 7,
    "BAPP": 8,
    "FAKTUR": 9,
    "KWITANSI": 9,
}

INDONESIAN_DAY_NAMES = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu"
}


def validate_br07_date_chronology(
    events: List[Dict[str, Any]],
    fiscal_year: Optional[int] = None
) -> List[RuleFinding]:
    """BR07 Date Chronology:
    Validates that procurement document events strictly follow the legal sequence:
    [HPS, SPP] <= Penawaran <= Negosiasi <= Pesanan <= Surat Jalan <= BAPB <= BAST <= BAPP <= Faktur / Kwitansi.
    Flags any backwards date (e.g. Surat Pesanan 25 June after Surat Jalan 16 June, or 2025 date).
    """
    findings: List[RuleFinding] = []

    # Map of event_code -> date object
    event_dates: Dict[str, date] = {}
    for ev in events:
        raw_code = (ev.get("event_code") or "").upper().strip()
        # Canonical alias mapping
        if raw_code in ("SPN",):
            code = "PENAWARAN"
        elif raw_code in ("BA_KLARIFIKASI",):
            code = "NEGOSIASI"
        elif raw_code in ("SP",):
            code = "PESANAN"
        elif raw_code in ("SJ",):
            code = "SURAT_JALAN"
        else:
            code = raw_code

        d = ev.get("event_date")
        if isinstance(d, str):
            try:
                d = date.fromisoformat(d)
            except ValueError:
                d = None
        if code and d:
            event_dates[code] = d

    # Stage 9 (Settlement / Penagihan): FAKTUR and KWITANSI occur on the final payment stage
    # If FAKTUR was moved forward but KWITANSI was left at an older date, sync KWITANSI
    if "FAKTUR" in event_dates and "KWITANSI" in event_dates:
        if event_dates["KWITANSI"] < event_dates["FAKTUR"]:
            event_dates["KWITANSI"] = event_dates["FAKTUR"]
    elif "FAKTUR" in event_dates and "KWITANSI" not in event_dates:
        event_dates["KWITANSI"] = event_dates["FAKTUR"]
    elif "KWITANSI" in event_dates and "FAKTUR" not in event_dates:
        event_dates["FAKTUR"] = event_dates["KWITANSI"]

    # 1. Check fiscal year consistency
    if fiscal_year:
        for code, dt in event_dates.items():
            if dt.year != fiscal_year:
                findings.append(RuleFinding(
                    rule_code="BR07",
                    severity=SeverityEnum.BLOCK,
                    field_name=f"events[{code}].event_date",
                    original_value=str(dt),
                    proposed_value=f"Tahun {fiscal_year}",
                    message=(
                        f"Inkonsistensi tahun anggaran pada dokumen '{code}': tanggal tercatat {dt} "
                        f"berada di luar tahun anggaran transaksi ({fiscal_year})."
                    )
                ))

    # 2. Check chronological sequence between pairs
    # For every pair where stage(A) < stage(B), date(A) must be <= date(B)
    for code_a, stage_a in EVENT_STAGE_ORDER.items():
        if code_a not in event_dates:
            continue
        date_a = event_dates[code_a]

        for code_b, stage_b in EVENT_STAGE_ORDER.items():
            if code_b not in event_dates:
                continue
            if stage_a < stage_b:
                date_b = event_dates[code_b]
                if date_a > date_b:
                    findings.append(RuleFinding(
                        rule_code="BR07",
                        severity=SeverityEnum.BLOCK,
                        field_name="event_date_sequence",
                        original_value=f"{code_a}={date_a}, {code_b}={date_b}",
                        message=(
                            f"Pelanggaran kronologis urutan tanggal: dokumen '{code_a}' (tanggal {date_a}) "
                            f"terjadi setelah dokumen lanjutan '{code_b}' (tanggal {date_b}). "
                            f"Secara regulasi, {code_a} harus mendahului atau sama dengan {code_b}."
                        )
                    ))

    return findings


def validate_br12_holiday_or_unusual_date(
    events: List[Dict[str, Any]]
) -> List[RuleFinding]:
    """BR12 Holiday or Unusual Date:
    Flags dates that fall on weekends (Saturday/Sunday) as a WARNING requiring recorded reason.
    """
    findings: List[RuleFinding] = []

    for ev in events:
        code = (ev.get("event_code") or "").upper()
        d = ev.get("event_date")
        if isinstance(d, str):
            try:
                d = date.fromisoformat(d)
            except ValueError:
                d = None

        if d and isinstance(d, date):
            weekday = d.weekday()  # 5=Saturday, 6=Sunday
            if weekday in [5, 6]:
                day_name = INDONESIAN_DAY_NAMES.get(weekday, "Akhir Pekan")
                findings.append(RuleFinding(
                    rule_code="BR12",
                    severity=SeverityEnum.WARNING,
                    field_name=f"events[{code}].event_date",
                    original_value=f"{d} ({day_name})",
                    message=(
                        f"Peringatan tanggal: Dokumen '{code}' bertanggal {d} jatuh pada hari {day_name} "
                        f"(hari libur/akhir pekan). Pastikan terdapat alasan operasional yang sah."
                    )
                ))

    return findings
