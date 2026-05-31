"""
Enrutador para los apartamentos.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import ApartmentUseCases, get_apartment_use_cases, require_admin
from api.v1.apartments.schemas import ApartmentResponse
from domain.apartments.filters import ApartmentSearchFilters

router = APIRouter(prefix="/apartments", tags=["Apartments"], dependencies=[Depends(require_admin)])


@router.get("/search", response_model=list[ApartmentResponse])
def search_apartments(
    q: str | None = Query(default=None),
    booking_id: str | None = Query(default=None),
    community: str | None = Query(default=None),
    booking_name: str | None = Query(default=None),
    address: str | None = Query(default=None),
    parking: str | None = Query(default=None),
    owner_name: str | None = Query(default=None),
    email: str | None = Query(default=None),
    phone: str | None = Query(default=None),
    min_rooms: int | None = Query(default=None, ge=0),
    max_rooms: int | None = Query(default=None, ge=0),
    min_bathrooms: int | None = Query(default=None, ge=0),
    max_bathrooms: int | None = Query(default=None, ge=0),
    min_occupants: int | None = Query(default=None, ge=0),
    max_occupants: int | None = Query(default=None, ge=0),
    available_from: date | None = Query(default=None),
    available_to: date | None = Query(default=None),
    use_cases: ApartmentUseCases = Depends(get_apartment_use_cases),
) -> list[ApartmentResponse]:
    """
    Busca apartamentos aplicando los diferentes filtros.
    """

    try:
        filters = ApartmentSearchFilters(
            q=q,
            booking_id=booking_id,
            community=community,
            booking_name=booking_name,
            address=address,
            parking=parking,
            owner_name=owner_name,
            email=email,
            phone=phone,
            min_rooms=min_rooms,
            max_rooms=max_rooms,
            min_bathrooms=min_bathrooms,
            max_bathrooms=max_bathrooms,
            min_occupants=min_occupants,
            max_occupants=max_occupants,
            available_from=available_from,
            available_to=available_to,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return use_cases.search_apartments.execute(filters)


@router.get("/{booking_id}", response_model=ApartmentResponse)
def get_apartment_by_booking_id(
    booking_id: str,
    use_cases: ApartmentUseCases = Depends(get_apartment_use_cases),
) -> ApartmentResponse:
    """
    Obtiene un apartamento por su booking_id.
    """

    try:
        apartment = use_cases.get_apartment_by_booking_id.execute(booking_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if apartment is None:
        raise HTTPException(
            status_code=404,
            detail="Apartamento no encontrado",
        )

    return apartment
