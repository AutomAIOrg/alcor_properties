"""
Aplicación FastAPI del proyecto.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.error_handlers import (
    booking_conflict_handler,
    booking_not_found_handler,
    domain_validation_error_handler,
)
from api.v1.router import router as v1_router
from config import settings
from domain.exceptions import BookingConflict, BookingNotFound, DomainValidationError

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="REST API for Property Management System",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Excepción de dominio → Respuesta HTTP
app.add_exception_handler(BookingNotFound, booking_not_found_handler)
app.add_exception_handler(BookingConflict, booking_conflict_handler)
app.add_exception_handler(DomainValidationError, domain_validation_error_handler)

# Rutas de la API
app.include_router(v1_router)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
