from application.shared.user_repository_interface import IUserRepository
from domain.auth.user_entity import User


class GetAllUsersUseCase:
    """Caso de uso para obtener todos los usuarios."""

    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    def execute(self) -> list[User]:
        return self.user_repository.get_all_users()
