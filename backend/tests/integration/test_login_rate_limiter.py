import pytest
from sqlalchemy.orm import Session

from domain.exceptions import RateLimitExceeded
from infrastructure.models.login_limit import LoginLimitORM
from infrastructure.security.sqlalchemy_login_rate_limiter import SQLAlchemyLoginRateLimiter


def limiter(db):
    return SQLAlchemyLoginRateLimiter(db, max_attempts=2, window_seconds=60)


def test_shared_across_sessions_and_no_success_reset(sqlite_session):
    limiter(sqlite_session).consume(client_ip="1.1.1.1", username="victim")
    with Session(sqlite_session.get_bind()) as other:
        limiter(other).consume(client_ip="1.1.1.1", username="own-account")
    with pytest.raises(RateLimitExceeded):
        limiter(sqlite_session).consume(client_ip="1.1.1.1", username="another")


def test_user_budget_across_ips_and_normalization(sqlite_session):
    admission = limiter(sqlite_session)
    admission.consume(client_ip="1.1.1.1", username=" ADMIN ")
    admission.consume(client_ip="2.2.2.2", username="admin")
    with pytest.raises(RateLimitExceeded):
        admission.consume(client_ip="3.3.3.3", username="Admin")


def test_expiry_and_denial_do_not_consume_other_key(sqlite_session):
    admission = limiter(sqlite_session)
    for _ in range(2):
        admission.consume(client_ip="1.1.1.1", username="one")
    with pytest.raises(RateLimitExceeded):
        admission.consume(client_ip="1.1.1.1", username="two")
    for _ in range(2):
        admission.consume(client_ip="2.2.2.2", username="two")
    sqlite_session.query(LoginLimitORM).update({LoginLimitORM.window_start: 0})
    sqlite_session.commit()
    admission.consume(client_ip="1.1.1.1", username="one")
