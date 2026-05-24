"""
Enrutador raíz de la API v1. Agrupa todos los sub-enrutadores de v1.
"""

from fastapi import APIRouter

from api.v1.bookings.router import router as bookings_router
from api.v1.searches.router import router as searches_router
from config import settings

router = APIRouter(prefix=settings.API_PREFIX)

router.include_router(bookings_router)
router.include_router(searches_router)
