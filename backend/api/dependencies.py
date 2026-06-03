"""
Contenedor de inyección de dependencias para FastAPI.
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from application.apartments.queries import GetApartmentByBookingIdQuery, SearchApartmentsQuery
from application.auth.login_use_case import LoginUseCase
from application.auth.password_verifier_interface import IPasswordVerifier
from application.auth.refresh_token_use_case import RefreshTokenUseCase
from application.auth.token_manager_interface import ITokenManager
from application.auth.user_repository_interface import IUserRepository
from application.bookings.commands import (
    CreateBookingUseCase,
    DeleteBookingUseCase,
    UpdateBookingUseCase,
)
from application.bookings.queries import (
    GetActiveBookingsQuery,
    GetBookingByIdQuery,
    GetCalendarEventsQuery,
    GetUpcomingCheckinsQuery,
    GetUpcomingCheckoutsQuery,
    ListBookingsQuery,
)
from config import settings
from domain.apartments.repository import IApartmentRepository
from domain.auth.token_payload_entity import TokenPayload
from domain.auth.user_entity import Role
from domain.bookings.repository import IBookingRepository
from domain.exceptions import InvalidToken
from infrastructure.database.session import get_db
from infrastructure.repositories.sqlalchemy_apartment_repository import (
    SQLAlchemyApartmentRepository,
)
from infrastructure.repositories.sqlalchemy_booking_repository import (
    SQLAlchemyBookingRepository,
)
from infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from infrastructure.security.jwt_token_manager import JwtTokenManager
from infrastructure.security.passlib_password_verifier import PasslibPasswordVerifier

bearer_scheme = HTTPBearer(auto_error=False)  # Esquema de autenticación Bearer

# ---------------------------------------------------------------------------
# Dependencias primitivas
# ---------------------------------------------------------------------------


def get_user_repository(db: Session = Depends(get_db)) -> IUserRepository:
    """Repositorio de usuarios."""
    return SQLAlchemyUserRepository(db)


def get_token_manager() -> ITokenManager:
    """Manager de tokens."""
    return JwtTokenManager()


def get_password_verifier() -> IPasswordVerifier:
    """Verificador de contraseñas."""
    return PasslibPasswordVerifier()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token_manager: ITokenManager = Depends(get_token_manager),
) -> TokenPayload:
    """Decodifica el token y devuelve el payload."""
    if credentials is None:
        raise InvalidToken("Token de autenticación no proporcionado.")
    return token_manager.decode_access_token(credentials.credentials)


def require_admin(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    """Verifica que el usuario tenga el rol de administrador."""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=403, detail="Permiso denegado. El usuario no es administrador."
        )
    return current_user


def get_electric_ids() -> set[str]:
    """Parsea la variable de entorno ELECTRIC a un set de IDs de reservas."""
    return {b.strip() for b in settings.ELECTRIC.split(",") if b.strip()}


def get_booking_repository(db: Session = Depends(get_db)) -> IBookingRepository:
    """Repositorio de reservas."""
    return SQLAlchemyBookingRepository(db)


def get_apartment_repository(db: Session = Depends(get_db)) -> IApartmentRepository:
    """Repositorio de apartamentos."""
    return SQLAlchemyApartmentRepository(db)


# ---------------------------------------------------------------------------
# Casos de uso
# ---------------------------------------------------------------------------


def get_login_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
    token_manager: ITokenManager = Depends(get_token_manager),
    password_verifier: IPasswordVerifier = Depends(get_password_verifier),
) -> LoginUseCase:
    """Inyección de dependencias para el caso de uso de login."""
    return LoginUseCase(user_repository, token_manager, password_verifier)


def get_refresh_token_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
    token_manager: ITokenManager = Depends(get_token_manager),
) -> RefreshTokenUseCase:
    """Inyección de dependencias para renovar access tokens."""
    return RefreshTokenUseCase(user_repository, token_manager)


@dataclass
class BookingUseCases:
    """Casos de uso de reservas."""

    list_query: ListBookingsQuery
    get_by_id_query: GetBookingByIdQuery
    get_active_query: GetActiveBookingsQuery
    upcoming_checkins_query: GetUpcomingCheckinsQuery
    upcoming_checkouts_query: GetUpcomingCheckoutsQuery
    calendar_events_query: GetCalendarEventsQuery
    create_command: CreateBookingUseCase
    update_command: UpdateBookingUseCase
    delete_command: DeleteBookingUseCase


def get_booking_use_cases(
    repo: IBookingRepository = Depends(get_booking_repository),
    electric_ids: set[str] = Depends(get_electric_ids),
) -> BookingUseCases:
    """Inyección de dependencias para los casos de uso de reservas."""
    return BookingUseCases(
        list_query=ListBookingsQuery(repo, electric_ids),
        get_by_id_query=GetBookingByIdQuery(repo, electric_ids),
        get_active_query=GetActiveBookingsQuery(repo, electric_ids),
        upcoming_checkins_query=GetUpcomingCheckinsQuery(repo, electric_ids),
        upcoming_checkouts_query=GetUpcomingCheckoutsQuery(repo, electric_ids),
        calendar_events_query=GetCalendarEventsQuery(repo, electric_ids),
        create_command=CreateBookingUseCase(repo, electric_ids),
        update_command=UpdateBookingUseCase(repo, electric_ids),
        delete_command=DeleteBookingUseCase(repo),
    )


@dataclass
class ApartmentUseCases:
    """Casos de uso de apartamentos."""

    search_apartments: SearchApartmentsQuery
    get_apartment_by_booking_id: GetApartmentByBookingIdQuery


def get_apartment_use_cases(
    repository: IApartmentRepository = Depends(get_apartment_repository),
) -> ApartmentUseCases:
    """Inyección de dependencias para los casos de uso de apartamentos."""
    return ApartmentUseCases(
        search_apartments=SearchApartmentsQuery(repository),
        get_apartment_by_booking_id=GetApartmentByBookingIdQuery(repository),
    )
