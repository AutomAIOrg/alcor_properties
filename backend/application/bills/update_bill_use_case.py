"""
Casos de uso (comandos) para el dominio de Facturas.
"""

from datetime import date

from domain.bills.entity import (
    ALLOWED_BILL_TRANSITIONS,
    BILL_STATE_CANCELLED,
    BILL_STATE_PAID,
    Bill,
)
from domain.bills.repository import IBillRepository
from domain.exceptions import DomainValidationError


class UpdateBillStateUseCase:
    """
    Cambia el estado de una factura existente aplicando las transiciones permitidas.

    La fecha de pago se registra automáticamente al pasar a "Pagada" (por defecto hoy,
    o la indicada explícitamente) y se limpia en cualquier otro estado.

    La nota de cancelación se conserva únicamente al pasar a "Cancelada" y se limpia
    en cualquier otro estado (por ejemplo, al reactivar la factura).
    """

    def __init__(self, bill_repository: IBillRepository) -> None:
        self._bill_repository = bill_repository

    def execute(
        self,
        bill_id: int,
        new_state: str,
        paid_at: date | None = None,
        cancellation_note: str | None = None,
    ) -> Bill:
        bill = self._bill_repository.get_by_id(bill_id)  # lanza BillNotFoundError si no existe

        allowed = ALLOWED_BILL_TRANSITIONS.get(bill.state, set())
        if new_state not in allowed:
            raise DomainValidationError(
                f"No se puede cambiar el estado de '{bill.state}' a '{new_state}'."
            )

        resolved_paid_at = (paid_at or date.today()) if new_state == BILL_STATE_PAID else None

        note = (cancellation_note or "").strip() or None
        resolved_note = note if new_state == BILL_STATE_CANCELLED else None

        updated = bill.model_copy(
            update={
                "state": new_state,
                "paid_at": resolved_paid_at,
                "cancellation_note": resolved_note,
            }
        )
        return self._bill_repository.update(updated)
