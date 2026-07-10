"""
Adaptador de almacenamiento de archivos para NAS Synology vía SSH (SCP).

Pensado para acceso por red privada (p. ej. Tailscale). Usa SCP en lugar del
subsistema SFTP, que en Synology suele estar deshabilitado y provoca
«Channel closed» al llamar a open_sftp().
"""

import logging
import os
import shlex
import shutil
import tempfile

import paramiko
from scp import SCPClient

from application.shared.file_storage_interface import IFileStorage
from domain.exceptions import FileStorageError

logger = logging.getLogger(__name__)


class SynologyFileStorage(IFileStorage):
    """Sube archivos al NAS Synology usando SCP sobre SSH."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        *,
        volume_prefix: str = "/volume1",
        connect_timeout: int = 30,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._volume_prefix = volume_prefix.rstrip("/")
        self._connect_timeout = connect_timeout

    def upload_bytes(
        self,
        remote_folder: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        folder = self._to_ssh_path(remote_folder)
        remote_path = f"{folder}/{filename}"

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, filename)
        try:
            with open(tmp_path, "wb") as tmp:
                tmp.write(content)

            logger.info("Conectando al NAS por SSH/SCP (%s:%s)...", self._host, self._port)
            ssh.connect(
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                timeout=self._connect_timeout,
                allow_agent=False,
                look_for_keys=False,
            )
            self._ensure_folder(ssh, folder)

            with SCPClient(ssh.get_transport()) as scp:
                scp.put(tmp_path, remote_path=remote_path)

            logger.info("Archivo subido al NAS: %s (%s)", remote_path, content_type)
            return remote_path

        except FileStorageError:
            raise
        except Exception as exc:
            logger.exception("Error al subir archivo al NAS por SCP en %s", remote_path)
            raise FileStorageError("No se pudo almacenar el archivo en el NAS.") from exc
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            ssh.close()

    def delete(self, remote_path: str) -> None:
        path = self._to_ssh_path(remote_path)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            logger.info("Conectando al NAS por SSH para borrar %s...", path)
            ssh.connect(
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                timeout=self._connect_timeout,
                allow_agent=False,
                look_for_keys=False,
            )
            command = f"rm -f {shlex.quote(path)}"
            _, stdout, stderr = ssh.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                error = stderr.read().decode().strip()
                raise FileStorageError(
                    f"No se pudo eliminar el archivo en el NAS: {path}. {error}".strip()
                )
            logger.info("Archivo eliminado del NAS: %s", path)
        except FileStorageError:
            raise
        except Exception as exc:
            logger.exception("Error al eliminar archivo del NAS en %s", path)
            raise FileStorageError("No se pudo eliminar el archivo en el NAS.") from exc
        finally:
            ssh.close()

    def _to_ssh_path(self, path: str) -> str:
        """Convierte rutas estilo FileStation a ruta absoluta SSH (/volume1/...)."""
        normalized = self._normalize_path(path)
        if normalized.startswith("/volume"):
            return normalized
        return f"{self._volume_prefix}{normalized}"

    @staticmethod
    def _ensure_folder(ssh: paramiko.SSHClient, folder: str) -> None:
        command = f"mkdir -p {shlex.quote(folder)}"
        _, stdout, stderr = ssh.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            error = stderr.read().decode().strip()
            raise FileStorageError(
                f"No se pudo crear la carpeta en el NAS: {folder}. {error}".strip()
            )

    @staticmethod
    def _normalize_path(path: str) -> str:
        normalized = path.replace("\\", "/").strip()
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        return normalized.rstrip("/")
