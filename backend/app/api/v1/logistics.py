from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import get_current_user_role
from app.models.logistics import LogisticsRecord, LogisticsEvidence
from app.schemas.logistics import (
    LogisticsFactsUpdate,
    LogisticsRecordResponse,
    LogisticsEvidenceResponse,
)
from app.services.logistics_service import logistics_service

router = APIRouter(tags=["Logistics & Evidence"])


@router.get(
    "/packages/{id}/revisions/{revision_id}/logistics",
    response_model=LogisticsRecordResponse
)
@router.get(
    "/revisions/{revision_id}/logistics",
    response_model=LogisticsRecordResponse
)
async def get_logistics_record(
    revision_id: UUID,
    id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    res = await db.execute(
        select(LogisticsRecord)
        .where(LogisticsRecord.revision_id == revision_id)
    )
    rec = res.scalar_one_or_none()
    if not rec:
        rec = LogisticsRecord(
            revision_id=revision_id,
            inspection_status="PENDING",
            courier_name="Armada Pengiriman CV PCI",
            vehicle_plate="B 1234 PCI",
        )
        db.add(rec)
        await db.commit()
        await db.refresh(rec)

    att_res = await db.execute(
        select(LogisticsEvidence)
        .where(LogisticsEvidence.revision_id == revision_id)
        .order_by(LogisticsEvidence.created_at)
    )
    evidences = att_res.scalars().all()

    resp = LogisticsRecordResponse.model_validate(rec)
    resp.attachments = [LogisticsEvidenceResponse.model_validate(e) for e in evidences]
    return resp



@router.patch(
    "/packages/{id}/revisions/{revision_id}/logistics",
    response_model=LogisticsRecordResponse
)
@router.put(
    "/packages/{id}/revisions/{revision_id}/logistics",
    response_model=LogisticsRecordResponse
)
@router.patch(
    "/revisions/{revision_id}/logistics",
    response_model=LogisticsRecordResponse
)
@router.put(
    "/revisions/{revision_id}/logistics",
    response_model=LogisticsRecordResponse
)
async def update_logistics_record(
    revision_id: UUID,
    payload: LogisticsFactsUpdate,
    id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Updates dispatch dates, receipt confirmation, driver/vehicle details,
    line item conditions (BAIK/RUSAK), and physical received quantities.
    Enforces dispute routing if goods are damaged or partial.
    """
    record = await logistics_service.update_logistics_facts(
        db=db,
        revision_id=revision_id,
        payload=payload,
        actor_role=role,
        actor_name=f"User ({role})"
    )
    return record


@router.post(
    "/packages/{id}/revisions/{revision_id}/evidence",
    response_model=LogisticsEvidenceResponse,
    status_code=status.HTTP_201_CREATED
)
@router.post(
    "/revisions/{revision_id}/logistics/evidence",
    response_model=LogisticsEvidenceResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_logistics_evidence(
    revision_id: UUID,
    id: Optional[UUID] = None,
    file: UploadFile = File(...),
    evidence_type: str = Form(default="DELIVERY_PHOTO"),
    description: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Uploads photo or document evidence for delivery and physical inspection
    (supports JPEG, PNG, PDF up to 10 MB).
    """
    evidence = await logistics_service.save_evidence_attachment(
        db=db,
        revision_id=revision_id,
        file=file,
        evidence_type=evidence_type,
        description=description,
        actor_role=role,
        actor_name=f"User ({role})"
    )
    return evidence


@router.get(
    "/packages/{id}/revisions/{revision_id}/evidence",
    response_model=List[LogisticsEvidenceResponse]
)
@router.get(
    "/revisions/{revision_id}/evidence",
    response_model=List[LogisticsEvidenceResponse]
)
async def list_logistics_evidence(
    revision_id: UUID,
    id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Lists all uploaded delivery and inspection evidence attachments for a package revision."""
    return await logistics_service.list_evidence(db, revision_id)
