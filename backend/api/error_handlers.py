"""
Mapea las excepciones de dominio a respuestas HTTP.

Registra todos los handlers en main.py usando app.add_exception_handler().
"""

from fastapi import Request
from fastapi.responses import JSONResponse


async def booking_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Devuelve un error 404 cuando no se encuentra la reserva."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def apartment_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Devuelve un error 404 cuando no se encuentra el apartamento."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def booking_conflict_handler(request: Request, exc: Exception) -> JSONResponse:
    """Devuelve un error 409 ante un conflicto de reserva."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def domain_validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Devuelve un error 422 por un error de validación de dominio."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def invalid_credentials_handler(request: Request, exc: Exception) -> JSONResponse:
    """Devuelve un error 401 por credenciales inválidas."""
    return JSONResponse(status_code=401, content={"detail": str(exc)})


async def invalid_token_handler(request: Request, exc: Exception) -> JSONResponse:
    """Devuelve un error 401 cuando el token es inválido."""
    return JSONResponse(
        status_code=401, content={"detail": str(exc)}, headers={"WWW-Authenticate": "Bearer"}
    )


async def token_expired_handler(request: Request, exc: Exception) -> JSONResponse:
    """Devuelve un error 401 cuando el token ha expirado."""
    return JSONResponse(
        status_code=401, content={"detail": str(exc)}, headers={"WWW-Authenticate": "Bearer"}
    )


async def user_already_exists_handler(request: Request, exc: Exception) -> JSONResponse:
    """Devuelve un error 409 cuando el usuario ya existe."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def integrity_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Devuelve un error 409 cuando ocurre un error de integridad."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def user_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Devuelve un error 404 cuando el usuario no existe."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def user_database_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Devuelve un error 500 cuando ocurre un error al interactuar con la base de datos de usuarios."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})
