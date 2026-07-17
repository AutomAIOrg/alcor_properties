"""
Enrutador raíz de la API v1. Agrupa todos los sub-enrutadores de v1.
"""

from fastapi import APIRouter

from api.v1.apartments.router import router as apartments_router
from api.v1.auth.router import router as auth_router
from api.v1.bills.router import router as bills_router
from api.v1.bookings.router import router as bookings_router
from api.v1.cleaning_types.router import router as cleaning_types_router
from api.v1.settings.router import router as settings_router
from api.v1.users.router import router as users_router
from config import settings

router = APIRouter(prefix=settings.API_PREFIX)

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(bookings_router)
router.include_router(apartments_router)
router.include_router(bills_router)
router.include_router(cleaning_types_router)
router.include_router(settings_router)
