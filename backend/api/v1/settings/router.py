"""
Enrutador de ajustes globales de la aplicación (banner de avisos).

Estado temporal en memoria del proceso: guarda solo si el banner está activado. La lectura
la puede hacer cualquier usuario autenticado (el frontend decide a quién se lo muestra) y
solo la cuenta de desarrollo puede cambiarlo. Al ser algo temporal no se persiste en base
de datos; un reinicio del servidor lo vuelve a dejar activado.
"""

from fastapi import APIRouter, Depends

from api.dependencies import get_current_user, require_developer
from api.v1.settings.schemas import BannerSettingResponse, BannerSettingUpdateRequest
from domain.auth.user_entity import User

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])

# Estado en memoria del banner. Arranca activado.
_banner_state = {"enabled": True}


@router.get("/banner", response_model=BannerSettingResponse)
async def get_banner_setting():
    return BannerSettingResponse(enabled=_banner_state["enabled"])


@router.put("/banner", response_model=BannerSettingResponse)
async def update_banner_setting(
    payload: BannerSettingUpdateRequest,
    _: User = Depends(require_developer),
):
    _banner_state["enabled"] = payload.enabled
    return BannerSettingResponse(enabled=_banner_state["enabled"])
