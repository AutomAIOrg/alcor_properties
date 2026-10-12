"""
Implementación de IUserRepository usando SQLAlchemy.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from application.shared.user_repository_interface import IUserRepository
from domain.auth.user_entity import NewUser, Role, User
from domain.exceptions import InvalidToken, UserDatabaseError, UserNotFound
from infrastructure.models.auth_session import AuthSessionORM
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
            must_change_password=user.must_change_password,
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
        orm.must_change_password = user.must_change_password

        try:
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            logger.exception(f"Error al actualizar el usuario: {e}")
            raise UserDatabaseError("Error al actualizar el usuario.") from e

    def set_password_reset_jti(self, user_id: int, jti: str) -> None:
        """Registra el jti del token de restablecimiento activo para el usuario."""
        orm = self._db.query(UserORM).filter(UserORM.id == user_id).first()
        if orm is None:
            raise UserNotFound()
        orm.password_reset_jti = jti
        try:
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            logger.exception(f"Error al registrar el token de restablecimiento: {e}")
            raise UserDatabaseError("Error al registrar el token de restablecimiento.") from e

    def consume_password_reset_jti(self, user_id: int, jti: str) -> bool:
        """Consume el jti de forma atómica. Devuelve True si era válido y no estaba usado."""
        rows = (
            self._db.query(UserORM)
            .filter(UserORM.id == user_id, UserORM.password_reset_jti == jti)
            .update({UserORM.password_reset_jti: None}, synchronize_session=False)
        )
        return rows == 1

    def bump_token_version(self, user_id: int) -> None:
        try:
            result = self._db.execute(
                update(UserORM)
                .where(UserORM.id == user_id)
                .values(token_version=UserORM.token_version + 1)
            )
            if result.rowcount != 1:
                raise UserNotFound()
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def _lock_user(self, user_id: int, token_version: int):
        user = self._db.scalar(
            select(UserORM)
            .where(UserORM.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None or user.token_version != token_version:
            raise InvalidToken("Token de sesión revocado")
        return user

    def create_auth_session(self, user_id, session_id, jti, expires_at, token_version):
        try:
            self._lock_user(user_id, token_version)
            self._db.add(
                AuthSessionORM(
                    id=session_id,
                    user_id=user_id,
                    refresh_jti=jti,
                    expires_at=expires_at.replace(tzinfo=None),
                    revoked=False,
                )
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def rotate_auth_session(
        self, user_id, session_id, expected_jti, new_jti, expires_at, token_version
    ):
        try:
            self._lock_user(user_id, token_version)
            session = self._db.scalar(
                select(AuthSessionORM)
                .where(AuthSessionORM.id == session_id, AuthSessionORM.user_id == user_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                session is None
                or session.revoked
                or session.expires_at <= datetime.now(UTC).replace(tzinfo=None)
            ):
                self._db.rollback()
                return False
            if session.refresh_jti != expected_jti:
                session.revoked = True
                self._db.commit()
                return False
            session.refresh_jti = new_jti
            session.expires_at = expires_at.replace(tzinfo=None)
            self._db.commit()
            return True
        except Exception:
            self._db.rollback()
            raise

    def is_auth_session_active(self, user_id, session_id):
        return (
            self._db.scalar(
                select(AuthSessionORM.id).where(
                    AuthSessionORM.id == session_id,
                    AuthSessionORM.user_id == user_id,
                    AuthSessionORM.revoked.is_(False),
                    AuthSessionORM.expires_at > datetime.now(UTC).replace(tzinfo=None),
                )
            )
            is not None
        )

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
            token_version=orm.token_version,
            must_change_password=orm.must_change_password,
        )
