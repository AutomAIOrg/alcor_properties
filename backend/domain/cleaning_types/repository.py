"""
Interfaz abstracta de repositorio para el dominio de Tipos de limpieza.
"""

from abc import ABC, abstractmethod

from domain.cleaning_types.entity import CleaningType


class ICleaningTypeRepository(ABC):
    """Puerto para las operaciones de persistencia de tipos de limpieza."""

    @abstractmethod
    def create(self, cleaning_type: CleaningType) -> CleaningType:
        """
        Persiste un nuevo tipo de limpieza y lo devuelve con el *cleaning_type_id* asignado.

        El *cleaning_type* recibido debe tener ``cleaning_type_id=None``.
        """
        pass

    @abstractmethod
    def get_by_id(self, cleaning_type_id: int) -> CleaningType | None:
        """Devuelve el tipo de limpieza identificado por *cleaning_type_id*, o None si no existe."""
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> CleaningType | None:
        """Devuelve el tipo de limpieza con ese *name*, o None si no existe."""
        pass

    @abstractmethod
    def update(self, cleaning_type: CleaningType) -> CleaningType:
        """
        Persiste los cambios de un tipo de limpieza existente.

        Excepciones:
            CleaningTypeNotFoundError: si no existe un tipo con *cleaning_type.cleaning_type_id*.
        """
        pass

    @abstractmethod
    def delete(self, cleaning_type_id: int) -> None:
        """
        Elimina el tipo de limpieza identificado por *cleaning_type_id*.

        Excepciones:
            CleaningTypeNotFoundError: si no existe un tipo con ese ID.
        """
        pass

    @abstractmethod
    def list(self, active_only: bool = False) -> list[CleaningType]:
        """
        Devuelve todos los tipos de limpieza.

        Si *active_only* es True, solo devuelve los que están activos.
        """
        pass
