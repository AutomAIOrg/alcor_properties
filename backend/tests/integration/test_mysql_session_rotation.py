from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

from sqlalchemy.orm import Session

from infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from tests.e2e.test_auth_flows import _insert_user
from tests.mysql_auth_helpers import isolated_mysql


def test_simultaneous_refresh_revokes_only_that_family_and_atomic_version_bumps():
    with isolated_mysql() as engine:
        expires = datetime.now(UTC) + timedelta(days=1)
        with Session(engine) as db:
            user = _insert_user(db)
            user_id = user.id
            repo = SQLAlchemyUserRepository(db)
            repo.create_auth_session(user_id, "family-a", "old-a", expires, 0)
            repo.create_auth_session(user_id, "family-b", "old-b", expires, 0)
        barrier = Barrier(2)

        def rotate(index):
            with Session(engine) as db:
                barrier.wait(timeout=20)
                return SQLAlchemyUserRepository(db).rotate_auth_session(
                    user_id, "family-a", "old-a", f"new-{index}", expires, 0
                )

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(rotate, range(2))) == [False, True]
        with Session(engine) as db:
            repo = SQLAlchemyUserRepository(db)
            assert not repo.is_auth_session_active(user_id, "family-a")
            assert repo.is_auth_session_active(user_id, "family-b")

        def bump(_):
            with Session(engine) as db:
                SQLAlchemyUserRepository(db).bump_token_version(user_id)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(bump, range(8)))
        with Session(engine) as db:
            assert SQLAlchemyUserRepository(db).get_by_id(user_id).token_version == 8
