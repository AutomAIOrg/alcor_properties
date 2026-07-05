"""
Implementación de ICleaningTypeRepository usando SQLAlchemy.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.cleaning_types.entity import CleaningType
from domain.cleaning_types.repository import ICleaningTypeRepository
from domain.exceptions import CleaningTypeAlreadyExistsError, CleaningTypeNotFoundError
from infrastructure.models.cleaning_type import CleaningTypeORM


class SQLAlchemyCleaningTypeRepository(ICleaningTypeRepository):
    """Repositorio de tipos de limpieza respaldado por una sesión de SQLAlchemy."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, cleaning_type: CleaningType) -> CleaningType:
        orm = self._to_orm(cleaning_type)
        self._db.add(orm)
        try:
            self._db.commit()
        except IntegrityError as exc:
            # Salvaguarda ante una carrera con la restricción UNIQUE(Name): el caso de
            # uso ya comprueba la unicidad, pero dos altas concurrentes podrían colarse.
            self._db.rollback()
            raise CleaningTypeAlreadyExistsError(cleaning_type.name) from exc
        self._db.refresh(orm)
        return self._to_entity(orm)

    def get_by_id(self, cleaning_type_id: int) -> CleaningType | None:
        orm = self._db.get(CleaningTypeORM, cleaning_type_id)
        return self._to_entity(orm) if orm is not None else None

    def get_by_name(self, name: str) -> CleaningType | None:
        orm = self._db.query(CleaningTypeORM).filter(CleaningTypeORM.name == name.strip()).first()
        return self._to_entity(orm) if orm is not None else None

    def update(self, cleaning_type: CleaningType) -> CleaningType:
        assert cleaning_type.cleaning_type_id is not None
        orm = self._db.get(CleaningTypeORM, cleaning_type.cleaning_type_id)
        if orm is None:
            raise CleaningTypeNotFoundError(cleaning_type.cleaning_type_id)

        orm.name = cleaning_type.name
        orm.hourly_rate = cleaning_type.hourly_rate
        orm.active = cleaning_type.active

        try:
            self._db.commit()
        except IntegrityError as exc:
            # Salvaguarda ante una carrera con la restricción UNIQUE(Name).
            self._db.rollback()
            raise CleaningTypeAlreadyExistsError(cleaning_type.name) from exc
        self._db.refresh(orm)
        return self._to_entity(orm)

    def delete(self, cleaning_type_id: int) -> None:
        orm = self._db.get(CleaningTypeORM, cleaning_type_id)
        if orm is None:
            raise CleaningTypeNotFoundError(cleaning_type_id)
        self._db.delete(orm)
        self._db.commit()

    def list(self, active_only: bool = False) -> list[CleaningType]:
        query = self._db.query(CleaningTypeORM)
        if active_only:
            query = query.filter(CleaningTypeORM.active.is_(True))
        query = query.order_by(CleaningTypeORM.name.asc())
        return [self._to_entity(orm) for orm in query.all()]

    # ------------------------------------------------------------------ #
    # Helpers privados de conversión                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_entity(orm: CleaningTypeORM) -> CleaningType:
        return CleaningType(
            cleaning_type_id=orm.cleaning_type_id,
            name=orm.name,
            hourly_rate=orm.hourly_rate,
            active=orm.active,
        )

    @staticmethod
    def _to_orm(cleaning_type: CleaningType) -> CleaningTypeORM:
        return CleaningTypeORM(
            name=cleaning_type.name,
            hourly_rate=cleaning_type.hourly_rate,
            active=cleaning_type.active,
        )
