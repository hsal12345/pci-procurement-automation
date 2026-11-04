from sqlalchemy import Boolean, Column, String
from app.models.base import BaseModel, TZDateTime

VALID_USER_ROLES = (
    "SYSTEM_ADMINISTRATOR",
    "ADMINISTRATION",
    "FINANCE_DIRECTOR",
    "LOGISTICS",
)


class User(BaseModel):
    __tablename__ = "users"

    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(64), nullable=False, default="ADMINISTRATION", index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(TZDateTime, nullable=True)

