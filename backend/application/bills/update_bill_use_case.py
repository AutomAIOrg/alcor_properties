"""
Casos de uso (comandos) para el dominio de Facturas.
"""

from datetime import date, datetime

from application.bills.list_bills_use_cases import enrich_with_apartment_data
from domain.apartments.repository import IApartmentRepository
from domain.auth.user_entity import Role, User
from domain.bills.entity import (
    ALLOWED_BILL_TRANSITIONS,
    BILL_STATE_CANCELLED,
    BILL_STATE_PAID,
    Bill,
)
from domain.bills.repository import IBillRepository
from domain.exceptions import DomainValidationError


def _display_name(user: User) -> str:
    """Nombre completo del usuario para mostrar ('Nombre Apellidos')."""
    return f"{user.name} {user.lastname}".strip() if user.lastname else user.name


class UpdateBillStateUseCase:
    """
    Cambia el estado de una factura existente aplicando las transiciones permitidas.

    El pago requiere doble confirmación: la factura solo pasa a "Pagada" cuando tanto
    administración como la limpiadora lo han confirmado. Cada confirmación registra el
    instante exacto en que se produjo (fecha y hora) junto con el nombre completo de
    quien confirmó (congelado, como snapshot histórico, para "Pago confirmado por
    <Nombre Apellidos> el día <fecha> a las <hora>"); mientras falte la otra confirmación
    la factura permanece en "Creada".

    La fecha de pago (``paid_at``) la declara la limpiadora al confirmar — por defecto
    hoy — y queda registrada aunque la factura siga en "Creada" a la espera de
    administración; la confirmación de administración no la modifica (el ``paid_at``
    que envíe se ignora).

    Cualquier transición que no sea a "Pagada" limpia ambas confirmaciones (revertir a
    "Creada" o cancelar reinician el proceso de pago).

    La nota de cancelación se conserva únicamente al pasar a "Cancelada" y se limpia
    en cualquier otro estado (por ejemplo, al reactivar la factura).
    """

    def __init__(
        self,
        bill_repository: IBillRepository,
        apartment_repository: IApartmentRepository | None = None,
    ) -> None:
        self._bill_repository = bill_repository
        self._apartment_repository = apartment_repository

    def execute(
        self,
        bill_id: int,
        new_state: str,
        actor: User,
        paid_at: date | None = None,
        cancellation_note: str | None = None,
    ) -> Bill:
        bill = self._bill_repository.get_by_id(bill_id)  # lanza BillNotFoundError si no existe

        allowed = ALLOWED_BILL_TRANSITIONS.get(bill.state, set())
        if new_state not in allowed:
            raise DomainValidationError(
                f"No se puede cambiar el estado de '{bill.state}' a '{new_state}'."
            )

        admin_confirmation = bill.paid_confirmed_by_admin
        admin_confirmation_name = bill.paid_confirmed_by_admin_name
        cleaner_confirmation = bill.paid_confirmed_by_cleaner
        cleaner_confirmation_name = bill.paid_confirmed_by_cleaner_name
        resolved_state = new_state
        resolved_paid_at: date | None = None

        if new_state == BILL_STATE_PAID:
            confirmed_at = datetime.now()
            confirmation_name = _display_name(actor)
            # La fecha de pago (paid_at) la declara la limpiadora al confirmar; es un
            # dato distinto del instante exacto de cada confirmación (ahora), que se
            # registra por separado.
            resolved_paid_at = bill.paid_at
            if actor.role == Role.ADMIN:
                if admin_confirmation is not None:
                    raise DomainValidationError(
                        "Administración ya ha confirmado el pago de esta factura."
                    )
                admin_confirmation = confirmed_at
                admin_confirmation_name = confirmation_name
            else:
                if cleaner_confirmation is not None:
                    raise DomainValidationError(
                        "La limpiadora ya ha confirmado el pago de esta factura."
                    )
                cleaner_confirmation = confirmed_at
                cleaner_confirmation_name = confirmation_name
                resolved_paid_at = paid_at or date.today()

            if admin_confirmation is None or cleaner_confirmation is None:
                # Falta la confirmación de la otra parte: la factura sigue en su estado.
                resolved_state = bill.state
        else:
            admin_confirmation = None
            admin_confirmation_name = None
            cleaner_confirmation = None
            cleaner_confirmation_name = None

        note = (cancellation_note or "").strip() or None
        resolved_note = note if resolved_state == BILL_STATE_CANCELLED else None

        updated = bill.model_copy(
            update={
                "state": resolved_state,
                "paid_at": resolved_paid_at,
                "cancellation_note": resolved_note,
                "paid_confirmed_by_admin": admin_confirmation,
                "paid_confirmed_by_admin_name": admin_confirmation_name,
                "paid_confirmed_by_cleaner": cleaner_confirmation,
                "paid_confirmed_by_cleaner_name": cleaner_confirmation_name,
            }
        )
        persisted = self._bill_repository.update(updated)
        # La respuesta lleva la dirección del apartamento para que el recibo pueda
        # mostrarse completo justo después del cambio de estado (sin recargar el listado).
        return enrich_with_apartment_data([persisted], self._apartment_repository)[0]
