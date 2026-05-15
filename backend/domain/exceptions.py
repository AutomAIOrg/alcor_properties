"""
Excepciones de dominio para el backend de Alcor Properties.

Estas son excepciones puramente de negocio sin dependencia de frameworks HTTP.
La capa de API asigna cada excepción al código de estado HTTP apropiado.
"""


class DomainException(Exception):
    """Clase base para todas las excepciones de dominio."""

    pass


class BookingNotFound(DomainException):
    """Se lanza cuando no se puede encontrar una reserva por su identificador."""

    def __init__(self, record_id: int) -> None:
        self.record_id = record_id
        super().__init__(f"Reserva con ID {record_id} no encontrada")


class BookingConflict(DomainException):
    """Se lanza cuando una reserva se superpone con otra existente en las mismas fechas."""

    def __init__(self, check_in: str = "", check_out: str = "") -> None:
        detail = (
            f"Ya existe una reserva entre {check_in} y {check_out}"
            if check_in and check_out
            else "La reserva entra en conflicto con una reserva existente"
        )
        super().__init__(detail)


class DomainValidationError(DomainException):
    """Se lanza cuando se viola una regla de negocio (por ejemplo, check-out antes que check-in)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
