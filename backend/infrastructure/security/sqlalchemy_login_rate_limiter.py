"""MySQL-backed fixed-window admission; every attempt counts, including successes."""

import hashlib
import math
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from application.auth.login_rate_limiter_interface import ILoginRateLimiter
from domain.exceptions import RateLimitExceeded
from infrastructure.models.login_limit import LoginLimitORM
from infrastructure.models.user import UserORM


class SQLAlchemyLoginRateLimiter(ILoginRateLimiter):
    def __init__(self, db: Session, *, max_attempts: int, window_seconds: int):
        if max_attempts < 1 or window_seconds < 1:
            raise ValueError("Login limits must be positive")
        self.db = db
        self.maximum = max_attempts
        self.window = window_seconds

    def consume(self, *, client_ip: str, username: str) -> None:
        dialect = self.db.get_bind().dialect.name
        try:
            # Use the database's username comparison, exactly as login does.
            # Unicode normalization alone cannot reproduce MySQL collations.
            user_id = self.db.scalar(select(UserORM.id).where(UserORM.username == username))
            identity = (
                f"user:{user_id}"
                if user_id is not None
                else "username:"
                + "".join(
                    c
                    for c in unicodedata.normalize("NFKD", username.strip().casefold())
                    if not unicodedata.combining(c)
                )
            )
            keys = sorted(
                hashlib.sha256(v.encode()).hexdigest() for v in ("ip:" + client_ip, identity)
            )
            now = int(
                self.db.execute(select(func.unix_timestamp())).scalar_one()
                if dialect == "mysql"
                else self.db.execute(select(func.strftime("%s", "now"))).scalar_one()
            )
            # Stable ordering avoids deadlocks when two attempts share either key.
            rows: list[LoginLimitORM] = []
            for key in keys:
                values = dict(key=key, window_start=now, attempts=0)
                if dialect == "mysql":
                    mysql_stmt = mysql_insert(LoginLimitORM).values(**values)
                    self.db.execute(mysql_stmt.on_duplicate_key_update(key=mysql_stmt.inserted.key))
                elif dialect == "sqlite":
                    self.db.execute(
                        sqlite_insert(LoginLimitORM).values(**values).on_conflict_do_nothing()
                    )
                else:
                    raise RuntimeError("Unsupported login rate-limit database")
                row = self.db.execute(
                    select(LoginLimitORM)
                    .where(LoginLimitORM.key == key)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                ).scalar_one()
                if now >= row.window_start + self.window:
                    row.window_start, row.attempts = now, 0
                rows.append(row)
            retry = max(
                (
                    row.window_start + self.window - now
                    for row in rows
                    if row.attempts >= self.maximum
                ),
                default=0,
            )
            if retry:
                raise RateLimitExceeded(math.ceil(retry))
            for row in rows:
                row.attempts += 1
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
