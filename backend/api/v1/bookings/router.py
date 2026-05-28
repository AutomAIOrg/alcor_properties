"""
Enrutador de reservas.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, status

from api.dependencies import BookingUseCases, get_booking_use_cases, require_admin
from api.v1.bookings.schemas import (
    BookingCreateRequest,
    BookingResponse,
    BookingUpdateRequest,
)
from application.bookings.commands import BookingUpdateData
from domain.bookings.entity import Booking

router = APIRouter(prefix="/bookings", tags=["bookings"], dependencies=[Depends(require_admin)])


@router.get("/", response_model=list[BookingResponse])
async def get_bookings(
    limit: int | None = Query(None, description="Limita el número de resultados"),
    start_date: date | None = Query(None, description="Filtrar desde esta fecha"),
    end_date: date | None = Query(None, description="Filtrar hasta esta fecha"),
    days: int | None = Query(
        None, description="Obtener reservas para los próximos N días desde start_date"
    ),
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
):
    return use_cases.list_query.execute(
        start_date=start_date,
        end_date=end_date,
        days=days,
        limit=limit,
    )


@router.get("/active", response_model=list[BookingResponse])
async def get_active_bookings(
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
):
    return use_cases.get_active_query.execute()


@router.get("/upcoming-checkins", response_model=list[BookingResponse])
async def get_upcoming_checkins(
    days: int = Query(7, description="Cantidad de días a futuro"),
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
):
    return use_cases.upcoming_checkins_query.execute(days=days)


@router.get("/upcoming-checkouts", response_model=list[BookingResponse])
async def get_upcoming_checkouts(
    days: int = Query(7, description="Cantidad de días a futuro"),
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
):
    return use_cases.upcoming_checkouts_query.execute(days=days)


@router.get("/calendar-events")
async def get_calendar_events(
    start_date: date | None = Query(None, description="Fecha de inicio (por defecto hoy)"),
    days: int = Query(90, description="Cantidad de días a incluir"),
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
):
    return use_cases.calendar_events_query.execute(start_date=start_date, days=days)


@router.get("/{record_id}", response_model=BookingResponse)
async def get_booking(
    record_id: int,
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
):
    return use_cases.get_by_id_query.execute(record_id)


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreateRequest,
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
):
    booking = Booking(**payload.model_dump())
    return use_cases.create_command.execute(booking)


@router.put("/{record_id}", response_model=BookingResponse)
async def update_booking(
    record_id: int,
    payload: BookingUpdateRequest,
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
):
    update_data = BookingUpdateData(**payload.model_dump())
    return use_cases.update_command.execute(record_id, update_data)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_booking(
    record_id: int,
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
):
    use_cases.delete_command.execute(record_id)
