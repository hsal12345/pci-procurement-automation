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

# Daftar Hari Libur Nasional Indonesia (SKB 3 Menteri 2025 & 2026) untuk deteksi BR12 / Bab 6 Tabel 6.1
INDONESIAN_NATIONAL_HOLIDAYS: Dict[str, str] = {
    # 2025
    "2025-01-01": "Tahun Baru 2025 Masehi",
    "2025-01-27": "Isra Mikraj Nabi Muhammad SAW",
    "2025-01-29": "Tahun Baru Imlek 2576 Kongzili",
    "2025-03-29": "Hari Suci Nyepi Tahun Baru Saka 1947",
    "2025-03-31": "Hari Raya Idulfitri 1446 H",
    "2025-04-01": "Hari Raya Idulfitri 1446 H",
    "2025-04-18": "Wafat Yesus Kristus",
    "2025-04-20": "Kebangkitan Yesus Kristus (Paskah)",
    "2025-05-01": "Hari Buruh Internasional",
    "2025-05-12": "Hari Raya Waisak 2569 BE",
    "2025-05-29": "Kenaikan Yesus Kristus",
    "2025-06-01": "Hari Lahir Pancasila",
    "2025-06-06": "Hari Raya Iduladha 1446 H",
    "2025-06-27": "Tahun Baru Islam 1447 H",
    "2025-08-17": "Hari Kemerdekaan Republik Indonesia",
    "2025-09-05": "Maulid Nabi Muhammad SAW",
    "2025-12-25": "Hari Raya Natal",
    # 2026
    "2026-01-01": "Tahun Baru 2026 Masehi",
    "2026-01-16": "Isra Mikraj Nabi Muhammad SAW",
    "2026-02-17": "Tahun Baru Imlek 2577 Kongzili",
    "2026-03-19": "Hari Suci Nyepi Tahun Baru Saka 1948",
    "2026-03-20": "Hari Raya Idulfitri 1447 H (Hari Pertama)",
    "2026-03-21": "Hari Raya Idulfitri 1447 H (Hari Kedua)",
    "2026-04-03": "Wafat Yesus Kristus",
    "2026-04-05": "Kebangkitan Yesus Kristus (Paskah)",
    "2026-05-01": "Hari Buruh Internasional",
    "2026-05-14": "Kenaikan Yesus Kristus",
    "2026-05-27": "Hari Raya Iduladha 1447 H",
    "2026-05-31": "Hari Raya Waisak 2570 BE",
    "2026-06-01": "Hari Lahir Pancasila",
    "2026-06-16": "Tahun Baru Islam 1448 H",
    "2026-08-17": "Hari Kemerdekaan Republik Indonesia",
    "2026-08-25": "Maulid Nabi Muhammad SAW",
    "2026-12-25": "Hari Raya Natal",
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
    """BR12 Holiday or Unusual Date (Bab 6 Tabel 6.1):
    Flags dates that fall on weekends (Saturday/Sunday) or Indonesian national holidays
    as a WARNING requiring recorded reason.
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
            holiday_name = INDONESIAN_NATIONAL_HOLIDAYS.get(d.isoformat())
            if holiday_name:
                findings.append(RuleFinding(
                    rule_code="BR12",
                    severity=SeverityEnum.WARNING,
                    field_name=f"events[{code}].event_date",
                    original_value=f"{d} ({holiday_name})",
                    message=(
                        f"Peringatan kalender hari libur nasional (BR12): Tanggal untuk tahapan '{code}' ({d}) "
                        f"jatuh pada Hari Libur Nasional ({holiday_name}). Pastikan terdapat alasan operasional yang sah."
                    )
                ))
            elif weekday in [5, 6]:
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
