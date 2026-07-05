"""
Respositorio SQLAlchemy para apartamentos
"""

import logging

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session

from domain.apartments.entity import Apartment
from domain.apartments.filters import ApartmentSearchFilters
from domain.apartments.repository import IApartmentRepository
from domain.bookings.entity import NON_BLOCKING_STATUSES
from domain.exceptions import ApartmentDatabaseError, ApartmentNotFoundError
from infrastructure.models.apartment import ApartmentORM
from infrastructure.models.booking import BookingORM

logger = logging.getLogger(__name__)


class SQLAlchemyApartmentRepository(IApartmentRepository):
    """
    Implementación del respositorio de apartamentos usando SQLAlchemy.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_apartment(self, new_apartment: Apartment) -> None:
        """Crea un nuevo apartamento."""
        new_apartment_orm = ApartmentORM(**new_apartment.model_dump())
        try:
            self._db.add(new_apartment_orm)
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            logger.exception(f"Error al crear el apartamento: {e}")
            raise ApartmentDatabaseError("Error al crear el apartamento.") from e

    def get_by_apartment_id(self, apartment_id: str) -> Apartment | None:
        stmt = select(ApartmentORM).where(ApartmentORM.apartment_id == apartment_id)

        row = self._db.execute(stmt).scalar_one_or_none()

        if row is None:
            return None

        return self._to_domain(row)

    def delete_apartment(self, apartment: Apartment) -> None:
        """Elimina un apartamento."""
        orm = (
            self._db.query(ApartmentORM)
            .filter(ApartmentORM.apartment_id == apartment.apartment_id)
            .first()
        )
        if orm is None:
            raise ApartmentNotFoundError(apartment.apartment_id)
        self._db.delete(orm)
        try:
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            logger.exception(f"Error al eliminar el apartamento: {e}")
            raise ApartmentDatabaseError("Error al eliminar el apartamento.") from e

    def update_apartment(self, updated_apartment: Apartment) -> None:
        """Actualiza un apartamento."""
        orm = (
            self._db.query(ApartmentORM)
            .filter(ApartmentORM.apartment_id == updated_apartment.apartment_id)
            .first()
        )
        if orm is None:
            raise ApartmentNotFoundError(updated_apartment.apartment_id)
        orm.community = updated_apartment.community
        orm.apartment_description = updated_apartment.apartment_description
        orm.address = updated_apartment.address
        orm.rooms = updated_apartment.rooms
        orm.bathrooms = updated_apartment.bathrooms
        orm.parking = updated_apartment.parking
        orm.total_occupants = updated_apartment.total_occupants
        orm.owner_name = updated_apartment.owner_name
        orm.email = updated_apartment.email
        orm.phone = updated_apartment.phone
        try:
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            logger.exception(f"Error al actualizar el apartamento: {e}")
            raise ApartmentDatabaseError("Error al actualizar el apartamento.") from e

    def search_apartments(self, filters: ApartmentSearchFilters) -> list[Apartment]:
        stmt = select(ApartmentORM)

        stmt = self._apply_text_filters(stmt, filters)
        stmt = self._apply_number_filters(stmt, filters)
        stmt = self._apply_availability_filter(stmt, filters)

        stmt = stmt.order_by(ApartmentORM.apartment_id.asc())

        rows = self._db.execute(stmt).scalars().all()

        return [self._to_domain(row) for row in rows]

    def get_all(self) -> list[Apartment]:
        stmt = select(ApartmentORM).order_by(ApartmentORM.apartment_id.asc())
        rows = self._db.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]

    # ------------------------------------------------------------------ #
    # Filtros                                                            #
    # ------------------------------------------------------------------ #

    def _apply_text_filters(
        self,
        stmt: Select[tuple[ApartmentORM]],
        filters: ApartmentSearchFilters,
    ) -> Select[tuple[ApartmentORM]]:
        if filters.q:
            q = f"%{filters.q.strip().lower()}%"

            stmt = stmt.where(
                or_(
                    func.lower(ApartmentORM.apartment_id).like(q),
                    func.lower(ApartmentORM.community).like(q),
                    func.lower(ApartmentORM.apartment_description).like(q),
                    func.lower(ApartmentORM.address).like(q),
                    func.lower(ApartmentORM.parking).like(q),
                    func.lower(ApartmentORM.owner_name).like(q),
                    func.lower(ApartmentORM.email).like(q),
                    func.lower(ApartmentORM.phone).like(q),
                )
            )

        if filters.apartment_id:
            stmt = stmt.where(
                func.lower(ApartmentORM.apartment_id).like(
                    f"%{filters.apartment_id.strip().lower()}%"
                )
            )

        if filters.community:
            stmt = stmt.where(
                func.lower(ApartmentORM.community).like(f"%{filters.community.strip().lower()}%")
            )

        if filters.apartment_description:
            stmt = stmt.where(
                func.lower(ApartmentORM.apartment_description).like(
                    f"%{filters.apartment_description.strip().lower()}%"
                )
            )

        if filters.address:
            stmt = stmt.where(
                func.lower(ApartmentORM.address).like(f"%{filters.address.strip().lower()}%")
            )

        if filters.parking:
            parking_filter = filters.parking.strip().lower()

            if parking_filter == "yes":
                stmt = stmt.where(func.lower(ApartmentORM.parking) != "n/a")
            elif parking_filter == "no":
                stmt = stmt.where(func.lower(ApartmentORM.parking) == "n/a")
            else:
                stmt = stmt.where(
                    func.lower(ApartmentORM.parking).like(f"%{filters.parking.strip().lower()}%")
                )

        if filters.owner_name:
            stmt = stmt.where(
                func.lower(ApartmentORM.owner_name).like(f"%{filters.owner_name.strip().lower()}%")
            )

        if filters.email:
            stmt = stmt.where(
                func.lower(ApartmentORM.email).like(f"%{filters.email.strip().lower()}%")
            )

        if filters.phone:
            stmt = stmt.where(
                func.lower(ApartmentORM.phone).like(f"%{filters.phone.strip().lower()}%")
            )

        return stmt

    def _apply_number_filters(
        self,
        stmt: Select[tuple[ApartmentORM]],
        filters: ApartmentSearchFilters,
    ) -> Select[tuple[ApartmentORM]]:
        if filters.min_rooms is not None:
            stmt = stmt.where(ApartmentORM.rooms >= filters.min_rooms)

        if filters.min_bathrooms is not None:
            stmt = stmt.where(ApartmentORM.bathrooms >= filters.min_bathrooms)

        if filters.min_occupants is not None:
            stmt = stmt.where(ApartmentORM.total_occupants >= filters.min_occupants)

        if filters.max_occupants is not None:
            stmt = stmt.where(ApartmentORM.total_occupants <= filters.max_occupants)

        return stmt

    def _apply_availability_filter(
        self,
        stmt: Select[tuple[ApartmentORM]],
        filters: ApartmentSearchFilters,
    ) -> Select[tuple[ApartmentORM]]:
        if not filters.available_from or not filters.available_to:
            return stmt

        overlapping_booking_exists = exists().where(
            BookingORM.apartment_id == ApartmentORM.apartment_id,
            BookingORM.check_in < filters.available_to,
            BookingORM.check_out > filters.available_from,
            or_(
                BookingORM.status.is_(None),
                func.lower(BookingORM.status).notin_(NON_BLOCKING_STATUSES),
            ),
        )

        return stmt.where(~overlapping_booking_exists)

    # ------------------------------------------------------------------ #
    # Mapper                                                             #
    # ------------------------------------------------------------------ #

    def _to_domain(self, row: ApartmentORM) -> Apartment:
        return Apartment(
            apartment_id=row.apartment_id,
            community=row.community,
            apartment_description=row.apartment_description,
            address=row.address,
            rooms=row.rooms,
            bathrooms=row.bathrooms,
            parking=row.parking,
            total_occupants=row.total_occupants,
            owner_name=row.owner_name,
            email=row.email,
            phone=row.phone,
        )
