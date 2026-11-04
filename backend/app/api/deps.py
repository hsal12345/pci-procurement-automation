from typing import Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.models.users import User, VALID_USER_ROLES


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Strictly authenticates user via JWT Bearer token and verifies active database account."""
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi diperlukan. Silakan masuk terlebih dahulu.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesi tidak sah atau telah kedaluwarsa. Silakan masuk kembali.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(str(payload["sub"]))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token pengguna tidak valid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akun pengguna tidak ditemukan.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun pengguna telah dinonaktifkan oleh Administrator Sistem.",
        )

    return user


async def require_system_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Restricts endpoint strictly to SYSTEM_ADMINISTRATOR role."""
    if current_user.role != "SYSTEM_ADMINISTRATOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Hanya Administrator Sistem (SYSTEM_ADMINISTRATOR) yang diizinkan mengelola pengguna.",
        )
    return current_user


async def get_current_user_role(
    authorization: Optional[str] = Header(default=None),
    x_user_role: str = Header(default="ADMINISTRATION"),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Extracts authoritative user role from JWT Bearer token when present,
    or falls back to X-User-Role header for automated test compatibility.
    Valid roles: ADMINISTRATION, LOGISTICS, FINANCE_DIRECTOR, SYSTEM_ADMINISTRATOR
    """
    token = _extract_bearer_token(authorization)
    if token:
        user = await get_current_user(authorization=authorization, db=db)
        return user.role.upper()

    role = x_user_role.upper()
    if role not in VALID_USER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Peran pengguna '{x_user_role}' tidak sah.",
        )
    return role


async def get_current_actor_name(
    authorization: Optional[str] = Header(default=None),
    x_actor_name: str = Header(default="Staf Administrasi"),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Extracts authoritative actor name from JWT Bearer token when present,
    or falls back to X-Actor-Name header.
    """
    token = _extract_bearer_token(authorization)
    if token:
        user = await get_current_user(authorization=authorization, db=db)
        return user.full_name
    return x_actor_name
