"""
Mapea las excepciones de dominio a respuestas HTTP.

Registra todos los handlers en main.py usando app.add_exception_handler().
"""

from fastapi import Request
from fastapi.responses import JSONResponse


async def booking_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def booking_conflict_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def domain_validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})
