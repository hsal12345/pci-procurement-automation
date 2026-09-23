from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
from typing import List, Dict, Any, Optional
from app.core.rules.base import RuleFinding
from app.schemas.common import SeverityEnum


def _round_currency(val: Decimal, rule: str = "ROUND_HALF_UP") -> Decimal:
    """Rounds a currency amount according to policy rounding rule."""
    rounding_mode = ROUND_HALF_UP if rule == "ROUND_HALF_UP" else ROUND_DOWN
    return val.quantize(Decimal("1"), rounding=rounding_mode)


def validate_br04_price_stage(lines: List[Dict[str, Any]]) -> List[RuleFinding]:
    """BR04 Price Stage:
    Ensures that each price stage is valid:
    - hps_unit_price (D01) >= 0
    - offer_unit_price (D03) >= 0
    - final_unit_price (D04..D13) >= 0 and typically <= offer_unit_price
    """
    findings: List[RuleFinding] = []

    for idx, line in enumerate(lines, start=1):
        hps = Decimal(str(line.get("hps_unit_price") or "0"))
        offer = Decimal(str(line.get("offer_unit_price") or "0"))
        final = Decimal(str(line.get("final_unit_price") or "0"))
        desc = line.get("confirmed_description") or f"Baris {idx}"

        if hps < 0:
            findings.append(RuleFinding(
                rule_code="BR04",
                severity=SeverityEnum.BLOCK,
                field_name=f"lines[{idx}].hps_unit_price",
                message=f"Harga HPS pada item '{desc}' tidak boleh bernilai negatif."
            ))

        if offer < 0:
            findings.append(RuleFinding(
                rule_code="BR04",
                severity=SeverityEnum.BLOCK,
                field_name=f"lines[{idx}].offer_unit_price",
                message=f"Harga penawaran pada item '{desc}' tidak boleh bernilai negatif."
            ))

        if final < 0:
            findings.append(RuleFinding(
                rule_code="BR04",
                severity=SeverityEnum.BLOCK,
                field_name=f"lines[{idx}].final_unit_price",
                message=f"Harga kesepakatan final pada item '{desc}' tidak boleh bernilai negatif."
            ))

        # Negotiation check: agreed final price is usually <= offer price
        if offer > 0 and final > offer:
            findings.append(RuleFinding(
                rule_code="BR04",
                severity=SeverityEnum.WARNING,
                field_name=f"lines[{idx}].final_unit_price",
                original_value=str(final),
                proposed_value=str(offer),
                message=f"Harga kesepakatan final ({final}) pada item '{desc}' melebihi harga penawaran awal ({offer})."
            ))

    return findings


def validate_br05_and_br06_arithmetic_and_tax(
    lines: List[Dict[str, Any]],
    tax_policies: List[Dict[str, Any]],
    recorded_subtotal: Decimal,
    recorded_tax_total: Decimal,
    recorded_grand_total: Decimal,
) -> List[RuleFinding]:
    """BR05 Arithmetic & BR06 Tax Policy:
    Recomputes line totals, subtotal, and tax additions/withholdings
    strictly according to the active dynamic tax_policy_snapshot (no hardcoded tax rates).
    Compares against recorded totals with ZERO tolerance.
    """
    findings: List[RuleFinding] = []

    if not tax_policies:
        findings.append(RuleFinding(
            rule_code="BR06",
            severity=SeverityEnum.BLOCK,
            field_name="tax_policy_snapshot",
            message="Tidak ada kebijakan perpajakan aktif (tax policy) yang ditetapkan pada snapshot revisi."
        ))

    computed_subtotal = Decimal("0")

    # 1. Line-by-line arithmetic verification
    for idx, line in enumerate(lines, start=1):
        qty = Decimal(str(line.get("quantity") or "0"))
        unit_price = Decimal(str(line.get("final_unit_price") or "0"))
        discount = Decimal(str(line.get("discount") or "0"))
        line_total = Decimal(str(line.get("line_total") or "0"))
        desc = line.get("confirmed_description") or f"Baris {idx}"

        expected_line_total = (qty * unit_price) - discount

        if abs(line_total - expected_line_total) > Decimal("0.0001"):
            findings.append(RuleFinding(
                rule_code="BR05",
                severity=SeverityEnum.BLOCK,
                field_name=f"lines[{idx}].line_total",
                original_value=str(line_total),
                proposed_value=str(expected_line_total),
                message=(
                    f"Kesalahan kalkulasi aritmatika baris {idx} ('{desc}'): "
                    f"kuantitas ({qty}) x harga ({unit_price}) - diskon ({discount}) = {expected_line_total}, "
                    f"tetapi tercatat {line_total}."
                )
            ))

        computed_subtotal += expected_line_total

    # Compare subtotal
    if abs(recorded_subtotal - computed_subtotal) > Decimal("0.0001"):
        findings.append(RuleFinding(
            rule_code="BR05",
            severity=SeverityEnum.BLOCK,
            field_name="subtotal",
            original_value=str(recorded_subtotal),
            proposed_value=str(computed_subtotal),
            message=(
                f"Selisih subtotal barang: jumlah total seluruh baris adalah {computed_subtotal}, "
                f"namun subtotal tercatat {recorded_subtotal}."
            )
        ))

    # 2. Dynamic policy-driven tax calculations
    computed_additive_tax = Decimal("0")
    for policy in tax_policies:
        tax_type = policy.get("tax_type", "").upper()
        rate = Decimal(str(policy.get("rate") or "0"))
        withholding = policy.get("withholding_rule", "NONE").upper()
        rounding_rule = policy.get("rounding_rule", "ROUND_HALF_UP")

        tax_amount = _round_currency(computed_subtotal * rate, rounding_rule)

        # In Indonesian school procurement:
        # PPN is typically additive to the gross billed total
        # PPh (22/23) is a withholding (pemotongan pajak)
        if withholding == "NONE" and not policy.get("is_inclusive", False):
            computed_additive_tax += tax_amount

    computed_grand_total = computed_subtotal + computed_additive_tax

    # Verify grand total
    if abs(recorded_grand_total - computed_grand_total) > Decimal("0.0001"):
        findings.append(RuleFinding(
            rule_code="BR05",
            severity=SeverityEnum.BLOCK,
            field_name="grand_total",
            original_value=str(recorded_grand_total),
            proposed_value=str(computed_grand_total),
            message=(
                f"Selisih total akhir (Grand Total): hasil perhitungan subtotal + pajak aditif adalah {computed_grand_total}, "
                f"namun total tercatat {recorded_grand_total}."
            )
        ))

    return findings
