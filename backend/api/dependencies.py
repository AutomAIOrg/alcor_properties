"""
Contenedor de inyección de dependencias para FastAPI.
"""

from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy.orm import Session

from application.bookings.commands import (
    CreateBookingUseCase,
    DeleteBookingUseCase,
    UpdateBookingUseCase,
)
from application.bookings.queries import (
    GetActiveBookingsQuery,
    GetBookingByIdQuery,
    GetCalendarEventsQuery,
    GetUpcomingCheckinsQuery,
    GetUpcomingCheckoutsQuery,
    ListBookingsQuery,
)
from config import settings
from domain.bookings.repository import IBookingRepository
from infrastructure.database.session import get_db
from infrastructure.repositories.sqlalchemy_booking_repository import (
    SQLAlchemyBookingRepository,
)

# ---------------------------------------------------------------------------
# Dependencias primitivas
# ---------------------------------------------------------------------------


def get_electric_ids() -> set[str]:
    """Parsea la variable de entorno ELECTRIC a un set de IDs de reservas."""
    return {b.strip() for b in settings.ELECTRIC.split(",") if b.strip()}


def get_booking_repository(db: Session = Depends(get_db)) -> IBookingRepository:
    """Repositorio de reservas."""
    return SQLAlchemyBookingRepository(db)


# ---------------------------------------------------------------------------
# Casos de uso
# ---------------------------------------------------------------------------


@dataclass
class BookingUseCases:
    """Casos de uso de reservas."""

    list_query: ListBookingsQuery
    get_by_id_query: GetBookingByIdQuery
    get_active_query: GetActiveBookingsQuery
    upcoming_checkins_query: GetUpcomingCheckinsQuery
    upcoming_checkouts_query: GetUpcomingCheckoutsQuery
    calendar_events_query: GetCalendarEventsQuery
    create_command: CreateBookingUseCase
    update_command: UpdateBookingUseCase
    delete_command: DeleteBookingUseCase


def get_booking_use_cases(
    repo: IBookingRepository = Depends(get_booking_repository),
    electric_ids: set[str] = Depends(get_electric_ids),
) -> BookingUseCases:
    """Inyección de dependencias para los casos de uso de reservas."""
    return BookingUseCases(
        list_query=ListBookingsQuery(repo, electric_ids),
        get_by_id_query=GetBookingByIdQuery(repo, electric_ids),
        get_active_query=GetActiveBookingsQuery(repo, electric_ids),
        upcoming_checkins_query=GetUpcomingCheckinsQuery(repo, electric_ids),
        upcoming_checkouts_query=GetUpcomingCheckoutsQuery(repo, electric_ids),
        calendar_events_query=GetCalendarEventsQuery(repo, electric_ids),
        create_command=CreateBookingUseCase(repo, electric_ids),
        update_command=UpdateBookingUseCase(repo, electric_ids),
        delete_command=DeleteBookingUseCase(repo),
    )
