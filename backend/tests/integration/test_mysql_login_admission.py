from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from domain.exceptions import RateLimitExceeded
from infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from infrastructure.security.sqlalchemy_login_rate_limiter import SQLAlchemyLoginRateLimiter
from tests.e2e.test_auth_flows import _insert_user
from tests.mysql_auth_helpers import isolated_mysql


def test_concurrent_workers_cannot_exceed_either_budget():
    with isolated_mysql() as engine:
        barrier = Barrier(12)

        def attempt(index):
            with Session(engine) as db:
                barrier.wait(timeout=20)
                try:
                    SQLAlchemyLoginRateLimiter(db, max_attempts=5, window_seconds=900).consume(
                        client_ip="203.0.113.1", username="user" + str(index)
                    )
                    return True
                except RateLimitExceeded:
                    return False

        with ThreadPoolExecutor(max_workers=12) as pool:
            assert sum(pool.map(attempt, range(12))) == 5
        # A separate pool of clients with distinct IPs must still share the user budget.
        barrier = Barrier(12)

        def same_user(index):
            with Session(engine) as db:
                barrier.wait(timeout=20)
                try:
                    SQLAlchemyLoginRateLimiter(db, max_attempts=5, window_seconds=900).consume(
                        client_ip=f"198.51.100.{index}", username="same-user"
                    )
                    return True
                except RateLimitExceeded:
                    return False

        with ThreadPoolExecutor(max_workers=12) as pool:
            assert sum(pool.map(same_user, range(12))) == 5


@pytest.mark.parametrize("collation", ["utf8mb4_unicode_ci", "utf8mb4_0900_ai_ci"])
def test_equivalent_usernames_share_account_budget(collation):
    with isolated_mysql() as engine, Session(engine) as db:
        db.execute(
            text(f"ALTER TABLE users MODIFY Username VARCHAR(255) COLLATE {collation} NOT NULL")
        )
        user_id = _insert_user(db).id
        repository = SQLAlchemyUserRepository(db)
        admission = SQLAlchemyLoginRateLimiter(db, max_attempts=2, window_seconds=60)
        variants = ["admin", "ad\u200dmin", "adm\u200din"]
        for index, username in enumerate(variants):
            assert repository.get_by_username(username).id == user_id
            if index < 2:
                admission.consume(client_ip=f"198.51.100.{index}", username=username)
            else:
                with pytest.raises(RateLimitExceeded):
                    admission.consume(client_ip=f"198.51.100.{index}", username=username)
