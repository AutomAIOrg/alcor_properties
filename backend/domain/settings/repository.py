"""
Interfaz abstracta de repositorio para la configuración de la aplicación (clave-valor).
"""

from abc import ABC, abstractmethod


class ISettingsRepository(ABC):
    """Puerto para leer y escribir parámetros de configuración persistentes."""

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Devuelve el valor almacenado para *key*, o None si no existe."""
        pass

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Crea o actualiza el valor asociado a *key*."""
        pass
