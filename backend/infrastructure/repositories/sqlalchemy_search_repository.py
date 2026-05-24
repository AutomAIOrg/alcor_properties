from datetime import date

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Query, Session

from api.v1.searches.schemas import BookingSearchFilters
from infrastructure.models.apartment import ApartmentORM
from infrastructure.models.booking import BookingORM


class SQLAlchemySearchRepository:
    """
    Repositorio para consultar reservas y apartamentos con filtros complejos, respaldado por una sesión de SQLAlchemy
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ----------------------------------------------------------------- #
    # Interfaz pública (contrato ISearchRepository)                     #
    # ----------------------------------------------------------------- #

    def search_bookings(
        self,
        filters: BookingSearchFilters,
    ) -> tuple[list[tuple[BookingORM, ApartmentORM | None]], int]:
        """
        Busca reservas aplicando filtros, ordenación y paginación

        Devuelve:
        - rows: lista de tuplas (BookingORM, ApartmentORM | None)
        - total: número de resultados antes de aplicar paginación (limit, offset)
        """

        # LEFT JOIN: conserva las reservas aunque no tengan apartamento asociado
        query = self._db.query(BookingORM, ApartmentORM).outerjoin(
            ApartmentORM,
            BookingORM.booking_id == ApartmentORM.booking_id,
        )

        # Los filtros se combinan acumulativamente con AND
        query = self._apply_filters(query, filters)

        # Total filtrado antes de paginar
        total = query.count()

        # Ordenación mediante whitelist
        sort_column = self._sort_column(filters.sort_by)

        if filters.sort_dir == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()

        # Ordenación secundaria por record_id
        rows = (
            query.order_by(sort_column, BookingORM.record_id.asc())
            .offset(filters.offset)
            .limit(filters.limit)
            .all()
        )

        return rows, total

    def get_options(self) -> tuple[list[str], list[str]]:
        """
        Obtiene las opciones disponibles para los filtros de búsqueda

        Devuelve:
        - booking_ids: lista de booking_id únicos en la tabla de reservas
        - statuses: lista de estados únicos en la tabla de reservas
        """
        booking_ids = [
            row[0]
            for row in self._db.query(ApartmentORM.booking_id)
            .distinct()
            .order_by(ApartmentORM.booking_id)
            .all()
            if row[0]
        ]

        statuses = [
            row[0]
            for row in self._db.query(BookingORM.status)
            .distinct()
            .order_by(BookingORM.status)
            .all()
            if row[0]
        ]

        return booking_ids, statuses

    # ----------------------------------------------------------------- #
    # Helpers privados
    # ----------------------------------------------------------------- #

    def _apply_filters(
        self,
        query: Query,
        filters: BookingSearchFilters,
    ) -> Query:
        """
        Aplica todos los filtros de búsqueda sobre la query Base
        """

        q = filters.q.strip().lower() if filters.q else ""

        if q:
            pattern = f"%{q}%"

            query = query.filter(
                or_(
                    # Campos de reserva
                    func.lower(BookingORM.booking_id).like(pattern),
                    func.lower(BookingORM.booking_number).like(pattern),
                    func.lower(BookingORM.guest_name).like(pattern),
                    func.lower(BookingORM.email).like(pattern),
                    func.lower(BookingORM.phone).like(pattern),
                    func.lower(BookingORM.status).like(pattern),
                    func.lower(BookingORM.notes).like(pattern),
                    # Campos de apartamento
                    func.lower(ApartmentORM.community).like(pattern),
                    func.lower(ApartmentORM.booking_name).like(pattern),
                    func.lower(ApartmentORM.address).like(pattern),
                    func.lower(ApartmentORM.owner_name).like(pattern),
                    func.lower(ApartmentORM.owner_email).like(pattern),
                    func.lower(ApartmentORM.owner_phone).like(pattern),
                )
            )

        if filters.booking_ids:
            query = query.filter(BookingORM.booking_id.in_(filters.booking_ids))

        if filters.statuses:
            query = query.filter(BookingORM.status.in_(filters.statuses))

        start, end = self._date_range(filters)

        if start and end:
            if filters.date_mode == "movement":
                # Reservas cuyo check-in o check-out se solapa con el rango dado:
                query = query.filter(
                    or_(
                        BookingORM.check_in.between(start, end),
                        BookingORM.check_out.between(start, end),
                    )
                )
            elif filters.date_mode == "check_in":
                # Reservas cuyo check-in se encuentra dentro del rango dado
                query = query.filter(BookingORM.check_in.between(start, end))
            elif filters.date_mode == "check_out":
                # Reservas cuyo check-out se encuentra dentro del rango dado
                query = query.filter(BookingORM.check_out.between(start, end))
            elif filters.date_mode == "stay":
                # Reservas cuya estancia (check-in a check-out) se solapa con el rango dado
                query = query.filter(
                    and_(
                        BookingORM.check_in <= end,
                        BookingORM.check_out >= start,
                    )
                )

        return query

    def _date_range(
        self,
        filters: BookingSearchFilters,
    ) -> tuple[date | None, date | None]:
        """
        Normaliza el rango de fechas recibido.
        """

        if filters.start_date and filters.end_date:
            return filters.start_date, filters.end_date

        if filters.start_date:
            return filters.start_date, filters.start_date

        if filters.end_date:
            return filters.end_date, filters.end_date

        return None, None

    def _sort_column(
        self,
        sort_by: str,
    ):
        """
        Devuelve la columna ORM permitida para ordenar.
        """

        allowed = {
            "record_id": BookingORM.record_id,
            "booking_id": BookingORM.booking_id,
            "booking_number": BookingORM.booking_number,
            "guest_name": BookingORM.guest_name,
            "check_in": BookingORM.check_in,
            "check_out": BookingORM.check_out,
            "status": BookingORM.status,
            "persons": BookingORM.persons,
            "price": BookingORM.price,
            "community": ApartmentORM.community,
            "booking_name": ApartmentORM.booking_name,
            "owner_name": ApartmentORM.owner_name,
        }

        return allowed.get(sort_by, BookingORM.check_in)
