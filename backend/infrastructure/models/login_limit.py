"""Shared login admission counters, persisted across workers and restarts."""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class LoginLimitORM(Base):
    __tablename__ = "auth_login_limits"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[int] = mapped_column(BigInteger, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
