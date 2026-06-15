"""
Implementación de IBookingRepository usando SQLAlchemy.
"""

from datetime import date

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from domain.bookings.entity import NON_BLOCKING_STATUSES, Booking
from domain.bookings.repository import IBookingRepository
from domain.exceptions import BookingNotFound
from infrastructure.models.booking import BookingORM


class SQLAlchemyBookingRepository(IBookingRepository):
    """
    Implementación del repositorio de reservas respaldado por una sesión de SQLAlchemy
    (MySQL vía PyMySQL).
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Interfaz pública (contrato IBookingRepository)                     #
    # ------------------------------------------------------------------ #

    def get_by_id(self, record_id: int) -> Booking:
        orm = self._db.get(BookingORM, record_id)
        if orm is None:
            raise BookingNotFound(record_id)
        return self._to_entity(orm)

    def list(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int | None = None,
        apartment_id: str | None = None,
        status: str | None = None,
        guest_name: str | None = None,
        booking_number: str | None = None,
    ) -> list[Booking]:
        query = self._db.query(BookingORM)

        if start_date is not None and end_date is not None:
            # Solape de intervalos semiabiertos: [check_in, check_out)
            query = query.filter(
                and_(
                    BookingORM.check_in < end_date,
                    BookingORM.check_out > start_date,
                )
            ).order_by(BookingORM.check_in)

        if apartment_id is not None:
            query = query.filter(BookingORM.apartment_id == apartment_id)

        if status is not None:
            query = query.filter(func.lower(BookingORM.status) == status.lower())

        if guest_name is not None:
            query = query.filter(
                func.lower(BookingORM.guest_name).like(f"%{guest_name.strip().lower()}%")
            )

        if booking_number is not None:
            query = query.filter(
                func.lower(BookingORM.booking_number).like(f"%{booking_number.strip().lower()}%")
            )

        if limit is not None:
            query = query.limit(limit)

        return [self._to_entity(orm) for orm in query.all()]

    def create(self, booking: Booking) -> Booking:
        orm = self._to_orm(booking)
        self._db.add(orm)
        self._db.commit()
        self._db.refresh(orm)
        return self._to_entity(orm)

    def update(self, booking: Booking) -> Booking:
        orm = self._db.get(BookingORM, booking.record_id)
        if orm is None:
            assert booking.record_id is not None
            raise BookingNotFound(booking.record_id)

        orm.apartment_id = booking.apartment_id
        orm.guest_name = booking.guest_name
        orm.check_in = booking.check_in
        orm.check_out = booking.check_out
        orm.nights = booking.nights
        orm.status = booking.status
        orm.persons = booking.persons
        orm.adults = booking.adults
        orm.children = booking.children
        orm.price = booking.price
        orm.charges = booking.charges
        orm.email = booking.email
        orm.phone = booking.phone
        orm.booking_number = booking.booking_number
        orm.notes = booking.notes

        self._db.commit()
        self._db.refresh(orm)
        return self._to_entity(orm)

    def delete(self, record_id: int) -> None:
        orm = self._db.get(BookingORM, record_id)
        if orm is None:
            raise BookingNotFound(record_id)
        self._db.delete(orm)
        self._db.commit()

    def find_overlapping_active(self, apartment_id: str, check_in: date, check_out: date) -> bool:
        return (
            self._db.query(BookingORM)
            .filter(
                BookingORM.apartment_id == apartment_id,
                BookingORM.check_in < check_out,
                BookingORM.check_out > check_in,
                or_(
                    BookingORM.status.is_(None),
                    func.lower(BookingORM.status).notin_(NON_BLOCKING_STATUSES),
                ),
            )
            .first()
            is not None
        )

    # ------------------------------------------------------------------ #
    # Helpers privados de conversión                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_entity(orm: BookingORM) -> Booking:
        """Convierte una fila BookingORM en una entidad de dominio Booking."""
        nights = orm.nights or (orm.check_out - orm.check_in).days

        return Booking(
            record_id=orm.record_id,
            apartment_id=orm.apartment_id,
            guest_name=orm.guest_name or "Unknown",
            check_in=orm.check_in,
            check_out=orm.check_out,
            nights=nights,
            status=orm.status or "Confirmed",
            persons=orm.persons or 1,
            adults=orm.adults or 1,
            children=orm.children or 0,
            price=orm.price,
            charges=orm.charges,
            email=orm.email,
            phone=orm.phone,
            booking_number=orm.booking_number,
            notes=orm.notes,
        )

    @staticmethod
    def _to_orm(booking: Booking) -> BookingORM:
        """Convierte una entidad de dominio Booking en una instancia BookingORM para persistencia."""
        return BookingORM(
            apartment_id=booking.apartment_id,
            guest_name=booking.guest_name,
            check_in=booking.check_in,
            check_out=booking.check_out,
            nights=booking.nights,
            status=booking.status,
            persons=booking.persons,
            adults=booking.adults,
            children=booking.children,
            price=booking.price,
            charges=booking.charges,
            email=booking.email,
            phone=booking.phone,
            booking_number=booking.booking_number,
            notes=booking.notes,
        )
