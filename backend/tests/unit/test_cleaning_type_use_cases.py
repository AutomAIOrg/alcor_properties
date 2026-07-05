"""
Unit tests — casos de uso del catálogo de tipos de limpieza.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from application.cleaning_types.use_cases import (
    CreateCleaningTypeUseCase,
    DeleteCleaningTypeUseCase,
    ListCleaningTypesUseCase,
    UpdateCleaningTypeUseCase,
)
from domain.cleaning_types.repository import ICleaningTypeRepository
from domain.exceptions import (
    CleaningTypeAlreadyExistsError,
    CleaningTypeNotFoundError,
    DomainValidationError,
)
from tests.helpers import make_cleaning_type

pytestmark = pytest.mark.unit


def _repo() -> MagicMock:
    return MagicMock(spec=ICleaningTypeRepository)


class TestListCleaningTypesUseCase:
    def test_delegates_active_only_flag(self):
        repo = _repo()
        repo.list.return_value = [make_cleaning_type()]

        result = ListCleaningTypesUseCase(repo).execute(active_only=True)

        assert len(result) == 1
        repo.list.assert_called_once_with(active_only=True)


class TestCreateCleaningTypeUseCase:
    def test_creates_and_normalizes_rate(self):
        repo = _repo()
        repo.get_by_name.return_value = None
        repo.create.side_effect = lambda ct: ct

        result = CreateCleaningTypeUseCase(repo).execute(
            name="  Limpieza normal  ", hourly_rate=Decimal("12.5")
        )

        assert result.name == "Limpieza normal"
        assert result.hourly_rate == Decimal("12.50")
        assert result.active is True

    def test_raises_when_name_already_exists(self):
        repo = _repo()
        repo.get_by_name.return_value = make_cleaning_type()

        with pytest.raises(CleaningTypeAlreadyExistsError):
            CreateCleaningTypeUseCase(repo).execute(
                name="Limpieza normal", hourly_rate=Decimal("9")
            )

        repo.create.assert_not_called()

    def test_raises_on_negative_rate(self):
        repo = _repo()
        repo.get_by_name.return_value = None

        with pytest.raises(DomainValidationError):
            CreateCleaningTypeUseCase(repo).execute(name="X", hourly_rate=Decimal("-1"))


class TestUpdateCleaningTypeUseCase:
    def test_updates_existing_type(self):
        repo = _repo()
        repo.get_by_id.return_value = make_cleaning_type(cleaning_type_id=1)
        repo.get_by_name.return_value = None
        repo.update.side_effect = lambda ct: ct

        result = UpdateCleaningTypeUseCase(repo).execute(
            1, name="Fin de semana", hourly_rate=Decimal("20"), active=False
        )

        assert result.name == "Fin de semana"
        assert result.hourly_rate == Decimal("20.00")
        assert result.active is False

    def test_raises_when_missing(self):
        repo = _repo()
        repo.get_by_id.return_value = None

        with pytest.raises(CleaningTypeNotFoundError):
            UpdateCleaningTypeUseCase(repo).execute(
                9, name="X", hourly_rate=Decimal("1"), active=True
            )

    def test_allows_keeping_its_own_name(self):
        repo = _repo()
        repo.get_by_id.return_value = make_cleaning_type(cleaning_type_id=1, name="Normal")
        repo.get_by_name.return_value = make_cleaning_type(cleaning_type_id=1, name="Normal")
        repo.update.side_effect = lambda ct: ct

        result = UpdateCleaningTypeUseCase(repo).execute(
            1, name="Normal", hourly_rate=Decimal("15"), active=True
        )

        assert result.name == "Normal"

    def test_raises_when_name_clashes_with_another_type(self):
        repo = _repo()
        repo.get_by_id.return_value = make_cleaning_type(cleaning_type_id=1, name="Normal")
        repo.get_by_name.return_value = make_cleaning_type(cleaning_type_id=2, name="Fin de semana")

        with pytest.raises(CleaningTypeAlreadyExistsError):
            UpdateCleaningTypeUseCase(repo).execute(
                1, name="Fin de semana", hourly_rate=Decimal("15"), active=True
            )

        repo.update.assert_not_called()


class TestDeleteCleaningTypeUseCase:
    def test_deletes_existing_type(self):
        repo = _repo()
        repo.get_by_id.return_value = make_cleaning_type(cleaning_type_id=4)

        DeleteCleaningTypeUseCase(repo).execute(4)

        repo.delete.assert_called_once_with(4)

    def test_raises_when_missing(self):
        repo = _repo()
        repo.get_by_id.return_value = None

        with pytest.raises(CleaningTypeNotFoundError):
            DeleteCleaningTypeUseCase(repo).execute(99)

        repo.delete.assert_not_called()
