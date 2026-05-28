"""
Unit tests — verificador de contraseñas passlib/bcrypt.
"""

import pytest
from passlib.context import CryptContext

from infrastructure.security.passlib_password_verifier import PasslibPasswordVerifier

pytestmark = pytest.mark.unit


class TestPasslibPasswordVerifier:
    def test_verify_returns_true_for_matching_bcrypt_hash_and_false_for_wrong_password(self):
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        stored_hash = pwd_context.hash("admin-password")
        verifier = PasslibPasswordVerifier()

        assert verifier.verify("admin-password", stored_hash) is True
        assert verifier.verify("wrong-password", stored_hash) is False

    def test_verify_returns_false_for_unknown_hash_format(self):
        verifier = PasslibPasswordVerifier()

        assert verifier.verify("admin-password", "not-a-supported-hash") is False
