"""
Contenedor de inyección de dependencias para FastAPI.
"""

import logging
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from application.apartments.use_cases import (
    CreateApartmentUseCase,
    DeleteApartmentUseCase,
    GetAllApartmentsUseCase,
    GetApartmentByIdUseCase,
    GetApartmentStatsUseCase,
    SearchApartmentsUseCase,
    UpdateApartmentUseCase,
)
from application.auth.change_initial_password_use_case import ChangeInitialPasswordUseCase
from application.auth.change_password_use_case import ChangePasswordUseCase
from application.auth.forgot_password_use_case import ForgotPasswordUseCase
from application.auth.login_use_case import LoginUseCase
from application.auth.refresh_token_use_case import RefreshTokenUseCase
from application.auth.reset_password_use_case import ResetPasswordUseCase
from application.auth.token_manager_interface import ITokenManager
from application.bills.bill_pdf_renderer_interface import IBillPdfRenderer
from application.bills.create_bill_use_case import CreateBillUseCase
from application.bills.generate_and_store_bill_document_use_case import (
    GenerateAndStoreBillDocumentUseCase,
)
from application.bills.list_bills_use_cases import ListBillsUseCase, ListPendingBillsUseCase
from application.bills.move_paid_bill_document_use_case import MovePaidBillDocumentUseCase
from application.bills.render_bill_document_use_case import RenderBillDocumentUseCase
from application.bills.retry_bill_document_sync_use_case import RetryBillDocumentSyncUseCase
from application.bills.update_bill_use_case import RectifyBillUseCase, UpdateBillStateUseCase
from application.bookings.commands import (
    CreateBookingUseCase,
    DeleteBookingUseCase,
    UpdateBookingUseCase,
)
from application.bookings.helpers import ElectricRates
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
from application.cleaning_types.use_cases import (
    CreateCleaningTypeUseCase,
    DeleteCleaningTypeUseCase,
    ListCleaningTypesUseCase,
    UpdateCleaningTypeUseCase,
)
from application.shared.email_sender_interface import IEmailSender
from application.shared.file_storage_interface import IFileStorage
from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from application.users.create_user_use_case import CreateUserUseCase
from application.users.delete_user_use_case import DeleteUserUseCase
from application.users.get_all_users_use_case import GetAllUsersUseCase
from application.users.reset_user_password_use_case import ResetUserPasswordUseCase
from application.users.update_user_use_case import UpdateUserUseCase
from config import settings
from domain.apartments.repository import IApartmentRepository
from domain.auth.user_entity import Role, User
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.bills.repository import IBillRepository
from domain.bookings.repository import IBookingRepository
from domain.cleaning_types.repository import ICleaningTypeRepository
from domain.exceptions import InvalidToken
from infrastructure.database.session import get_db
from infrastructure.documents.chromium_bill_pdf_renderer import ChromiumBillPdfRenderer
from infrastructure.email.smtp_email_sender import ConsoleEmailSender, SMTPEmailSender
from infrastructure.repositories.sqlalchemy_apartment_repository import (
    SQLAlchemyApartmentRepository,
)
from infrastructure.repositories.sqlalchemy_bill_document_repository import (
    SQLAlchemyBillDocumentRepository,
)
from infrastructure.repositories.sqlalchemy_bill_repository import SQLAlchemyBillRepository
from infrastructure.repositories.sqlalchemy_booking_repository import (
    SQLAlchemyBookingRepository,
)
from infrastructure.repositories.sqlalchemy_cleaning_type_repository import (
    SQLAlchemyCleaningTypeRepository,
)
from infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from infrastructure.security.jwt_token_manager import JwtTokenManager
from infrastructure.security.passlib_password_manager import PasslibPasswordManager
from infrastructure.storage.synology_file_storage import SynologyFileStorage

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


def get_email_sender() -> IEmailSender:
    """Emisor de emails. Usa SMTP si está configurado; si no, cae a consola (solo dev)."""
    if settings.SMTP_HOST:
        return SMTPEmailSender(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            sender=settings.SMTP_FROM or settings.SMTP_USER,
            use_tls=settings.SMTP_USE_TLS,
        )
    return ConsoleEmailSender()


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

    if (token.token_version or 0) != user.token_version:
        raise InvalidToken("Token de sesión revocado.")
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


def get_booking_repository(db: Session = Depends(get_db)) -> IBookingRepository:
    """Repositorio de reservas."""
    return SQLAlchemyBookingRepository(db)


def get_apartment_repository(db: Session = Depends(get_db)) -> IApartmentRepository:
    """Repositorio de apartamentos."""
    return SQLAlchemyApartmentRepository(db)


def get_electric_rates(
    repository: IApartmentRepository = Depends(get_apartment_repository),
) -> ElectricRates:
    """Tarifas del cupo eléctrico por apartamento, configuradas desde administración."""
    return repository.get_electric_allowance_rates()


def get_bill_repository(db: Session = Depends(get_db)) -> IBillRepository:
    """Repositorio de facturas."""
    return SQLAlchemyBillRepository(db)


def get_bill_document_repository(db: Session = Depends(get_db)) -> IBillDocumentRepository:
    """Repositorio de documentos de factura."""
    return SQLAlchemyBillDocumentRepository(db)


def get_file_storage() -> IFileStorage:
    """Almacenamiento remoto en NAS Synology."""
    if not settings.NAS_HOST or not settings.NAS_USER:
        raise RuntimeError(
            "NAS no configurado: defina NAS_HOST, NAS_USER y NAS_PASSWORD en el entorno."
        )
    return SynologyFileStorage(
        host=settings.NAS_HOST,
        port=settings.NAS_PORT,
        username=settings.NAS_USER,
        password=settings.NAS_PASSWORD,
        volume_prefix=settings.NAS_VOLUME_PREFIX,
        connect_timeout=settings.NAS_SSH_TIMEOUT,
    )


def get_cleaning_type_repository(db: Session = Depends(get_db)) -> ICleaningTypeRepository:
    """Repositorio de tipos de limpieza."""
    return SQLAlchemyCleaningTypeRepository(db)


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


def get_forgot_password_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
    token_manager: ITokenManager = Depends(get_token_manager),
    email_sender: IEmailSender = Depends(get_email_sender),
) -> ForgotPasswordUseCase:
    """Inyección de dependencias para iniciar el restablecimiento de contraseña."""
    return ForgotPasswordUseCase(
        user_repository, token_manager, email_sender, settings.FRONTEND_URL
    )


def get_reset_password_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
    token_manager: ITokenManager = Depends(get_token_manager),
    password_manager: IPasswordManager = Depends(get_password_manager),
) -> ResetPasswordUseCase:
    """Inyección de dependencias para restablecer la contraseña."""
    return ResetPasswordUseCase(user_repository, token_manager, password_manager)


def get_change_password_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
    password_manager: IPasswordManager = Depends(get_password_manager),
) -> ChangePasswordUseCase:
    """Inyección de dependencias para que un usuario cambie su propia contraseña."""
    return ChangePasswordUseCase(user_repository, password_manager)


def get_change_initial_password_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
    password_manager: IPasswordManager = Depends(get_password_manager),
    token_manager: ITokenManager = Depends(get_token_manager),
) -> ChangeInitialPasswordUseCase:
    """Inyección de dependencias para que un usuario fije su contraseña inicial."""
    return ChangeInitialPasswordUseCase(user_repository, password_manager, token_manager)


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


def get_reset_user_password_use_case(
    user_repository: IUserRepository = Depends(get_user_repository),
    password_manager: IPasswordManager = Depends(get_password_manager),
) -> ResetUserPasswordUseCase:
    """Inyección de dependencias para restablecer la contraseña de un usuario a la inicial."""
    return ResetUserPasswordUseCase(user_repository, password_manager)


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
    bill_repository: IBillRepository = Depends(get_bill_repository),
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
    electric_rates: ElectricRates = Depends(get_electric_rates),
) -> BookingUseCases:
    """Inyección de dependencias para los casos de uso de reservas."""
    return BookingUseCases(
        list_query=ListBookingsQuery(repo, electric_rates),
        get_by_id_query=GetBookingByIdQuery(repo, electric_rates),
        get_active_query=GetActiveBookingsQuery(repo, electric_rates),
        upcoming_checkins_query=GetUpcomingCheckinsQuery(repo, electric_rates),
        upcoming_checkouts_query=GetUpcomingCheckoutsQuery(repo, electric_rates),
        calendar_events_query=GetCalendarEventsQuery(repo, electric_rates),
        get_cleaning_opportunities_query=GetCleaningOpportunitiesUseCase(
            repo, bill_repository, apartment_repository
        ),
        stats_query=GetBookingStatsQuery(repo, electric_rates),
        create_command=CreateBookingUseCase(repo, electric_rates),
        update_command=UpdateBookingUseCase(repo, electric_rates),
        delete_command=DeleteBookingUseCase(repo),
    )


def get_create_apartment_use_case(
    repository: IApartmentRepository = Depends(get_apartment_repository),
) -> CreateApartmentUseCase:
    """Inyección de dependencias para el caso de uso de crear un apartamento."""
    return CreateApartmentUseCase(repository)


def get_delete_apartment_use_case(
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
    booking_repository: IBookingRepository = Depends(get_booking_repository),
) -> DeleteApartmentUseCase:
    """Inyección de dependencias para el caso de uso de eliminar un apartamento."""
    return DeleteApartmentUseCase(apartment_repository, booking_repository)


def get_update_apartment_use_case(
    repository: IApartmentRepository = Depends(get_apartment_repository),
) -> UpdateApartmentUseCase:
    """Inyección de dependencias para el caso de uso de actualizar un apartamento."""
    return UpdateApartmentUseCase(repository)


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


def get_get_all_apartments_use_case(
    repository: IApartmentRepository = Depends(get_apartment_repository),
) -> GetAllApartmentsUseCase:
    """Inyección de dependencias para el caso de uso de obtener todos los apartamentos."""
    return GetAllApartmentsUseCase(repository)


def get_apartment_stats_use_case(
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
    booking_repository: IBookingRepository = Depends(get_booking_repository),
    electric_rates: ElectricRates = Depends(get_electric_rates),
) -> GetApartmentStatsUseCase:
    """Inyección de dependencias para el caso de uso de estadísticas de apartamentos."""
    return GetApartmentStatsUseCase(apartment_repository, booking_repository, electric_rates)


def get_bill_pdf_renderer() -> IBillPdfRenderer:
    """Renderer del PDF de factura (Chromium headless + plantilla del recibo)."""
    return ChromiumBillPdfRenderer(chromium_path=settings.BILL_PDF_CHROMIUM_PATH)


def get_create_bill_use_case(
    bill_repository: IBillRepository = Depends(get_bill_repository),
    booking_repository: IBookingRepository = Depends(get_booking_repository),
    cleaning_type_repository: ICleaningTypeRepository = Depends(get_cleaning_type_repository),
) -> CreateBillUseCase:
    """Inyección de dependencias para el caso de uso de crear una factura."""
    return CreateBillUseCase(bill_repository, booking_repository, cleaning_type_repository)


def get_update_bill_state_use_case(
    bill_repository: IBillRepository = Depends(get_bill_repository),
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
) -> UpdateBillStateUseCase:
    """Inyección de dependencias para el caso de uso de actualizar el estado de una factura."""
    return UpdateBillStateUseCase(bill_repository, apartment_repository)


def get_rectify_bill_use_case(
    bill_repository: IBillRepository = Depends(get_bill_repository),
    cleaning_type_repository: ICleaningTypeRepository = Depends(get_cleaning_type_repository),
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
) -> RectifyBillUseCase:
    """Inyección de dependencias para el caso de uso de rectificar los datos de una factura."""
    return RectifyBillUseCase(bill_repository, cleaning_type_repository, apartment_repository)


def get_list_bills_use_case(
    bill_repository: IBillRepository = Depends(get_bill_repository),
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
) -> ListBillsUseCase:
    """Inyección de dependencias para el caso de uso de obtener todas las facturas."""
    return ListBillsUseCase(bill_repository, apartment_repository)


def get_list_pending_bills_use_case(
    booking_repository: IBookingRepository = Depends(get_booking_repository),
    bill_repository: IBillRepository = Depends(get_bill_repository),
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
) -> ListPendingBillsUseCase:
    """Inyección de dependencias para el caso de uso de obtener todas las facturas pendientes."""
    return ListPendingBillsUseCase(booking_repository, bill_repository, apartment_repository)


def get_list_cleaning_types_use_case(
    repository: ICleaningTypeRepository = Depends(get_cleaning_type_repository),
) -> ListCleaningTypesUseCase:
    """Inyección de dependencias para listar los tipos de limpieza."""
    return ListCleaningTypesUseCase(repository)


def get_create_cleaning_type_use_case(
    repository: ICleaningTypeRepository = Depends(get_cleaning_type_repository),
) -> CreateCleaningTypeUseCase:
    """Inyección de dependencias para crear un tipo de limpieza."""
    return CreateCleaningTypeUseCase(repository)


def get_update_cleaning_type_use_case(
    repository: ICleaningTypeRepository = Depends(get_cleaning_type_repository),
) -> UpdateCleaningTypeUseCase:
    """Inyección de dependencias para actualizar un tipo de limpieza."""
    return UpdateCleaningTypeUseCase(repository)


def get_delete_cleaning_type_use_case(
    repository: ICleaningTypeRepository = Depends(get_cleaning_type_repository),
) -> DeleteCleaningTypeUseCase:
    """Inyección de dependencias para eliminar un tipo de limpieza."""
    return DeleteCleaningTypeUseCase(repository)


def get_generate_and_store_bill_document_use_case(
    bill_repository: IBillRepository = Depends(get_bill_repository),
    document_repository: IBillDocumentRepository = Depends(get_bill_document_repository),
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
    pdf_renderer: IBillPdfRenderer = Depends(get_bill_pdf_renderer),
    file_storage: IFileStorage = Depends(get_file_storage),
) -> GenerateAndStoreBillDocumentUseCase:
    """Inyección de dependencias para generar y almacenar documento de factura en NAS."""
    return GenerateAndStoreBillDocumentUseCase(
        bill_repository,
        document_repository,
        apartment_repository,
        pdf_renderer,
        file_storage,
        settings.NAS_BASE_PATH,
    )


def get_render_bill_document_use_case(
    bill_repository: IBillRepository = Depends(get_bill_repository),
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
    pdf_renderer: IBillPdfRenderer = Depends(get_bill_pdf_renderer),
) -> RenderBillDocumentUseCase:
    """Inyección de dependencias para descargar el recibo de una factura (sin NAS)."""
    return RenderBillDocumentUseCase(bill_repository, apartment_repository, pdf_renderer)


def get_move_paid_bill_document_use_case(
    bill_repository: IBillRepository = Depends(get_bill_repository),
    document_repository: IBillDocumentRepository = Depends(get_bill_document_repository),
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
    pdf_renderer: IBillPdfRenderer = Depends(get_bill_pdf_renderer),
    file_storage: IFileStorage = Depends(get_file_storage),
) -> MovePaidBillDocumentUseCase:
    """Inyección de dependencias para mover documento de factura pagada en NAS."""
    return MovePaidBillDocumentUseCase(
        bill_repository,
        document_repository,
        apartment_repository,
        pdf_renderer,
        file_storage,
        settings.NAS_BASE_PATH,
    )


def get_retry_bill_document_sync_use_case(
    bill_repository: IBillRepository = Depends(get_bill_repository),
    document_repository: IBillDocumentRepository = Depends(get_bill_document_repository),
    apartment_repository: IApartmentRepository = Depends(get_apartment_repository),
    pdf_renderer: IBillPdfRenderer = Depends(get_bill_pdf_renderer),
    file_storage: IFileStorage = Depends(get_file_storage),
) -> RetryBillDocumentSyncUseCase:
    """Inyección de dependencias para reintentar sincronizaciones documentales con NAS."""
    return RetryBillDocumentSyncUseCase(
        bill_repository,
        document_repository,
        apartment_repository,
        pdf_renderer,
        file_storage,
        settings.NAS_BASE_PATH,
    )
