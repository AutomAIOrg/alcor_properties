"""
Unit tests — casos de uso de configuración (precio por hora de limpieza).
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from application.settings.use_cases import (
    CLEANING_HOURLY_RATE_KEY,
    GetCleaningHourlyRateUseCase,
    UpdateCleaningHourlyRateUseCase,
)
from domain.exceptions import DomainValidationError
from domain.settings.repository import ISettingsRepository

pytestmark = pytest.mark.unit


def _repo(stored: str | None = None) -> MagicMock:
    repo = MagicMock(spec=ISettingsRepository)
    repo.get.return_value = stored
    return repo


class TestGetCleaningHourlyRate:
    def test_returns_stored_value(self):
        repo = _repo("18.50")
        result = GetCleaningHourlyRateUseCase(repo, Decimal("10")).execute()
        assert result == Decimal("18.50")
        repo.get.assert_called_once_with(CLEANING_HOURLY_RATE_KEY)

    def test_returns_default_when_unset(self):
        result = GetCleaningHourlyRateUseCase(_repo(None), Decimal("12")).execute()
        assert result == Decimal("12")

    def test_returns_default_when_stored_value_is_invalid(self):
        result = GetCleaningHourlyRateUseCase(_repo("not-a-number"), Decimal("12")).execute()
        assert result == Decimal("12")


class TestUpdateCleaningHourlyRate:
    def test_persists_normalized_value(self):
        repo = _repo()
        result = UpdateCleaningHourlyRateUseCase(repo).execute(Decimal("15.5"))
        assert result == Decimal("15.50")
        repo.set.assert_called_once_with(CLEANING_HOURLY_RATE_KEY, "15.50")

    def test_rejects_negative_rate(self):
        repo = _repo()
        with pytest.raises(DomainValidationError):
            UpdateCleaningHourlyRateUseCase(repo).execute(Decimal("-1"))
        repo.set.assert_not_called()
