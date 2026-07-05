"""
Casos de uso para la configuración de facturación.

El precio por hora de limpieza se persiste en la base de datos para que pueda
cambiarse en caliente. Las facturas que se generen tras un cambio usan el valor nuevo.
"""

from decimal import Decimal, InvalidOperation

from domain.exceptions import DomainValidationError
from domain.settings.repository import ISettingsRepository

CLEANING_HOURLY_RATE_KEY = "cleaning_hourly_rate"


class GetCleaningHourlyRateUseCase:
    """Devuelve el precio por hora de limpieza vigente (o un valor por defecto)."""

    def __init__(self, repository: ISettingsRepository, default: Decimal) -> None:
        self._repo = repository
        self._default = default

    def execute(self) -> Decimal:
        raw = self._repo.get(CLEANING_HOURLY_RATE_KEY)
        if raw is None:
            return self._default
        try:
            return Decimal(raw)
        except InvalidOperation:
            return self._default


class UpdateCleaningHourlyRateUseCase:
    """Actualiza el precio por hora de limpieza usado por las nuevas facturas."""

    def __init__(self, repository: ISettingsRepository) -> None:
        self._repo = repository

    def execute(self, rate: Decimal) -> Decimal:
        if rate < 0:
            raise DomainValidationError("El precio por hora de limpieza no puede ser negativo.")
        normalized = rate.quantize(Decimal("0.01"))
        self._repo.set(CLEANING_HOURLY_RATE_KEY, str(normalized))
        return normalized
