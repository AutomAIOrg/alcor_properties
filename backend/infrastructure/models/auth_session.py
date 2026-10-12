"""Refresh token families, one per authenticated session."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class AuthSessionORM(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.ID", ondelete="CASCADE"), index=True)
    refresh_jti: Mapped[str] = mapped_column(String(36), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
