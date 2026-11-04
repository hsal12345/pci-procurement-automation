from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_system_admin
from app.core.security import hash_password
from app.database import get_db
from app.models.users import User, VALID_USER_ROLES
from app.schemas.users import UserCreate, UserResponse, UserUpdate
from app.services.audit_service import AuditService

router = APIRouter(prefix="/users", tags=["User Management (RBAC)"])


@router.get("", response_model=List[UserResponse])
async def list_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_system_admin),
):
    """Lists all users in the system. Strictly restricted to SYSTEM_ADMINISTRATOR."""
    query = select(User).order_by(User.created_at.asc())
    if role and role.upper() != "ALL":
        query = query.where(User.role == role.upper())
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(User.username).like(term),
                func.lower(User.email).like(term),
                func.lower(User.full_name).like(term),
            )
        )
    res = await db.execute(query)
    return res.scalars().all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_system_admin),
):
    """Provisions a new user account with a specific RBAC role.
    Strictly restricted to SYSTEM_ADMINISTRATOR.
    """
    clean_username = payload.username.strip().lower()
    clean_email = payload.email.strip().lower()

    if payload.role not in VALID_USER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Peran '{payload.role}' tidak valid.",
        )

    existing_username = (
        await db.execute(select(User).where(func.lower(User.username) == clean_username))
    ).scalar_one_or_none()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{clean_username}' sudah terdaftar.",
        )

    existing_email = (
        await db.execute(select(User).where(func.lower(User.email) == clean_email))
    ).scalar_one_or_none()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{clean_email}' sudah terdaftar.",
        )

    new_user = User(
        username=clean_username,
        email=clean_email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(new_user)
    await db.flush()

    await AuditService.log_event(
        db=db,
        entity_name="User",
        entity_id=str(new_user.id),
        action="CREATE",
        actor=admin_user.full_name,
        after_state={
            "username": new_user.username,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role,
            "is_active": new_user.is_active,
        },
        reason=f"Pembuatan akun pengguna baru oleh {admin_user.username}",
    )

    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.put("/{id}", response_model=UserResponse)
async def update_user(
    id: UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_system_admin),
):
    """Updates an existing user's profile, RBAC role, active status, or password.
    Strictly restricted to SYSTEM_ADMINISTRATOR.
    """
    res = await db.execute(select(User).where(User.id == id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Akun pengguna tidak ditemukan.",
        )

    # Guard against self-lockout
    if user.id == admin_user.id:
        if payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anda tidak dapat menonaktifkan akun Administrator Anda sendiri yang sedang aktif.",
            )
        if payload.role is not None and payload.role != "SYSTEM_ADMINISTRATOR":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anda tidak dapat menurunkan peran Administrator pada akun Anda sendiri.",
            )

    before_state = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
    }

    if payload.username is not None:
        clean_username = payload.username.strip().lower()
        if clean_username != user.username.lower():
            dup = (
                await db.execute(
                    select(User).where(func.lower(User.username) == clean_username, User.id != id)
                )
            ).scalar_one_or_none()
            if dup:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Username '{clean_username}' sudah digunakan pengguna lain.",
                )
            user.username = clean_username

    if payload.email is not None:
        clean_email = payload.email.strip().lower()
        if clean_email != user.email.lower():
            dup = (
                await db.execute(
                    select(User).where(func.lower(User.email) == clean_email, User.id != id)
                )
            ).scalar_one_or_none()
            if dup:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email '{clean_email}' sudah digunakan pengguna lain.",
                )
            user.email = clean_email

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()

    if payload.role is not None:
        if payload.role not in VALID_USER_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Peran '{payload.role}' tidak valid.",
            )
        user.role = payload.role

    if payload.is_active is not None:
        user.is_active = payload.is_active

    password_changed = False
    if payload.password is not None and payload.password.strip():
        user.password_hash = hash_password(payload.password.strip())
        password_changed = True

    await AuditService.log_event(
        db=db,
        entity_name="User",
        entity_id=str(user.id),
        action="UPDATE",
        actor=admin_user.full_name,
        before_state=before_state,
        after_state={
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "password_reset": password_changed,
        },
        reason=f"Pembaruan data pengguna oleh {admin_user.username}",
    )

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{id}")
async def delete_user(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_system_admin),
):
    """Deletes a user account. Prevents deleting the currently authenticated admin."""
    res = await db.execute(select(User).where(User.id == id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Akun pengguna tidak ditemukan.",
        )

    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anda tidak dapat menghapus akun Anda sendiri yang sedang aktif.",
        )

    username_deleted = user.username
    await AuditService.log_event(
        db=db,
        entity_name="User",
        entity_id=str(user.id),
        action="DELETE",
        actor=admin_user.full_name,
        before_state={
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
        reason=f"Penghapusan akun pengguna oleh {admin_user.username}",
    )

    await db.delete(user)
    await db.commit()
    return {"message": f"Pengguna '{username_deleted}' berhasil dihapus.", "user_id": str(id)}

