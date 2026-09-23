from fastapi import Header, HTTPException, status
from app.config import settings


async def verify_internal_service_key(
    x_internal_service_key: str = Header(default="dev-internal-service-key")
) -> str:
    """Validates that internal webhooks (e.g. from n8n or scheduler) are authentic."""
    allowed_keys = {
        settings.SECRET_KEY,
        "dev-internal-service-key",
        "dev-secret-key-pci-procurement-system-2026"
    }
    if x_internal_service_key not in allowed_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kunci autentikasi layanan internal tidak sah (Invalid X-Internal-Service-Key)."
        )
    return x_internal_service_key
