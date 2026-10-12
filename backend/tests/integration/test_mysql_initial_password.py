from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy.orm import Session

from domain.exceptions import InvalidToken
from infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from tests.e2e.test_auth_flows import _insert_user
from tests.mysql_auth_helpers import isolated_mysql


def test_only_one_initial_password_change_can_commit():
    with isolated_mysql() as engine:
        with Session(engine) as db:
            user_id = _insert_user(db, must_change_password=True).id
        barrier = Barrier(2)

        def change(index):
            with Session(engine) as db:
                barrier.wait(timeout=20)
                try:
                    SQLAlchemyUserRepository(db).complete_initial_password(
                        user_id, f"hash-{index}", 0
                    )
                    return True
                except InvalidToken:
                    return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(change, range(2))) == [False, True]
        with Session(engine) as db:
            user = SQLAlchemyUserRepository(db).get_by_id(user_id)
            assert user.token_version == 1
            assert not user.must_change_password
