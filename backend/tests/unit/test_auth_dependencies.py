"""
Unit tests — dependencias de autorización por rol.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from api.dependencies import require_admin, require_cleaning
from domain.auth.user_entity import Role
from tests.helpers import make_user

pytestmark = pytest.mark.unit


class TestRequireAdmin:
    def test_allows_admin(self):
        user = make_user(role=Role.ADMIN)

        assert require_admin(current_user=user) is user

    def test_denies_limpiadora(self):
        user = make_user(role=Role.LIMPIADORA)

        with pytest.raises(HTTPException) as exc_info:
            require_admin(current_user=user)

        assert exc_info.value.status_code == 403


class TestRequireCleaning:
    def test_allows_admin(self):
        user = make_user(role=Role.ADMIN)

        assert require_cleaning(current_user=user) is user

    def test_allows_limpiadora(self):
        user = make_user(role=Role.LIMPIADORA)

        assert require_cleaning(current_user=user) is user

    def test_denies_unauthorized_role(self):
        user = make_user(role=Role.ADMIN)
        user = MagicMock(spec=user)
        user.role = "guest"

        with pytest.raises(HTTPException) as exc_info:
            require_cleaning(current_user=user)

        assert exc_info.value.status_code == 403
