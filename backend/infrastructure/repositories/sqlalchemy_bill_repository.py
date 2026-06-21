"""
Implementación de IBillRepository usando SQLAlchemy.
"""

from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.bills.entity import Bill
from domain.bills.repository import IBillRepository
from domain.exceptions import BillAlreadyExists, BillNotFound
from infrastructure.models.bill import BillORM


class SQLAlchemyBillRepository(IBillRepository):
    """
    Implementación del repositorio de facturas respaldado por una sesión de SQLAlchemy
    (MySQL vía PyMySQL).
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Interfaz pública (contrato IBillRepository)                        #
    # ------------------------------------------------------------------ #

    def create(self, bill: Bill) -> Bill:
        orm = self._to_orm(bill)
        self._db.add(orm)
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            if bill.record_id is not None and self.exists_for_booking(bill.record_id):
                raise BillAlreadyExists(bill.record_id) from exc
            raise
        self._db.refresh(orm)
        return self._to_entity(orm)

    def get_by_id(self, bill_id: int) -> Bill:
        orm = self._db.get(BillORM, bill_id)
        if orm is None:
            raise BillNotFound(bill_id)
        return self._to_entity(orm)

    def update(self, bill: Bill) -> Bill:
        assert bill.bill_id is not None
        orm = self._db.get(BillORM, bill.bill_id)
        if orm is None:
            raise BillNotFound(bill.bill_id)

        orm.state = bill.state
        orm.paid_at = bill.paid_at

        self._db.commit()
        self._db.refresh(orm)
        return self._to_entity(orm)

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
        query = self._db.query(BillORM)

        if record_id is not None:
            query = query.filter(BillORM.record_id == record_id)
        if apartment_id is not None:
            query = query.filter(BillORM.apartment_id == apartment_id)
        if state is not None:
            query = query.filter(BillORM.state == state)
        if date_from is not None:
            query = query.filter(BillORM.cleaning_date >= date_from)
        if date_to is not None:
            query = query.filter(BillORM.cleaning_date <= date_to)
        if cost_min is not None:
            query = query.filter(BillORM.cost >= cost_min)
        if cost_max is not None:
            query = query.filter(BillORM.cost <= cost_max)

        query = query.order_by(BillORM.bill_id.desc())

        return [self._to_entity(orm) for orm in query.all()]

    def exists_for_booking(self, record_id: int) -> bool:
        return (
            self._db.query(BillORM.bill_id)
            .filter(BillORM.record_id == record_id, BillORM.state != "Cancelada")
            .first()
            is not None
        )

    def list_billed_booking_ids(self) -> set[int]:
        rows = (
            self._db.query(BillORM.record_id)
            .filter(BillORM.record_id.isnot(None), BillORM.state != "Cancelada")
            .distinct()
            .all()
        )
        return {row[0] for row in rows}

    def get_bill_states_by_booking(self) -> dict[int, str]:
        rows = (
            self._db.query(BillORM.record_id, BillORM.state)
            .filter(BillORM.record_id.isnot(None))
            .all()
        )
        return {row[0]: row[1] for row in rows}

    def delete_cancelled_for_booking(self, record_id: int) -> None:
        orm = (
            self._db.query(BillORM)
            .filter(BillORM.record_id == record_id, BillORM.state == "Cancelada")
            .first()
        )
        if orm is not None:
            self._db.delete(orm)
            self._db.commit()

    # ------------------------------------------------------------------ #
    # Helpers privados de conversión                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_entity(orm: BillORM) -> Bill:
        """Convierte una fila BillORM en una entidad de dominio Bill."""
        return Bill(
            bill_id=orm.bill_id,
            record_id=orm.record_id,
            cleaning_date=orm.cleaning_date,
            clean_hours=orm.clean_hours,
            cost=orm.cost,
            hourly_rate=orm.hourly_rate,
            apartment_id=orm.apartment_id,
            state=orm.state,
            paid_at=orm.paid_at,
        )

    @staticmethod
    def _to_orm(bill: Bill) -> BillORM:
        """Convierte una entidad de dominio Bill en una instancia BillORM para persistencia."""
        return BillORM(
            record_id=bill.record_id,
            cleaning_date=bill.cleaning_date,
            clean_hours=bill.clean_hours,
            cost=bill.cost,
            hourly_rate=bill.hourly_rate,
            apartment_id=bill.apartment_id,
            state=bill.state,
            paid_at=bill.paid_at,
        )
