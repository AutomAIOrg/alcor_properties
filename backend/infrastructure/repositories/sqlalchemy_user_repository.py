"""
Implementación de IUserRepository usando SQLAlchemy.
"""

import logging

from sqlalchemy.orm import Session

from application.shared.user_repository_interface import IUserRepository
from domain.auth.user_entity import NewUser, Role, User
from domain.exceptions import UserDatabaseError, UserNotFound
from infrastructure.models.user import UserORM

logger = logging.getLogger(__name__)


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
        """Obtiene un usuario por su username."""
        orm = self._db.query(UserORM).filter(UserORM.username == username).first()
        if orm is None:
            return None
        return self._to_entity(orm)

    def get_by_id(self, user_id: int) -> User | None:
        """Obtiene un usuario por su id."""
        orm = self._db.query(UserORM).filter(UserORM.id == user_id).first()
        if orm is None:
            return None
        return self._to_entity(orm)

    def get_by_email(self, email: str) -> User | None:
        """Obtiene un usuario por su email."""
        orm = self._db.query(UserORM).filter(UserORM.email == email).first()
        if orm is None:
            return None
        return self._to_entity(orm)

    def create_user(self, user: NewUser) -> User:
        """Crea un nuevo usuario."""
        orm = UserORM(
            username=user.username,
            password=user.password,
            name=user.name,
            lastname=user.lastname,
            email=user.email,
            role=user.role.value,
        )
        self._db.add(orm)
        try:
            self._db.commit()
            self._db.refresh(orm)
        except Exception as e:
            self._db.rollback()
            logger.exception(f"Error al crear el usuario: {e}")
            raise UserDatabaseError("Error al crear el usuario.") from e
        return self._to_entity(orm)

    def delete_user(self, user_id: int):
        """Elimina un usuario."""
        orm = self._db.query(UserORM).filter(UserORM.id == user_id).first()
        if orm is None:
            raise UserNotFound()
        self._db.delete(orm)
        try:
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            logger.exception(f"Error al eliminar el usuario: {e}")
            raise UserDatabaseError("Error al eliminar el usuario.") from e

    def get_all_users(self) -> list[User]:
        """Obtiene todos los usuarios."""
        orms = self._db.query(UserORM).all()
        return [self._to_entity(orm) for orm in orms]

    def update_user(self, user: User):
        """Actualiza un usuario."""
        orm = self._db.query(UserORM).filter(UserORM.id == user.id).first()
        if orm is None:
            raise UserNotFound()
        orm.username = user.username
        orm.password = user.password
        orm.name = user.name
        orm.lastname = user.lastname
        orm.email = user.email
        orm.role = user.role.value

        try:
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            logger.exception(f"Error al actualizar el usuario: {e}")
            raise UserDatabaseError("Error al actualizar el usuario.") from e

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
