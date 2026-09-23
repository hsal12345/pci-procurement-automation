from decimal import Decimal
from typing import List, Dict, Any, Optional
from app.core.rules.base import RuleFinding
from app.core.rules.identity import validate_br01_identity_consistency, validate_br09_signatories
from app.core.rules.completeness import (
    validate_br02_completeness,
    validate_br03_item_coverage,
    validate_br10_external_and_stale_references,
)
from app.core.rules.pricing import validate_br04_price_stage, validate_br05_and_br06_arithmetic_and_tax
from app.core.rules.chronology import validate_br07_date_chronology, validate_br12_holiday_or_unusual_date
from app.core.rules.lifecycle import (
    validate_br08_reference_uniqueness,
    validate_br11_text_differences,
    validate_br13_delivery_and_payment_facts,
    validate_br14_export_equivalence,
    validate_br15_approval_freshness,
)
from app.schemas.common import SeverityEnum


class ValidationEngineResult:
    def __init__(self, findings: List[RuleFinding]):
        self.findings = findings
        self.error_count = sum(1 for f in findings if f.severity == SeverityEnum.BLOCK)
        self.warning_count = sum(1 for f in findings if f.severity == SeverityEnum.WARNING)
        self.info_count = sum(1 for f in findings if f.severity == SeverityEnum.INFO)
        self.passed = (self.error_count == 0)


def run_deterministic_validation(
    school_snapshot: Dict[str, Any],
    company_snapshot: Dict[str, Any],
    tax_policy_snapshot: List[Dict[str, Any]],
    officials_snapshot: List[Dict[str, Any]],
    lines: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    doc_numbers: List[Dict[str, Any]],
    subtotal: Decimal,
    tax_total: Decimal,
    grand_total: Decimal,
    fiscal_year: Optional[int] = None,
    itemized_sheet_counts: Optional[Dict[str, int]] = None,
    raw_cells_or_formulas: Optional[List[Dict[str, Any]]] = None,
    detected_entities: Optional[List[Dict[str, Any]]] = None,
    is_delivery_confirmed: bool = True,
    artifacts: Optional[List[Dict[str, Any]]] = None,
    revision_meta: Optional[Dict[str, Any]] = None,
) -> ValidationEngineResult:
    """Executes all 15 deterministic business rules (BR01..BR15)
    against the revision data and returns a consolidated ValidationEngineResult.
    """
    all_findings: List[RuleFinding] = []

    # BR01 Identity Consistency
    all_findings.extend(validate_br01_identity_consistency(
        school_snapshot=school_snapshot,
        company_snapshot=company_snapshot,
        detected_entities=detected_entities
    ))

    # BR02 Completeness
    all_findings.extend(validate_br02_completeness(
        doc_numbers=doc_numbers,
        events=events,
        lines=lines
    ))

    # BR03 Item Coverage (Dynamic N Items)
    all_findings.extend(validate_br03_item_coverage(
        revision_lines=lines,
        itemized_sheet_counts=itemized_sheet_counts
    ))

    # BR04 Price Stage
    all_findings.extend(validate_br04_price_stage(lines=lines))

    # BR05 Arithmetic & BR06 Tax Policy
    all_findings.extend(validate_br05_and_br06_arithmetic_and_tax(
        lines=lines,
        tax_policies=tax_policy_snapshot,
        recorded_subtotal=subtotal,
        recorded_tax_total=tax_total,
        recorded_grand_total=grand_total
    ))

    # BR07 Date Chronology
    all_findings.extend(validate_br07_date_chronology(
        events=events,
        fiscal_year=fiscal_year
    ))

    # BR08 Reference Uniqueness
    all_findings.extend(validate_br08_reference_uniqueness(doc_numbers=doc_numbers))

    # BR09 Signatories
    all_findings.extend(validate_br09_signatories(
        officials_snapshot=officials_snapshot,
        events=events
    ))

    # BR10 External and Stale References (Generic Regex)
    if raw_cells_or_formulas:
        all_findings.extend(validate_br10_external_and_stale_references(
            raw_cells_or_formulas=raw_cells_or_formulas
        ))

    # BR11 Text Differences
    all_findings.extend(validate_br11_text_differences(lines=lines))

    # BR12 Holiday or Unusual Date
    all_findings.extend(validate_br12_holiday_or_unusual_date(events=events))

    # BR13 Delivery and Payment Facts
    all_findings.extend(validate_br13_delivery_and_payment_facts(
        lines=lines,
        is_delivery_confirmed=is_delivery_confirmed
    ))

    # BR14 Export Equivalence
    if artifacts:
        all_findings.extend(validate_br14_export_equivalence(artifacts=artifacts))

    # BR15 Approval Freshness
    if revision_meta:
        all_findings.extend(validate_br15_approval_freshness(revision=revision_meta))

    return ValidationEngineResult(findings=all_findings)
