"""
Enrutador para los apartamentos.
"""


from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import ApartmentUseCases, get_apartment_use_cases, require_admin
from api.v1.apartments.schemas import ApartmentResponse
from domain.apartments.filters import ApartmentSearchFilters

router = APIRouter(prefix="/apartments", tags=["Apartments"], dependencies=[Depends(require_admin)])


@router.get("/search", response_model=list[ApartmentResponse])
def search_apartments(
    filters: ApartmentSearchFilters = Depends(),
    use_cases: ApartmentUseCases = Depends(get_apartment_use_cases),
) -> list[ApartmentResponse]:
    """
    Busca apartamentos aplicando los diferentes filtros.
    """

    apartments = use_cases.search_apartments.execute(filters)

    return [ApartmentResponse.model_validate(apartment.model_dump()) for apartment in apartments]


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

    return ApartmentResponse.model_validate(apartment.model_dump())
