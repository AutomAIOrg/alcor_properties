"""
Enrutador para los apartamentos.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import (
    get_apartment_by_id_query,
    get_apartment_stats_query,
    get_search_apartments_query,
    require_admin,
)
from api.v1.apartments.schemas import ApartmentResponse, ApartmentStatsResponse
from application.apartments.queries import (
    GetApartmentByIdQuery,
    GetApartmentStatsQuery,
    SearchApartmentsQuery,
)
from domain.apartments.filters import ApartmentSearchFilters
from domain.exceptions import ApartmentNotFound

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


@router.get("/stats/{apartment_id}", response_model=ApartmentStatsResponse)
def get_apartment_stats(
    apartment_id: str,
    start_date: date | None = Query(None, description="Filtrar desde esta fecha"),
    end_date: date | None = Query(None, description="Filtrar hasta esta fecha"),
    query: GetApartmentStatsQuery = Depends(get_apartment_stats_query),
) -> ApartmentStatsResponse:
    """
    Devuelve estadísticas de un apartamento: métricas del rango filtrado y desglose anual.
    """
    try:
        stats = query.execute(
            apartment_id,
            start_date=start_date,
            end_date=end_date,
            )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ApartmentNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return ApartmentStatsResponse.model_validate(stats)



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
