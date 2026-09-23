import json
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any, Dict, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from app.models.audit import AuditEvent
from app.models.packages import Package, PackageRevision


def _serialize_for_audit(obj: Any) -> Any:
    """Recursively converts Decimals, UUIDs, Dates, and Pydantic models to JSON-serializable types."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _serialize_for_audit(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_serialize_for_audit(i) for i in obj]
    if hasattr(obj, "model_dump"):
        return _serialize_for_audit(obj.model_dump())
    if hasattr(obj, "__dict__"):
        clean_dict = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return _serialize_for_audit(clean_dict)
    return str(obj)


class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        entity_name: str,
        entity_id: str,
        action: str,
        actor: str,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        reason: Optional[str] = None
    ) -> AuditEvent:
        """Appends a structured audit event to the append-only audit_events table."""
        event = AuditEvent(
            entity_name=entity_name,
            entity_id=str(entity_id),
            action=action.upper(),
            actor=actor,
            timestamp=datetime.utcnow(),
            before_state=_serialize_for_audit(before_state) if before_state else None,
            after_state=_serialize_for_audit(after_state) if after_state else None,
            ip_address=ip_address,
            reason=reason
        )
        db.add(event)
        await db.flush()
        return event

    @staticmethod
    async def get_package_audit_trail(
        db: AsyncSession,
        package_id: UUID
    ) -> List[AuditEvent]:
        """Retrieves chronological audit trail for a package and all its associated revisions."""
        # Find all revision IDs for this package
        rev_res = await db.execute(
            select(PackageRevision.id).where(PackageRevision.package_id == package_id)
        )
        revision_ids = [str(r) for r in rev_res.scalars().all()]
        target_ids = [str(package_id)] + revision_ids

        result = await db.execute(
            select(AuditEvent)
            .where(AuditEvent.entity_id.in_(target_ids))
            .order_by(desc(AuditEvent.timestamp))
        )
        return result.scalars().all()


audit_service = AuditService()
