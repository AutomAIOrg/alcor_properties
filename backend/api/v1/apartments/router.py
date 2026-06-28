"""
Enrutador para los apartamentos.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from api.dependencies import (
    get_apartment_by_id_use_case,
    get_apartment_stats_use_case,
    get_create_apartment_use_case,
    get_delete_apartment_use_case,
    get_get_all_apartments_use_case,
    get_search_apartments_use_case,
    get_update_apartment_use_case,
    require_admin,
)
from api.v1.apartments.schemas import (
    ApartmentResponse,
    ApartmentStatsResponse,
    CreateApartmentRequest,
    UpdateApartmentRequest,
)
from application.apartments.use_cases import (
    CreateApartmentUseCase,
    DeleteApartmentUseCase,
    GetAllApartmentsUseCase,
    GetApartmentByIdUseCase,
    GetApartmentStatsUseCase,
    SearchApartmentsUseCase,
    UpdateApartmentUseCase,
)
from domain.apartments.entity import Apartment
from domain.apartments.filters import ApartmentSearchFilters
from domain.exceptions import ApartmentNotFoundError

router = APIRouter(prefix="/apartments", tags=["Apartments"], dependencies=[Depends(require_admin)])


@router.post("/")
def create_apartment(
    new_apartment: Annotated[CreateApartmentRequest, Body(...)],
    create_apartment_use_case: CreateApartmentUseCase = Depends(get_create_apartment_use_case),
):
    """
    Crea un nuevo apartamento.
    """

    create_apartment_use_case.execute(Apartment(**new_apartment.model_dump()))

    return {"message": "Apartamento creado correctamente"}


@router.delete("/{apartment_id}")
def delete_apartment(
    apartment_id: str,
    delete_apartment_use_case: DeleteApartmentUseCase = Depends(get_delete_apartment_use_case),
):
    """
    Elimina un apartamento.
    """
    delete_apartment_use_case.execute(apartment_id)

    return {"message": "Apartamento eliminado correctamente"}


@router.put("/{apartment_id}")
def update_apartment(
    apartment_id: str,
    updated_apartment: Annotated[UpdateApartmentRequest, Body(...)],
    update_apartment_use_case: UpdateApartmentUseCase = Depends(get_update_apartment_use_case),
):
    """
    Actualiza un apartamento.
    """
    update_apartment_use_case.execute(
        Apartment(apartment_id=apartment_id, **updated_apartment.model_dump())
    )

    return {"message": "Apartamento actualizado correctamente"}


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


@router.get("/", response_model=list[ApartmentResponse])
def get_all_apartments(
    get_all_apartments_use_case: GetAllApartmentsUseCase = Depends(get_get_all_apartments_use_case),
) -> list[ApartmentResponse]:
    """
    Obtiene todos los apartamentos para mostrar en el panel de administración.
    """
    apartments = get_all_apartments_use_case.execute()
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
    if (start_date is None) != (end_date is None):
        raise HTTPException(
            status_code=422,
            detail="start_date y end_date deben informarse juntas",
        )

    if start_date is not None and end_date is not None and start_date >= end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date debe ser anterior a end_date",
        )

    try:
        stats = query.execute(
            apartment_id,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ApartmentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return ApartmentStatsResponse.model_validate(stats)
