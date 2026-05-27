"""
Engine de SQLAlchemy y fábrica de sesiones.
"""

from collections.abc import Generator
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings


def _build_database_url() -> str:
    # quote_plus encodes special characters (e.g. '@' in passwords) for safe URL use
    password = quote_plus(settings.DB_PASS or "")
    return (
        f"mysql+pymysql://{settings.DB_USER}:{password}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )


engine = create_engine(
    _build_database_url(),
    pool_pre_ping=True,  # vuelve a comprobar la conexión antes de usarla (reemplaza la antigua lógica de ping)
    pool_recycle=3600,  # recicla conexiones tras 1 h para evitar el wait_timeout de MySQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session]:
    """Cede una sesión de base de datos y garantiza su cierre después de la solicitud."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
