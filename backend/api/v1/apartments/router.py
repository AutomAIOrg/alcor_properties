"""
Enrutador para los apartamentos.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import (
    get_apartment_by_id_use_case,
    get_apartment_stats_use_case,
    get_search_apartments_use_case,
    require_admin,
)
from api.v1.apartments.schemas import ApartmentResponse, ApartmentStatsResponse
from application.apartments.use_cases import (
    GetApartmentByIdUseCase,
    GetApartmentStatsUseCase,
    SearchApartmentsUseCase,
)
from domain.apartments.filters import ApartmentSearchFilters
from domain.exceptions import ApartmentNotFound

router = APIRouter(prefix="/apartments", tags=["Apartments"], dependencies=[Depends(require_admin)])


@router.get("/search", response_model=list[ApartmentResponse])
def search_apartments(
    filters: Annotated[ApartmentSearchFilters, Query()],
    search_apartments_use_case: SearchApartmentsUseCase = Depends(get_search_apartments_use_case),
) -> list[ApartmentResponse]:
    """
    Busca apartamentos aplicando los diferentes filtros.
    """

    apartments = search_apartments_use_case.execute(filters)

    return [ApartmentResponse.model_validate(apartment.model_dump()) for apartment in apartments]


@router.get("/{apartment_id}", response_model=ApartmentResponse)
def get_apartment_by_id(
    apartment_id: str,
    get_apartment_by_id_use_case: GetApartmentByIdUseCase = Depends(get_apartment_by_id_use_case),
) -> ApartmentResponse:
    """
    Obtiene un apartamento por su apartment_id.
    """

    try:
        apartment = get_apartment_by_id_use_case.execute(apartment_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if apartment is None:
        raise HTTPException(
            status_code=404,
            detail="Apartamento no encontrado",
        )

    return ApartmentResponse.model_validate(apartment.model_dump())


@router.get("/stats/{apartment_id}", response_model=ApartmentStatsResponse)
def get_apartment_stats(
    apartment_id: str,
    start_date: date | None = Query(None, description="Filtrar desde esta fecha"),
    end_date: date | None = Query(None, description="Filtrar hasta esta fecha"),
    query: GetApartmentStatsUseCase = Depends(get_apartment_stats_use_case),
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
