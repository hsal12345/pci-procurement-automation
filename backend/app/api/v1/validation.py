from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.packages import PackageRevision
from app.models.validation import ValidationRun, Finding
from app.schemas.validation import (
    ValidationRunResponse,
    FindingResponse,
    FindingDispositionRequest,
)
from app.core.rules.engine import run_deterministic_validation
from app.api.deps import get_current_user_role

router = APIRouter(tags=["Validation"])


@router.post("/revisions/{id}/validate", response_model=ValidationRunResponse)
async def validate_revision(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Triggers the deterministic validation engine (rules BR01 through BR15)
    against the revision snapshot and persists the run along with any findings.
    """
    result = await db.execute(
        select(PackageRevision)
        .options(
            selectinload(PackageRevision.lines),
            selectinload(PackageRevision.events),
            selectinload(PackageRevision.numbers),
            selectinload(PackageRevision.package),
        )
        .where(PackageRevision.id == id)
    )
    revision = result.scalar_one_or_none()
    if not revision:
        raise HTTPException(status_code=404, detail="Revisi paket tidak ditemukan.")

    lines_data = [
        {
            "line_number": l.line_number,
            "original_description": l.original_description,
            "confirmed_description": l.confirmed_description,
            "specification": l.specification,
            "quantity": l.quantity,
            "unit": l.unit,
            "hps_unit_price": l.hps_unit_price,
            "offer_unit_price": l.offer_unit_price,
            "final_unit_price": l.final_unit_price,
            "discount": l.discount,
            "line_total": l.line_total,
            "condition": l.condition,
        }
        for l in revision.lines
    ]

    events_data = [
        {
            "event_code": e.event_code,
            "event_date": e.event_date,
            "day_name_id": e.day_name_id,
            "location": e.location
        }
        for e in revision.events
    ]

    numbers_data = [
        {
            "doc_code": n.doc_code,
            "doc_number": n.doc_number,
            "issuer": n.issuer,
            "counter_val": n.counter_val
        }
        for n in revision.numbers
    ]

    engine_res = run_deterministic_validation(
        school_snapshot=revision.school_snapshot or {},
        company_snapshot=revision.company_snapshot or {},
        tax_policy_snapshot=revision.tax_policy_snapshot or [],
        officials_snapshot=revision.officials_snapshot or [],
        lines=lines_data,
        events=events_data,
        doc_numbers=numbers_data,
        subtotal=revision.subtotal,
        tax_total=revision.tax_total,
        grand_total=revision.grand_total,
        fiscal_year=revision.package.fiscal_year if revision.package else None
    )

    # Persist ValidationRun
    v_run = ValidationRun(
        revision_id=revision.id,
        triggered_by=role,
        passed=engine_res.passed,
        error_count=engine_res.error_count,
        warning_count=engine_res.warning_count,
        info_count=engine_res.info_count
    )
    db.add(v_run)
    await db.flush()

    # Persist Findings
    for f in engine_res.findings:
        finding = Finding(
            run_id=v_run.id,
            rule_code=f.rule_code,
            severity=f.severity.value,
            doc_code=f.doc_code,
            sheet_name=f.sheet_name,
            cell_range=f.cell_range,
            field_name=f.field_name,
            original_value=f.original_value,
            proposed_value=f.proposed_value,
            message=f.message,
            disposition="PENDING"
        )
        db.add(finding)

    await db.commit()

    # Re-query with findings eager-loaded
    run_res = await db.execute(
        select(ValidationRun)
        .options(selectinload(ValidationRun.findings))
        .where(ValidationRun.id == v_run.id)
    )
    return run_res.scalar_one()


@router.get("/revisions/{id}/findings", response_model=List[FindingResponse])
async def get_revision_findings(id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieves all findings from the latest validation run of this revision."""
    res_run = await db.execute(
        select(ValidationRun)
        .where(ValidationRun.revision_id == id)
        .order_by(desc(ValidationRun.run_at))
    )
    latest_run = res_run.scalars().first()
    if not latest_run:
        return []

    res_findings = await db.execute(
        select(Finding).where(Finding.run_id == latest_run.id)
    )
    return res_findings.scalars().all()


@router.post("/findings/{finding_id}/disposition", response_model=FindingResponse)
async def update_finding_disposition(
    finding_id: UUID,
    payload: FindingDispositionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Allows finance director or administration to record justification
    and disposition for a warning finding.
    """
    res = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = res.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Temuan validasi tidak ditemukan.")

    finding.disposition = payload.disposition.value
    finding.disposition_reason = payload.disposition_reason
    finding.disposition_actor = payload.disposition_actor

    await db.commit()
    await db.refresh(finding)
    return finding
