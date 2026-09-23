from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from app.database import get_db
from app.api.deps import get_current_user_role
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
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Lists recent audit events filtered by entity_id or entity_name."""
    if entity_id:
        try:
            entity_uuid = UUID(entity_id)
            # Check if entity is a package or a revision
            rev_res = await db.execute(select(PackageRevision.id).where(PackageRevision.package_id == entity_uuid))
            child_revs = [str(r) for r in rev_res.scalars().all()]
            target_ids = [str(entity_id)] + child_revs
            query = select(AuditEvent).where(AuditEvent.entity_id.in_(target_ids)).order_by(desc(AuditEvent.timestamp)).limit(limit)
        except Exception:
            query = select(AuditEvent).where(AuditEvent.entity_id == str(entity_id)).order_by(desc(AuditEvent.timestamp)).limit(limit)
    elif entity_name:
        query = select(AuditEvent).where(AuditEvent.entity_name == entity_name).order_by(desc(AuditEvent.timestamp)).limit(limit)
    else:
        query = select(AuditEvent).order_by(desc(AuditEvent.timestamp)).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()

