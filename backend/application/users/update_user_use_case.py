from application.shared.user_repository_interface import IUserRepository
from domain.auth.user_entity import Role, User
from domain.exceptions import IntegrityError, UserNotFound


class UpdateUserUseCase:
    """Caso de uso para actualizar un usuario."""

    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    def execute(self, user_update: User):
        user = self.user_repository.get_by_id(user_update.id)

        # Verificar si el usuario existe
        if user is None:
            raise UserNotFound()

        # Verificar si el username ya está en uso
        found_user = self.user_repository.get_by_username(user_update.username)
        if found_user is not None and found_user.id != user.id:
            raise IntegrityError(f"El username {user_update.username} ya está en uso")

        # Verificar si el email ya está en uso
        if user_update.email is not None:
            found_user = self.user_repository.get_by_email(user_update.email)
            if found_user is not None and found_user.id != user.id:
                raise IntegrityError(f"El email {user_update.email} ya está en uso")

        # Verifica si el usuario es administrador y no se está intentando actualizar su rol a un rol diferente
        if user.role == Role.ADMIN and user_update.role != Role.ADMIN:
            raise IntegrityError(
                "No se puede actualizar el rol de administrador a un rol diferente"
            )

        # Actualizar los datos del usuario
        user.username = user_update.username
        user.password = user.password
        user.name = user_update.name
        user.lastname = user_update.lastname
        user.email = user_update.email
        user.role = user_update.role

        # Guardar los datos actualizados del usuario
        self.user_repository.update_user(user)
