"""
Implementación de IUserRepository usando SQLAlchemy.
"""

from sqlalchemy.orm import Session

from application.auth.user_repository_interface import IUserRepository
from domain.auth.user_entity import Role, User
from infrastructure.models.user import UserORM


class SQLAlchemyUserRepository(IUserRepository):
    """
    Implementación del repositorio de usuarios respaldado por una sesión de SQLAlchemy
    (MySQL vía PyMySQL).
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Interfaz pública (contrato IUserRepository)                        #
    # ------------------------------------------------------------------ #

    def get_by_username(self, username: str) -> User | None:
        orm = self._db.query(UserORM).filter(UserORM.username == username).first()
        if orm is None:
            return None
        return self._to_entity(orm)

    def get_by_id(self, user_id: int) -> User | None:
        orm = self._db.query(UserORM).filter(UserORM.id == user_id).first()
        if orm is None:
            return None
        return self._to_entity(orm)

    # ------------------------------------------------------------------ #
    # Helpers privados de conversión                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_entity(orm: UserORM) -> User:
        """Convierte una fila UserORM en una entidad de dominio User."""
        return User(
            id=orm.id,
            username=orm.username,
            password=orm.password,
            name=orm.name,
            lastname=orm.lastname,
            email=orm.email,
            role=Role(orm.role),
        )
