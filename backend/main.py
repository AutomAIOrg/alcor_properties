"""
Aplicación FastAPI del proyecto.
"""

import logging

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from api.error_handlers import (
    booking_conflict_handler,
    booking_not_found_handler,
    domain_validation_error_handler,
    integrity_error_handler,
    invalid_credentials_handler,
    invalid_token_handler,
    token_expired_handler,
    user_already_exists_handler,
    user_database_error_handler,
    user_not_found_handler,
)
from api.v1.router import router as v1_router
from config import settings
from domain.exceptions import (
    BookingConflict,
    BookingNotFound,
    DomainValidationError,
    IntegrityError,
    InvalidCredentials,
    InvalidToken,
    TokenExpired,
    UserAlreadyExists,
    UserDatabaseError,
    UserNotFound,
)
from infrastructure.database.session import check_database_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

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
app.add_exception_handler(InvalidCredentials, invalid_credentials_handler)
app.add_exception_handler(InvalidToken, invalid_token_handler)
app.add_exception_handler(TokenExpired, token_expired_handler)
app.add_exception_handler(UserAlreadyExists, user_already_exists_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(UserNotFound, user_not_found_handler)
app.add_exception_handler(UserDatabaseError, user_database_error_handler)

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
def health_check():
    try:
        check_database_connection()
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "unavailable"},
        )
    return {"status": "healthy", "database": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
