"""
Configuración de ajustes para la aplicación backend.
"""

import os
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> str | None:
    if os.getenv("ALCOR_IGNORE_ENV_FILE") == "1":
        return None
    return str(Path(__file__).parent / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file(),
        case_sensitive=True,
        extra="allow",
    )

    # Aplicación
    APP_NAME: str = "Property Management System API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Base de datos — claves principales (DB_*)
    DB_HOST: str | None = None
    DB_USER: str | None = None
    DB_PASS: str | None = None
    DB_NAME: str | None = None
    DB_PORT: int = 3306

    # Alias de compatibilidad (MYSQL_*) — los DB_* tienen prioridad si ambos están definidos
    MYSQL_HOST: str | None = None
    MYSQL_USER: str | None = None
    MYSQL_PASSWORD: str | None = None
    MYSQL_DATABASE: str | None = None
    MYSQL_PORT: str | None = None

    # Cupo eléctrico — IDs de reservas separados por comas
    ELECTRIC: str = ""

    # API
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = ["*"]

    # Autenticación / JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 1

    # URL pública del frontend, usada para construir el enlace de restablecimiento de contraseña.
    FRONTEND_URL: str = "http://localhost:4200"

    # Email (SMTP) — usado para enviar el enlace de restablecimiento de contraseña.
    # Si SMTP_HOST está vacío, el sistema cae a un emisor de consola (solo desarrollo).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True

    # Contraseña por defecto para nuevos usuarios
    DEFAULT_PASSWORD: str = Field(...)

    # Generación del PDF de factura.
    # BILL_PDF_CHROMIUM_PATH: ruta al binario de Chromium/Chrome usado para el render
    #   (subprocess --print-to-pdf). Vacío = autodetección en el PATH.
    # BILL_PDF_OUTPUT_DIR: carpeta donde se guardan los PDF generados. Vacío = la carpeta
    #   backend/bill_templates (temporal; se cambiará por el NAS más adelante).
    BILL_PDF_CHROMIUM_PATH: str = ""
    BILL_PDF_OUTPUT_DIR: str = ""

    @model_validator(mode="after")
    def _resolve_db_aliases(self) -> "Settings":
        """Utiliza variables MYSQL_* cuando las variables canónicas DB_* no están presentes."""
        if self.MYSQL_HOST and not self.DB_HOST:
            self.DB_HOST = self.MYSQL_HOST
        if self.MYSQL_USER and not self.DB_USER:
            self.DB_USER = self.MYSQL_USER
        if self.MYSQL_PASSWORD and not self.DB_PASS:
            self.DB_PASS = self.MYSQL_PASSWORD
        if self.MYSQL_DATABASE and not self.DB_NAME:
            self.DB_NAME = self.MYSQL_DATABASE
        if self.MYSQL_PORT and self.DB_PORT == 3306:
            self.DB_PORT = int(self.MYSQL_PORT)
        return self


settings = Settings()  # type: ignore[call-arg]
