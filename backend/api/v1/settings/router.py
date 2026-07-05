"""
Enrutador de configuración (solo administradores).
"""

from fastapi import APIRouter, Depends

from api.dependencies import (
    get_cleaning_rate_use_case,
    get_current_user,
    get_update_cleaning_rate_use_case,
    require_admin,
    require_cleaning,
)
from api.v1.settings.schemas import CleaningRateResponse, CleaningRateUpdateRequest
from application.settings.use_cases import (
    GetCleaningHourlyRateUseCase,
    UpdateCleaningHourlyRateUseCase,
)
from domain.auth.user_entity import User

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])


@router.get("/cleaning-rate", response_model=CleaningRateResponse)
async def get_cleaning_rate(
    use_case: GetCleaningHourlyRateUseCase = Depends(get_cleaning_rate_use_case),
    _: User = Depends(require_cleaning),
):
    # Lectura permitida a admin y limpiadora (esta última necesita ver la tarifa al facturar).
    return CleaningRateResponse(cleaning_hourly_rate=float(use_case.execute()))


@router.put("/cleaning-rate", response_model=CleaningRateResponse)
async def update_cleaning_rate(
    payload: CleaningRateUpdateRequest,
    use_case: UpdateCleaningHourlyRateUseCase = Depends(get_update_cleaning_rate_use_case),
    _: User = Depends(require_admin),
):
    # Solo el administrador puede modificar la tarifa.
    new_rate = use_case.execute(payload.cleaning_hourly_rate)
    return CleaningRateResponse(cleaning_hourly_rate=float(new_rate))
