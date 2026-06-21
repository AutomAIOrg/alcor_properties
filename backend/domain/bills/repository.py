"""
Interfaz abstracta de repositorio para el dominio de Facturas.
"""

from abc import ABC, abstractmethod
from datetime import date

from domain.bills.entity import Bill


class IBillRepository(ABC):
    """Puerto para las operaciones de persistencia de facturas."""

    @abstractmethod
    def create(self, bill: Bill) -> Bill:
        """
        Persiste una nueva factura y la devuelve con el *bill_id* asignado.

        La *bill* recibida debe tener ``bill_id=None``.
        """
        pass

    @abstractmethod
    def get_by_id(self, bill_id: int) -> Bill:
        """
        Devuelve la factura identificada por *bill_id*.

        Excepciones:
            BillNotFound: si no existe una factura con ese ID.
        """
        pass

    @abstractmethod
    def update(self, bill: Bill) -> Bill:
        """
        Persiste los cambios de estado/pago de una factura existente.

        Excepciones:
            BillNotFound: si no existe una factura con *bill.bill_id*.
        """
        pass

    @abstractmethod
    def list(
        self,
        record_id: int | None = None,
        apartment_id: str | None = None,
        state: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        cost_min: float | None = None,
        cost_max: float | None = None,
    ) -> list[Bill]:
        """
        Devuelve las facturas, opcionalmente filtradas por los parámetros proporcionados.
        """
        pass

    @abstractmethod
    def exists_for_booking(self, record_id: int) -> bool:
        """Devuelve True si ya existe alguna factura activa (no cancelada) para *record_id*."""
        pass

    @abstractmethod
    def list_billed_booking_ids(self) -> set[int]:
        """Devuelve el conjunto de *record_id* con factura activa (no cancelada)."""
        pass

    @abstractmethod
    def get_bill_states_by_booking(self) -> dict[int, str]:
        """Devuelve un mapa record_id → estado de factura para todas las facturas."""
        pass

    @abstractmethod
    def delete_cancelled_for_booking(self, record_id: int) -> None:
        """Elimina la factura cancelada asociada a *record_id*, si existe."""
        pass
