"""
Interfaz abstracta para almacenamiento de archivos en sistemas externos (NAS).
"""

from abc import ABC, abstractmethod


class IFileStorage(ABC):
    """Puerto para subir archivos a un almacenamiento remoto."""

    @abstractmethod
    def upload_bytes(
        self,
        remote_folder: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Sube contenido binario a una carpeta remota.

        Args:
            remote_folder: Ruta de carpeta destino en el almacenamiento remoto.
            filename: Nombre del archivo a crear.
            content: Contenido binario del archivo.
            content_type: Tipo MIME del archivo.

        Returns:
            Ruta completa del archivo en el almacenamiento remoto.

        Raises:
            FileStorageError: si la subida falla.
        """
        pass

    @abstractmethod
    def delete(self, remote_path: str) -> None:
        """
        Elimina un archivo del almacenamiento remoto.

        Args:
            remote_path: Ruta completa del archivo en el almacenamiento remoto.

        Raises:
            FileStorageError: si el borrado falla.
        """
        pass
