"""
Integration tests — SQLAlchemySettingsRepository contra SQLite en memoria.
"""

import pytest

from infrastructure.repositories.sqlalchemy_settings_repository import (
    SQLAlchemySettingsRepository,
)

pytestmark = pytest.mark.integration


class TestSettingsRepository:
    def test_get_returns_none_for_missing_key(self, sqlite_session):
        assert SQLAlchemySettingsRepository(sqlite_session).get("missing") is None

    def test_set_then_get_roundtrip(self, sqlite_session):
        repo = SQLAlchemySettingsRepository(sqlite_session)
        repo.set("cleaning_hourly_rate", "15.00")

        assert repo.get("cleaning_hourly_rate") == "15.00"

    def test_set_updates_existing_value(self, sqlite_session):
        repo = SQLAlchemySettingsRepository(sqlite_session)
        repo.set("cleaning_hourly_rate", "15.00")
        repo.set("cleaning_hourly_rate", "20.00")

        assert repo.get("cleaning_hourly_rate") == "20.00"
