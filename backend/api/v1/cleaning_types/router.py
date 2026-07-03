"""
Enrutador de tipos de limpieza.

Lectura permitida a admin y limpiadora (esta última los necesita al facturar).
Escritura (crear, editar, eliminar) restringida al administrador.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from api.dependencies import (
    get_create_cleaning_type_use_case,
    get_current_user,
    get_delete_cleaning_type_use_case,
    get_list_cleaning_types_use_case,
    get_update_cleaning_type_use_case,
    require_admin,
    require_cleaning,
)
from api.v1.cleaning_types.schemas import (
    CleaningTypeCreateRequest,
    CleaningTypeResponse,
    CleaningTypeUpdateRequest,
)
from application.cleaning_types.use_cases import (
    CreateCleaningTypeUseCase,
    DeleteCleaningTypeUseCase,
    ListCleaningTypesUseCase,
    UpdateCleaningTypeUseCase,
)
from domain.auth.user_entity import User

router = APIRouter(
    prefix="/cleaning-types", tags=["cleaning-types"], dependencies=[Depends(get_current_user)]
)


@router.get("/", response_model=list[CleaningTypeResponse])
async def list_cleaning_types(
    use_case: Annotated[ListCleaningTypesUseCase, Depends(get_list_cleaning_types_use_case)],
    active_only: bool = Query(False, description="Devolver solo los tipos activos"),
    _: User = Depends(require_cleaning),
):
    return use_case.execute(active_only=active_only)


@router.post("/", response_model=CleaningTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_cleaning_type(
    payload: CleaningTypeCreateRequest,
    use_case: Annotated[CreateCleaningTypeUseCase, Depends(get_create_cleaning_type_use_case)],
    _: User = Depends(require_admin),
):
    return use_case.execute(
        name=payload.name, hourly_rate=payload.hourly_rate, active=payload.active
    )


@router.put("/{cleaning_type_id}", response_model=CleaningTypeResponse)
async def update_cleaning_type(
    cleaning_type_id: int,
    payload: CleaningTypeUpdateRequest,
    use_case: Annotated[UpdateCleaningTypeUseCase, Depends(get_update_cleaning_type_use_case)],
    _: User = Depends(require_admin),
):
    return use_case.execute(
        cleaning_type_id,
        name=payload.name,
        hourly_rate=payload.hourly_rate,
        active=payload.active,
    )


@router.delete("/{cleaning_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cleaning_type(
    cleaning_type_id: int,
    use_case: Annotated[DeleteCleaningTypeUseCase, Depends(get_delete_cleaning_type_use_case)],
    _: User = Depends(require_admin),
):
    use_case.execute(cleaning_type_id)
