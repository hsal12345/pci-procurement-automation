from datetime import date, datetime, time
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from app.database import get_db
from app.api.deps import get_current_user_role, require_finance_or_sysadmin
from app.models.packages import Package, PackageRevision
from app.models.audit import AuditEvent
from app.schemas.audit import AuditEventResponse
from app.services.audit_service import audit_service

router = APIRouter(tags=["Audit Trail"])


@router.get("/packages/{id}/audit", response_model=List[AuditEventResponse])
async def get_package_audit_log(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Retrieves full append-only audit trail for a package and all its associated revisions."""
    pkg_res = await db.execute(select(Package).where(Package.id == id))
    pkg = pkg_res.scalar_one_or_none()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paket pengadaan dengan ID {id} tidak ditemukan."
        )

    return await audit_service.get_package_audit_trail(db, id)


@router.get("/audit/events", response_model=List[AuditEventResponse])
@router.get("/audit", response_model=List[AuditEventResponse])
async def list_audit_events(
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    q: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    role: str = Depends(require_finance_or_sysadmin),
):
    """Lists append-only audit events with UC-09 multi-criteria search (periode, entitas, aksi, aktor, kata kunci)."""
    query = select(AuditEvent)

    if entity_id:
        try:
            entity_uuid = UUID(entity_id)
            rev_res = await db.execute(select(PackageRevision.id).where(PackageRevision.package_id == entity_uuid))
            child_revs = [str(r) for r in rev_res.scalars().all()]
            target_ids = [str(entity_id)] + child_revs
            query = query.where(AuditEvent.entity_id.in_(target_ids))
        except Exception:
            query = query.where(AuditEvent.entity_id == str(entity_id))

    if entity_name:
        query = query.where(AuditEvent.entity_name == entity_name)

    if action:
        query = query.where(AuditEvent.action == action.upper())

    if actor and actor.strip():
        query = query.where(AuditEvent.actor.ilike(f"%{actor.strip()}%"))

    if date_from:
        query = query.where(AuditEvent.timestamp >= datetime.combine(date_from, time.min))

    if date_to:
        query = query.where(AuditEvent.timestamp <= datetime.combine(date_to, time.max))

    if q and q.strip():
        needle = f"%{q.strip()}%"
        query = query.where(
            or_(
                AuditEvent.reason.ilike(needle),
                AuditEvent.actor.ilike(needle),
                AuditEvent.entity_name.ilike(needle),
                AuditEvent.entity_id.ilike(needle),
                AuditEvent.action.ilike(needle),
            )
        )

    result = await db.execute(query.order_by(desc(AuditEvent.timestamp)).limit(limit))
    return result.scalars().all()

