from decimal import Decimal
from typing import Any, Dict, List, Union
from app.core.terbilang import terbilang
from app.services.export.date_helpers import (
    format_date_id,
    format_day_date_id,
    format_formal_narrative_date,
    format_idr,
    parse_date,
)


def build_generation_context(
    revision: Any,
    package: Any = None,
    is_draft: bool = False
) -> Dict[str, Any]:
    """Extracts and formats all frozen snapshot data, lines, events, and numbers
    into a standardized, rich context dictionary usable by Excel, Word, and PDF generators.
    """
    # 1. Handle ORM vs dict for revision
    if hasattr(revision, "school_snapshot"):
        school_snap = revision.school_snapshot or {}
        company_snap = revision.company_snapshot or {}
        tax_snap = revision.tax_policy_snapshot or []
        officials_snap = revision.officials_snapshot or []
        rev_lines = list(revision.lines) if hasattr(revision, "lines") else []
        rev_events = list(revision.events) if hasattr(revision, "events") else []
        rev_numbers = list(revision.numbers) if hasattr(revision, "numbers") else []
        subtotal = Decimal(str(revision.subtotal or 0))
        tax_total = Decimal(str(revision.tax_total or 0))
        grand_total = Decimal(str(revision.grand_total or 0))
        pkg_obj = package or (revision.package if hasattr(revision, "package") else None)
        pkg_number = pkg_obj.package_number if pkg_obj else "PKG/UNKNOWN"
        fiscal_year = pkg_obj.fiscal_year if pkg_obj else 2026
        quarter = pkg_obj.quarter if pkg_obj else 2
        rev_number = revision.revision_number if hasattr(revision, "revision_number") else 1
    else:
        school_snap = revision.get("school_snapshot") or {}
        company_snap = revision.get("company_snapshot") or {}
        tax_snap = revision.get("tax_policy_snapshot") or []
        officials_snap = revision.get("officials_snapshot") or []
        rev_lines = revision.get("lines") or []
        rev_events = revision.get("events") or []
        rev_numbers = revision.get("numbers") or []
        subtotal = Decimal(str(revision.get("subtotal") or 0))
        tax_total = Decimal(str(revision.get("tax_total") or 0))
        grand_total = Decimal(str(revision.get("grand_total") or 0))
        pkg_number = revision.get("package_number") or "PKG/UNKNOWN"
        fiscal_year = revision.get("fiscal_year") or 2026
        quarter = revision.get("quarter") or 2
        rev_number = revision.get("revision_number") or 1

    # 2. Extract Officials
    officials_map: Dict[str, Dict[str, Any]] = {}
    for off in officials_snap:
        if isinstance(off, dict):
            role = off.get("role") or "UNKNOWN"
            officials_map[role] = off
        else:
            role = getattr(off, "role", "UNKNOWN")
            officials_map[role] = {
                "role": role,
                "name": getattr(off, "name", ""),
                "nip": getattr(off, "nip", ""),
                "position": getattr(off, "position", ""),
            }

    # Extract Primary Key Roles with fallbacks
    kepala_sekolah = officials_map.get("KEPALA_SEKOLAH", {
        "name": school_snap.get("principal_name") or "Drs. Mulyadi",
        "nip": school_snap.get("principal_nip") or "19680512 199303 1 005",
        "position": "Kepala Sekolah"
    })
    pejabat_pengadaan = officials_map.get("PEJABAT_PENGADAAN", {
        "name": "Budi Santoso, S.Pd",
        "nip": "19750814 200112 1 002",
        "position": "Pejabat Pengadaan"
    })
    pphp_ketua = officials_map.get("PPHP_KETUA", {
        "name": "Siti Rahayu, S.Pd",
        "nip": "19800321 200501 2 008",
        "position": "Ketua PPHP"
    })
    pphp_sekretaris = officials_map.get("PPHP_SEKRETARIS", {
        "name": "Ahmad Fauzi, S.Pd",
        "nip": "19841105 200902 1 003",
        "position": "Sekretaris PPHP"
    })
    pphp_anggota = officials_map.get("PPHP_ANGGOTA", {
        "name": "Dewi Sartika, S.Pd",
        "nip": "19880719 201101 2 015",
        "position": "Anggota PPHP"
    })
    pengurus_barang = officials_map.get("PENGURUS_BARANG", {
        "name": "Hendra Wijaya",
        "nip": "19820415 200801 1 009",
        "position": "Pengurus Barang"
    })

    # 3. Extract Events
    events_map: Dict[str, Dict[str, Any]] = {}
    for ev in rev_events:
        if isinstance(ev, dict):
            code = ev.get("event_code") or ""
            dt_raw = ev.get("event_date")
            loc = ev.get("location") or "Jakarta"
        else:
            code = getattr(ev, "event_code", "")
            dt_raw = getattr(ev, "event_date", None)
            loc = getattr(ev, "location", "Jakarta")

        dt = parse_date(dt_raw)
        events_map[code] = {
            "event_code": code,
            "raw_date": dt,
            "date_id": format_date_id(dt),
            "day_date_id": format_day_date_id(dt),
            "narrative_id": format_formal_narrative_date(dt),
            "location": loc,
        }

    # Ensure all standard events have fallbacks
    standard_events = [
        "HPS", "SPP", "PENAWARAN", "NEGOSIASI", "PESANAN",
        "SURAT_JALAN", "BAPB", "BAST", "BAST_REKANAN", "BAPP",
        "FAKTUR", "KWITANSI"
    ]
    for ev_code in standard_events:
        if ev_code not in events_map:
            d_today = parse_date(None)
            events_map[ev_code] = {
                "event_code": ev_code,
                "raw_date": d_today,
                "date_id": format_date_id(d_today),
                "day_date_id": format_day_date_id(d_today),
                "narrative_id": format_formal_narrative_date(d_today),
                "location": "Jakarta",
            }

    # 4. Extract Numbers
    numbers_map: Dict[str, Dict[str, Any]] = {}
    for num in rev_numbers:
        if isinstance(num, dict):
            code = num.get("doc_code") or ""
            doc_no = num.get("doc_number") or ""
            iss = num.get("issuer") or "COMPANY"
        else:
            code = getattr(num, "doc_code", "")
            doc_no = getattr(num, "doc_number", "")
            iss = getattr(num, "issuer", "COMPANY")

        numbers_map[code] = {
            "doc_code": code,
            "doc_number": doc_no,
            "issuer": iss,
        }

    # Ensure all 13 standard documents have fallbacks
    for idx in range(1, 14):
        code = f"D{idx:02d}"
        if code not in numbers_map:
            numbers_map[code] = {
                "doc_code": code,
                "doc_number": f"{idx:02d}/DOC/{fiscal_year}",
                "issuer": "SCHOOL" if idx in [1, 2, 4, 5, 7, 9, 10, 11, 12] else "COMPANY",
            }

    # 5. Extract & Format Items
    items_list: List[Dict[str, Any]] = []
    for idx, l in enumerate(rev_lines, start=1):
        if isinstance(l, dict):
            line_no = l.get("line_number") or idx
            desc = l.get("confirmed_description") or l.get("original_description") or f"Item {idx}"
            spec = l.get("specification") or "-"
            qty = Decimal(str(l.get("quantity") or 1))
            unit = l.get("unit") or "Buah"
            hps_p = Decimal(str(l.get("hps_unit_price") or 0))
            offer_p = Decimal(str(l.get("offer_unit_price") or 0))
            final_p = Decimal(str(l.get("final_unit_price") or 0))
            disc = Decimal(str(l.get("discount") or 0))
            line_tot = Decimal(str(l.get("line_total") or (qty * final_p - disc)))
            cond = l.get("condition") or "BAIK"
            notes = l.get("notes") or ""
        else:
            line_no = getattr(l, "line_number", idx)
            desc = getattr(l, "confirmed_description", None) or getattr(l, "original_description", f"Item {idx}")
            spec = getattr(l, "specification", "-") or "-"
            qty = Decimal(str(getattr(l, "quantity", 1)))
            unit = getattr(l, "unit", "Buah")
            hps_p = Decimal(str(getattr(l, "hps_unit_price", 0)))
            offer_p = Decimal(str(getattr(l, "offer_unit_price", 0)))
            final_p = Decimal(str(getattr(l, "final_unit_price", 0)))
            disc = Decimal(str(getattr(l, "discount", 0)))
            line_tot = Decimal(str(getattr(l, "line_total", (qty * final_p - disc))))
            cond = getattr(l, "condition", "BAIK")
            notes = getattr(l, "notes", "") or ""

        hps_tot = qty * hps_p
        offer_tot = qty * offer_p

        items_list.append({
            "no": line_no,
            "name": desc,
            "spec": spec,
            "volume": int(qty) if qty == int(qty) else float(qty),
            "unit": unit,
            "hps_price": hps_p,
            "hps_price_formatted": format_idr(hps_p, with_prefix=False),
            "hps_total": hps_tot,
            "hps_total_formatted": format_idr(hps_tot, with_prefix=False),
            "offer_price": offer_p,
            "offer_price_formatted": format_idr(offer_p, with_prefix=False),
            "offer_total": offer_tot,
            "offer_total_formatted": format_idr(offer_tot, with_prefix=False),
            "final_price": final_p,
            "final_price_formatted": format_idr(final_p, with_prefix=False),
            "line_total": line_tot,
            "line_total_formatted": format_idr(line_tot, with_prefix=False),
            "discount": disc,
            "condition": cond,
            "notes": notes,
        })

    # 6. Totals and Terbilang
    terbilang_str = terbilang(grand_total)

    # Also ensure lines list has dictionary entries for ExcelPackageGenerator
    dict_lines = []
    for l in rev_lines:
        if isinstance(l, dict):
            dict_lines.append(l)
        else:
            dict_lines.append({
                "line_number": getattr(l, "line_number", 1),
                "original_description": getattr(l, "original_description", ""),
                "confirmed_description": getattr(l, "confirmed_description", None) or getattr(l, "original_description", ""),
                "specification": getattr(l, "specification", "-"),
                "quantity": getattr(l, "quantity", 1),
                "unit": getattr(l, "unit", "Buah"),
                "hps_unit_price": getattr(l, "hps_unit_price", 0),
                "offer_unit_price": getattr(l, "offer_unit_price", 0),
                "final_unit_price": getattr(l, "final_unit_price", 0),
                "discount": getattr(l, "discount", 0),
                "line_total": getattr(l, "line_total", 0),
                "condition": getattr(l, "condition", "BAIK"),
                "notes": getattr(l, "notes", ""),
            })

    return {
        "is_draft": is_draft,
        "draft_banner": "[ DOKUMEN DRAFT - BELUM DISETUJUI KEUANGAN ]" if is_draft else "",
        "package": {
            "number": pkg_number,
            "fiscal_year": fiscal_year,
            "quarter": quarter,
            "revision_number": rev_number,
        },
        "school": {
            "name": school_snap.get("name") or "SDN KEBON KOSONG 09",
            "npsn": school_snap.get("npsn") or "20108304",
            "address": school_snap.get("address") or "Jl. Kebon Kosong I No. 1",
            "subdistrict": school_snap.get("subdistrict") or "Kemayoran",
            "city": school_snap.get("city") or "Jakarta Pusat",
            "province": school_snap.get("province") or "DKI Jakarta",
            "postal_code": school_snap.get("postal_code") or "10630",
            "phone": school_snap.get("phone") or "021-4240000",
            "email": school_snap.get("email") or "sdnkebonkosong09@jakarta.go.id",
            "principal_name": kepala_sekolah["name"],
            "principal_nip": kepala_sekolah["nip"],
        },
        "company": {
            "legal_name": company_snap.get("legal_name") or "CV. PUSTAKA CEMERLANG INDONESIA",
            "director_name": company_snap.get("director_name") or "Bambang Solifian",
            "address": company_snap.get("address") or "Jl. Raya Bekasi KM 24 Jakarta",
            "city": company_snap.get("city") or "Jakarta",
            "phone": company_snap.get("phone") or "021-8888888",
            "npwp": company_snap.get("npwp") or "01.234.567.8-012.000",
            "bank_name": company_snap.get("bank_name") or "BANK DKI",
            "bank_account_number": company_snap.get("bank_account_number") or "300.21.00000.1",
            "bank_account_name": company_snap.get("bank_account_name") or "CV PUSTAKA CEMERLANG INDONESIA",
        },
        "officials": {
            "kepala_sekolah": kepala_sekolah,
            "pejabat_pengadaan": pejabat_pengadaan,
            "pphp_ketua": pphp_ketua,
            "pphp_sekretaris": pphp_sekretaris,
            "pphp_anggota": pphp_anggota,
            "pengurus_barang": pengurus_barang,
        },
        "events": events_map,
        "numbers": numbers_map,
        "items": items_list,
        "totals": {
            "subtotal": subtotal,
            "subtotal_formatted": format_idr(subtotal, with_prefix=False),
            "tax_total": tax_total,
            "tax_formatted": format_idr(tax_total, with_prefix=False),
            "grand_total": grand_total,
            "grand_total_formatted": format_idr(grand_total, with_prefix=False),
            "terbilang": terbilang_str,
        },
        # Raw references preserved for backward compatibility
        "school_snapshot": school_snap,
        "company_snapshot": company_snap,
        "tax_policy_snapshot": tax_snap,
        "officials_snapshot": officials_snap,
        "lines": dict_lines,
        "subtotal": subtotal,
        "tax_total": tax_total,
        "grand_total": grand_total,
        "terbilang_grand_total": terbilang_str,
    }
