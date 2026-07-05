"""
Implementación de ISettingsRepository usando SQLAlchemy.
"""

from sqlalchemy.orm import Session

from domain.settings.repository import ISettingsRepository
from infrastructure.models.app_setting import AppSettingORM


class SQLAlchemySettingsRepository(ISettingsRepository):
    """Almacén de configuración clave-valor respaldado por una sesión de SQLAlchemy."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, key: str) -> str | None:
        orm = self._db.get(AppSettingORM, key)
        return orm.value if orm is not None else None

    def set(self, key: str, value: str) -> None:
        orm = self._db.get(AppSettingORM, key)
        if orm is None:
            self._db.add(AppSettingORM(key=key, value=value))
        else:
            orm.value = value
        self._db.commit()
