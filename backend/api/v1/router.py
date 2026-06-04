"""
Enrutador raíz de la API v1. Agrupa todos los sub-enrutadores de v1.
"""

from fastapi import APIRouter

from api.v1.auth.router import router as auth_router
from api.v1.bookings.router import router as bookings_router
from api.v1.users.router import router as users_router
from config import settings

router = APIRouter(prefix=settings.API_PREFIX)

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(bookings_router)
