from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.users import User
from app.schemas.users import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticates a user by username or email and returns a signed JWT Bearer token.
    Note: Self-registration is disabled; accounts must be provisioned by SYSTEM_ADMINISTRATOR.
    """
    identifier = payload.username_or_email.strip().lower()
    res = await db.execute(
        select(User).where(
            or_(
                func.lower(User.username) == identifier,
                func.lower(User.email) == identifier,
            )
        )
    )
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username/email atau kata sandi salah.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda sedang dinonaktifkan. Hubungi Administrator Sistem.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    await AuditService.log_event(
        db=db,
        entity_name="User",
        entity_id=str(user.id),
        action="LOGIN",
        actor=user.full_name,
        after_state={"username": user.username, "role": user.role},
        reason="Pengguna berhasil masuk ke sistem",
    )
    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        subject=str(user.id),
        role=user.role,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the profile and RBAC role of the currently authenticated user."""
    return current_user


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Allows an authenticated user to update their own password."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi saat ini tidak sesuai.",
        )

    current_user.password_hash = hash_password(payload.new_password)
    await AuditService.log_event(
        db=db,
        entity_name="User",
        entity_id=str(current_user.id),
        action="CHANGE_PASSWORD",
        actor=current_user.full_name,
        reason="Pengguna memperbarui kata sandi akun sendiri",
    )
    await db.commit()
    return {"message": "Kata sandi berhasil diperbarui."}

