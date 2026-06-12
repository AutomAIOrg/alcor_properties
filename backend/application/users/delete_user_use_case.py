from application.shared.user_repository_interface import IUserRepository
from domain.auth.user_entity import User
from domain.exceptions import IntegrityError, UserNotFound


class DeleteUserUseCase:
    """Caso de uso para eliminar un usuario."""

    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    def execute(self, user_id: int, current_user: User):
        user = self.user_repository.get_by_id(user_id)

        # Verificar si el usuario existe
        if user is None:
            raise UserNotFound()

        # Verificar si el usuario es el mismo que el usuario actual
        if user.id == current_user.id:
            raise IntegrityError("No puedes eliminar tu propio usuario.")

        self.user_repository.delete_user(user_id)
