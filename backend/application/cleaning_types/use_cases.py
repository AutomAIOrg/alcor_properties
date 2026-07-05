"""
Casos de uso para el catálogo de tipos de limpieza.

Los tipos de limpieza son un catálogo mantenido por el administrador. Cada tipo lleva
asociada una tarifa por hora que se usa para calcular el coste de las facturas.
"""

from decimal import Decimal

from domain.cleaning_types.entity import CleaningType
from domain.cleaning_types.repository import ICleaningTypeRepository
from domain.exceptions import (
    CleaningTypeAlreadyExistsError,
    CleaningTypeNotFoundError,
    DomainValidationError,
)


class ListCleaningTypesUseCase:
    """Devuelve los tipos de limpieza del catálogo."""

    def __init__(self, repository: ICleaningTypeRepository) -> None:
        self._repository = repository

    def execute(self, active_only: bool = False) -> list[CleaningType]:
        return self._repository.list(active_only=active_only)


class CreateCleaningTypeUseCase:
    """Crea un tipo de limpieza garantizando la unicidad del nombre."""

    def __init__(self, repository: ICleaningTypeRepository) -> None:
        self._repository = repository

    def execute(self, name: str, hourly_rate: Decimal, active: bool = True) -> CleaningType:
        cleaning_type = CleaningType(
            name=name, hourly_rate=_normalize_rate(hourly_rate), active=active
        )
        if self._repository.get_by_name(cleaning_type.name) is not None:
            raise CleaningTypeAlreadyExistsError(cleaning_type.name)
        return self._repository.create(cleaning_type)


class UpdateCleaningTypeUseCase:
    """Actualiza un tipo de limpieza existente."""

    def __init__(self, repository: ICleaningTypeRepository) -> None:
        self._repository = repository

    def execute(
        self, cleaning_type_id: int, name: str, hourly_rate: Decimal, active: bool
    ) -> CleaningType:
        existing = self._repository.get_by_id(cleaning_type_id)
        if existing is None:
            raise CleaningTypeNotFoundError(cleaning_type_id)

        updated = CleaningType(
            cleaning_type_id=cleaning_type_id,
            name=name,
            hourly_rate=_normalize_rate(hourly_rate),
            active=active,
        )

        # El nombre debe seguir siendo único (permitiendo conservar el propio).
        clash = self._repository.get_by_name(updated.name)
        if clash is not None and clash.cleaning_type_id != cleaning_type_id:
            raise CleaningTypeAlreadyExistsError(updated.name)

        return self._repository.update(updated)


class DeleteCleaningTypeUseCase:
    """Elimina un tipo de limpieza del catálogo."""

    def __init__(self, repository: ICleaningTypeRepository) -> None:
        self._repository = repository

    def execute(self, cleaning_type_id: int) -> None:
        existing = self._repository.get_by_id(cleaning_type_id)
        if existing is None:
            raise CleaningTypeNotFoundError(cleaning_type_id)
        self._repository.delete(cleaning_type_id)


def _normalize_rate(hourly_rate: Decimal) -> Decimal:
    """Valida y redondea la tarifa a 2 decimales."""
    if hourly_rate < 0:
        raise DomainValidationError("La tarifa por hora no puede ser negativa.")
    return hourly_rate.quantize(Decimal("0.01"))
