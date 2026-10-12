from unittest.mock import patch

import pytest

from domain.exceptions import InvalidToken
from infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from tests.e2e.test_auth_flows import _insert_user


def test_password_flag_and_revocation_are_one_transaction(sqlite_session):
    user = _insert_user(sqlite_session, must_change_password=True)
    repo = SQLAlchemyUserRepository(sqlite_session)
    original = repo.get_by_id(user.id)
    with patch.object(sqlite_session, "commit", side_effect=RuntimeError("commit failed")):
        with pytest.raises(RuntimeError):
            repo.complete_initial_password(user.id, "new-hash", original.token_version)
    unchanged = repo.get_by_id(user.id)
    assert unchanged.password == original.password
    assert unchanged.must_change_password
    assert unchanged.token_version == original.token_version
    result = repo.complete_initial_password(user.id, "new-hash", original.token_version)
    assert result.password == "new-hash"
    assert not result.must_change_password
    assert result.token_version == original.token_version + 1
    with pytest.raises(InvalidToken):
        repo.complete_initial_password(user.id, "racing-hash", original.token_version)
    assert repo.get_by_id(user.id).password == "new-hash"
