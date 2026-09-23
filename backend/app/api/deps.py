from typing import AsyncGenerator
from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db


async def get_current_user_role(
    x_user_role: str = Header(default="ADMINISTRATION")
) -> str:
    """Extracts user role from header or session.
    Valid roles: ADMINISTRATION, LOGISTICS, FINANCE_DIRECTOR, SYSTEM_ADMINISTRATOR
    """
    valid_roles = ["ADMINISTRATION", "LOGISTICS", "FINANCE_DIRECTOR", "SYSTEM_ADMINISTRATOR"]
    role = x_user_role.upper()
    if role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Peran pengguna '{x_user_role}' tidak sah."
        )
    return role
