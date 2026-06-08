"""
Enrutador para los apartamentos.
"""


from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_apartment_by_id_query, get_search_apartments_query, require_admin
from api.v1.apartments.schemas import ApartmentResponse
from application.apartments.queries import GetApartmentByIdQuery, SearchApartmentsQuery
from domain.apartments.filters import ApartmentSearchFilters

router = APIRouter(prefix="/apartments", tags=["Apartments"], dependencies=[Depends(require_admin)])


@router.get("/search", response_model=list[ApartmentResponse])
def search_apartments(
    filters: ApartmentSearchFilters = Depends(),
    query: SearchApartmentsQuery = Depends(get_search_apartments_query),
) -> list[ApartmentResponse]:
    """
    Busca apartamentos aplicando los diferentes filtros.
    """

    apartments = query.execute(filters)

    return [ApartmentResponse.model_validate(apartment.model_dump()) for apartment in apartments]


@router.get("/{apartment_id}", response_model=ApartmentResponse)
def get_apartment_by_id(
    apartment_id: str,
    query: GetApartmentByIdQuery = Depends(get_apartment_by_id_query),
) -> ApartmentResponse:
    """
    Obtiene un apartamento por su apartment_id.
    """

    try:
        apartment = query.execute(apartment_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if apartment is None:
        raise HTTPException(
            status_code=404,
            detail="Apartamento no encontrado",
        )

    return ApartmentResponse.model_validate(apartment.model_dump())
