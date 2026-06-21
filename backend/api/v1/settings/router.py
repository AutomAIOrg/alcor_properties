"""
Enrutador de configuración (solo administradores).
"""

from fastapi import APIRouter, Depends

from api.dependencies import (
    get_cleaning_rate_query,
    get_update_cleaning_rate_use_case,
    require_admin,
)
from api.v1.settings.schemas import CleaningRateResponse, CleaningRateUpdateRequest
from application.settings.use_cases import (
    GetCleaningHourlyRateUseCase,
    UpdateCleaningHourlyRateUseCase,
)

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_admin)])


@router.get("/cleaning-rate", response_model=CleaningRateResponse)
async def get_cleaning_rate(
    use_case: GetCleaningHourlyRateUseCase = Depends(get_cleaning_rate_query),
):
    return CleaningRateResponse(cleaning_hourly_rate=float(use_case.execute()))


@router.put("/cleaning-rate", response_model=CleaningRateResponse)
async def update_cleaning_rate(
    payload: CleaningRateUpdateRequest,
    use_case: UpdateCleaningHourlyRateUseCase = Depends(get_update_cleaning_rate_use_case),
):
    new_rate = use_case.execute(payload.cleaning_hourly_rate)
    return CleaningRateResponse(cleaning_hourly_rate=float(new_rate))
