"""
Contenedor de inyección de dependencias para FastAPI.
"""

import logging
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from application.apartments.use_cases import (
    GetApartmentByIdUseCase,
    GetApartmentStatsUseCase,
    SearchApartmentsUseCase,
)
from application.auth.login_use_case import LoginUseCase
from application.auth.refresh_token_use_case import RefreshTokenUseCase
from application.auth.token_manager_interface import ITokenManager
from application.bookings.commands import (
    CreateBookingUseCase,
    DeleteBookingUseCase,
    UpdateBookingUseCase,
)
from application.bookings.queries import (
    GetActiveBookingsQuery,
    GetBookingByIdQuery,
    GetBookingStatsQuery,
    GetCalendarEventsQuery,
    GetCleaningOpportunitiesUseCase,
    GetUpcomingCheckinsQuery,
    GetUpcomingCheckoutsQuery,
    ListBookingsQuery,
)
from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from application.users.create_user_use_case import CreateUserUseCase
from application.users.delete_user_use_case import DeleteUserUseCase
from application.users.get_all_users_use_case import GetAllUsersUseCase
from application.users.update_user_use_case import UpdateUserUseCase
from config import settings
from domain.apartments.repository import IApartmentRepository
from domain.auth.user_entity import Role, User
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
from infrastructure.security.passlib_password_manager import PasslibPasswordManager

bearer_scheme = HTTPBearer(auto_error=False)  # Esquema de autenticación Bearer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dependencias primitivas
# ---------------------------------------------------------------------------


def get_user_repository(db: Session = Depends(get_db)) -> IUserRepository:
    """Repositorio de usuarios."""
    return SQLAlchemyUserRepository(db)


def get_token_manager() -> ITokenManager:
    """Manager de tokens."""
    return JwtTokenManager()


def get_password_manager() -> IPasswordManager:
    """Verificador de contraseñas."""
    return PasslibPasswordManager()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token_manager: ITokenManager = Depends(get_token_manager),
    user_repository: IUserRepository = Depends(get_user_repository),
) -> User:
    """Decodifica el token y devuelve el payload."""
    if credentials is None:
        raise InvalidToken("Token de autenticación no proporcionado.")

    token = token_manager.decode_access_token(credentials.credentials)

    try:
        user_id = int(token.subject)
    except (TypeError, ValueError) as exc:
        logger.warning("Subject del token no válido")
        raise InvalidToken("Subject del token no válido.") from exc

    user = user_repository.get_by_id(user_id)
    if user is None:
        raise InvalidToken("Usuario del token no encontrado.")
    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verifica que el usuario tenga el rol de administrador."""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=403, detail="Permiso denegado. El usuario no es administrador."
        )
    return current_user


def require_cleaning(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verifica que el usuario tenga acceso a la organización de limpiezas."""
    if current_user.role not in (Role.ADMIN, Role.LIMPIADORA):
        raise HTTPException(
            status_code=403, detail="Permiso denegado. El usuario no tiene acceso a limpiezas."
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
    password_manager: IPasswordManager = Depends(get_password_manager),
) -> LoginUseCase:
    """Inyección de dependencias para el caso de uso de login."""
    return LoginUseCase(user_repository, token_manager, password_manager)


def get_refresh_token_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
    token_manager: ITokenManager = Depends(get_token_manager),
) -> RefreshTokenUseCase:
    """Inyección de dependencias para renovar access tokens."""
    return RefreshTokenUseCase(user_repository, token_manager)


def get_create_user_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
    password_manager: IPasswordManager = Depends(get_password_manager),
) -> CreateUserUseCase:
    """Inyección de dependencias para crear un usuario."""
    return CreateUserUseCase(user_repository, password_manager)


def get_delete_user_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
) -> DeleteUserUseCase:
    """Inyección de dependencias para eliminar un usuario."""
    return DeleteUserUseCase(user_repository)


def get_update_user_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
) -> UpdateUserUseCase:
    """Inyección de dependencias para actualizar un usuario."""
    return UpdateUserUseCase(user_repository)


def get_get_all_users_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
) -> GetAllUsersUseCase:
    """Inyección de dependencias para obtener todos los usuarios."""
    return GetAllUsersUseCase(user_repository)


@dataclass
class BookingUseCases:
    """Casos de uso de reservas."""

    list_query: ListBookingsQuery
    get_by_id_query: GetBookingByIdQuery
    get_active_query: GetActiveBookingsQuery
    upcoming_checkins_query: GetUpcomingCheckinsQuery
    upcoming_checkouts_query: GetUpcomingCheckoutsQuery
    calendar_events_query: GetCalendarEventsQuery
    get_cleaning_opportunities_query: GetCleaningOpportunitiesUseCase
    stats_query: GetBookingStatsQuery
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
        get_cleaning_opportunities_query=GetCleaningOpportunitiesUseCase(repo),
        stats_query=GetBookingStatsQuery(repo, electric_ids),
        create_command=CreateBookingUseCase(repo, electric_ids),
        update_command=UpdateBookingUseCase(repo, electric_ids),
        delete_command=DeleteBookingUseCase(repo),
    )


def get_apartment_by_id_use_case(
    repository: IApartmentRepository = Depends(get_apartment_repository),
) -> GetApartmentByIdUseCase:
    """Inyección de dependencias para el caso de uso de obtener un apartamento por ID."""
    return GetApartmentByIdUseCase(repository)


def get_search_apartments_use_case(
    repository: IApartmentRepository = Depends(get_apartment_repository),
) -> SearchApartmentsUseCase:
    """Inyección de dependencias para el caso de uso de búsqueda de apartamentos."""
    return SearchApartmentsUseCase(repository)


def get_apartment_stats_use_case(
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
    booking_repository: IBookingRepository = Depends(get_booking_repository),
    electric_apartment_ids: set[str] = Depends(get_electric_ids),
) -> GetApartmentStatsUseCase:
    """Inyección de dependencias para el caso de uso de estadísticas de apartamentos."""
    return GetApartmentStatsUseCase(
        apartment_repository, booking_repository, electric_apartment_ids
    )
