from dataclasses import dataclass

from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from domain.auth.user_entity import NewUser, Role
from domain.exceptions import IntegrityError, UserAlreadyExists


@dataclass(frozen=True)
class CreateUserData:
    """Datos necesarios para crear un usuario desde la capa de aplicación."""

    username: str
    name: str
    role: Role
    initial_password: str
    lastname: str | None = None
    email: str | None = None


class CreateUserUseCase:
    """Caso de uso para crear un nuevo usuario."""

    def __init__(self, user_repository: IUserRepository, password_manager: IPasswordManager):
        self.user_repository = user_repository
        self.password_manager = password_manager

    def execute(self, user: CreateUserData):

        # Verificar si el usuario ya existe
        if self.user_repository.get_by_username(user.username) is not None:
            raise UserAlreadyExists(user.username)

        # Verificar si el email ya está en uso
        if user.email is not None:
            found_user = self.user_repository.get_by_email(user.email)
            if found_user is not None:
                raise IntegrityError(f"El email {user.email} ya está en uso")

        # Crear el usuario
        self.user_repository.create_user(
            NewUser(
                username=user.username,
                password=self.password_manager.hash(user.initial_password),
                name=user.name,
                lastname=user.lastname,
                email=user.email,
                role=user.role,
                # Nace con la contraseña inicial: debe fijar la suya al primer acceso.
                must_change_password=True,
            )
        )
