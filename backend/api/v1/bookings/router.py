"""
Enrutador de reservas.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import (
    BookingUseCases,
    get_booking_use_cases,
    get_current_user,
    require_admin,
    require_cleaning,
)
from api.v1.bookings.schemas import (
    BookingCreateRequest,
    BookingResponse,
    BookingStatsResponse,
    BookingUpdateRequest,
    CleaningOpportunityResponse,
)
from application.bookings.commands import BookingUpdateData
from domain.auth.user_entity import User
from domain.bookings.entity import Booking

router = APIRouter(prefix="/bookings", tags=["bookings"], dependencies=[Depends(get_current_user)])


def _validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if start_date is not None and end_date is not None and start_date >= end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date debe ser anterior a end_date",
        )


@router.get("/", response_model=list[BookingResponse])
async def get_bookings(
    limit: int | None = Query(None, description="Limita el numero de resultados"),
    start_date: date | None = Query(None, description="Filtrar desde esta fecha"),
    end_date: date | None = Query(None, description="Filtrar hasta esta fecha"),
    days: int | None = Query(
        None, ge=1, description="Obtener reservas para los proximos N dias desde start_date"
    ),
    apartment_id: str | None = Query(None, description="Filtrar por ID de apartamento (exacto)"),
    status: str | None = Query(None, description="Filtrar por estado de reserva"),
    guest_name: str | None = Query(None, description="Filtrar por nombre de huesped (parcial)"),
    booking_number: str | None = Query(None, description="Filtrar por numero de reserva (parcial)"),
    search: str | None = Query(
        None, description="Buscar por huesped, numero de reserva o ID de reserva (parcial, OR)"
    ),
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
    _: User = Depends(require_admin),
):
    _validate_date_range(start_date, end_date)
    return use_cases.list_query.execute(
        start_date=start_date,
        end_date=end_date,
        days=days,
        limit=limit,
        apartment_id=apartment_id,
        status=status,
        guest_name=guest_name,
        booking_number=booking_number,
        search=search,
    )


@router.get("/stats", response_model=BookingStatsResponse)
async def get_booking_stats(
    start_date: date | None = Query(None, description="Filtrar desde esta fecha"),
    end_date: date | None = Query(None, description="Filtrar hasta esta fecha"),
    days: int | None = Query(None, ge=1, description="Calcular stats para los proximos N dias"),
    apartment_id: str | None = Query(None, description="Filtrar por ID de apartamento"),
    status: str | None = Query(None, description="Filtrar por estado"),
    guest_name: str | None = Query(None, description="Filtrar por nombre de huesped"),
    booking_number: str | None = Query(None, description="Filtrar por numero de reserva"),
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
):
    _validate_date_range(start_date, end_date)
    return use_cases.stats_query.execute(
        start_date=start_date,
        end_date=end_date,
        days=days,
        apartment_id=apartment_id,
        status=status,
        guest_name=guest_name,
        booking_number=booking_number,
    )


@router.get("/active", response_model=list[BookingResponse])
async def get_active_bookings(
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
    _: User = Depends(require_admin),
):
    return use_cases.get_active_query.execute()


@router.get("/upcoming-checkins", response_model=list[BookingResponse])
async def get_upcoming_checkins(
    days: int = Query(7, ge=1, description="Cantidad de dias a futuro"),
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
    _: User = Depends(require_admin),
):
    return use_cases.upcoming_checkins_query.execute(days=days)


@router.get("/upcoming-checkouts", response_model=list[BookingResponse])
async def get_upcoming_checkouts(
    days: int = Query(7, ge=1, description="Cantidad de dias a futuro"),
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
    _: User = Depends(require_admin),
):
    return use_cases.upcoming_checkouts_query.execute(days=days)


@router.get("/calendar-events")
async def get_calendar_events(
    start_date: date | None = Query(None, description="Fecha de inicio (por defecto hoy)"),
    days: int = Query(90, ge=1, description="Cantidad de dias a incluir"),
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
    _: User = Depends(require_admin),
):
    return use_cases.calendar_events_query.execute(start_date=start_date, days=days)


@router.get("/cleaning-opportunities", response_model=list[CleaningOpportunityResponse])
async def get_cleaning_opportunities(
    week_start: date | None = Query(
        None, description="Ancla el rango operativo en esa semana (por defecto, la actual)"
    ),
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
    _: User = Depends(require_cleaning),
):
    return use_cases.get_cleaning_opportunities_query.execute(week_start=week_start)


@router.get("/{record_id}", response_model=BookingResponse)
async def get_booking(
    record_id: int,
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
    _: User = Depends(require_admin),
):
    return use_cases.get_by_id_query.execute(record_id)


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreateRequest,
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
    _: User = Depends(require_admin),
):
    booking = Booking(**payload.model_dump())
    return use_cases.create_command.execute(booking)


@router.put("/{record_id}", response_model=BookingResponse)
async def update_booking(
    record_id: int,
    payload: BookingUpdateRequest,
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
    _: User = Depends(require_admin),
):
    update_data = BookingUpdateData(**payload.model_dump(exclude_unset=True))
    return use_cases.update_command.execute(record_id, update_data)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_booking(
    record_id: int,
    use_cases: BookingUseCases = Depends(get_booking_use_cases),
    _: User = Depends(require_admin),
):
    use_cases.delete_command.execute(record_id)
