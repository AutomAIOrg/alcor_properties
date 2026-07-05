"""
Unit tests — DTOs de la API de autenticación.
"""

import pytest
from pydantic import ValidationError

from api.v1.auth.schemas import ForgotPasswordRequest

pytestmark = pytest.mark.unit


class TestForgotPasswordRequest:
    def test_accepts_valid_email(self):
        request = ForgotPasswordRequest(email="admin@example.com")

        assert request.email == "admin@example.com"

    def test_normalizes_email_before_validation(self):
        request = ForgotPasswordRequest(email="  Admin@Example.COM  ")

        assert request.email == "admin@example.com"

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="not-an-email")
