"""
Fixtures de pytest compartidas por todos los niveles de la test suite.

Niveles:
  - unit        → mock_repo
  - integration → sqlite_engine, sqlite_session, mock_use_cases, api_client
  - e2e         → sqlite_engine, e2e_client
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

import infrastructure.models.apartment  # noqa: F401 — registra ApartmentORM en Base.metadata
import infrastructure.models.booking  # noqa: F401 — registra BookingORM en Base.metadata
import infrastructure.models.user  # noqa: F401 — registra UserORM en Base.metadata
from domain.apartments.repository import IApartmentRepository
from domain.auth.token_payload_entity import TokenPayload
from domain.auth.user_entity import Role
from domain.bookings.repository import IBookingRepository
from infrastructure.database.base import Base
from infrastructure.models.user import UserORM

# ---------------------------------------------------------------------------
# Unit
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repo() -> MagicMock:
    """Repositorio mockeado con spec de IBookingRepository."""
    return MagicMock(spec=IBookingRepository)


@pytest.fixture
def mock_apartment_repo() -> MagicMock:
    """Repositorio mockeado con spec de IApartmentRepository."""
    return MagicMock(spec=IApartmentRepository)


@pytest.fixture
def mock_get_apartment_by_id_query() -> MagicMock:
    """GetApartmentByIdQuery mockeado para tests de API."""
    return MagicMock()

# ---------------------------------------------------------------------------
# Infraestructura SQLite compartida
# ---------------------------------------------------------------------------


@pytest.fixture
def sqlite_engine():
    """
    Motor SQLite en memoria con el schema de bookings creado.

    StaticPool garantiza que todas las conexiones (incluidas las que crea cada
    sesión de FastAPI en e2e) comparten la misma conexión subyacente, evitando
    que SQLite in-memory cree una BD vacía por cada nuevo checkout de conexión.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def sqlite_session(sqlite_engine):
    """Sesión SQLite lista para tests de repositorio."""
    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Integration — API con use cases mockeados
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_use_cases() -> MagicMock:
    """BookingUseCases completamente mockeado para tests de API."""
    return MagicMock()


@pytest.fixture
def api_client(mock_use_cases: MagicMock) -> TestClient:
    """
    TestClient de FastAPI con use cases inyectados como mock.

    - El mismo mock_use_cases que recibe el fixture está disponible en los tests
      que lo soliciten como parámetro (pytest reutiliza la misma instancia).
    """
    from api.dependencies import get_booking_use_cases, get_current_user
    from main import app

    now = datetime.now(UTC)
    admin_payload = TokenPayload(
        subject="1",
        expires_at=now + timedelta(minutes=30),
        issued_at=now,
        username="admin",
        role=Role.ADMIN,
    )

    app.dependency_overrides[get_booking_use_cases] = lambda: mock_use_cases
    app.dependency_overrides[get_current_user] = lambda: admin_payload

    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_booking_use_cases, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_search_apartments_query() -> MagicMock:
    """ApartmentUseCases completamente mockeado para tests de API."""
    return MagicMock()


@pytest.fixture
def apartment_api_client(
    mock_search_apartments_query: MagicMock,
    mock_get_apartment_by_id_query: MagicMock,
) -> TestClient:
    from api.dependencies import (
        get_apartment_by_id_query,
        get_current_user,
        get_search_apartments_query,
    )
    from main import app

    now = datetime.now(UTC)
    admin_payload = TokenPayload(
        subject="1",
        expires_at=now + timedelta(minutes=30),
        issued_at=now,
        username="admin",
        role=Role.ADMIN,
    )

    app.dependency_overrides[get_search_apartments_query] = lambda: mock_search_apartments_query
    app.dependency_overrides[get_apartment_by_id_query] = lambda: mock_get_apartment_by_id_query
    app.dependency_overrides[get_current_user] = lambda: admin_payload

    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_search_apartments_query, None)
        app.dependency_overrides.pop(get_apartment_by_id_query, None)
        app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# E2E — stack completo con SQLite
# ---------------------------------------------------------------------------


@pytest.fixture
def e2e_client(sqlite_engine):
    """
    TestClient sin mocks de use cases.

    Solo sobreescribe get_db para apuntar a SQLite en lugar de MySQL.
    El stack completo (use cases + repositorio) es real.
    """
    from infrastructure.database.session import get_db
    from main import app

    Session = sessionmaker(bind=sqlite_engine)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def admin_auth_headers(sqlite_session, e2e_client) -> dict[str, str]:
    """Crea un admin real en SQLite y devuelve headers Bearer obtenidos por login."""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = UserORM(
        username="admin",
        password=pwd_context.hash("admin-password"),
        name="Admin",
        lastname="User",
        email="admin@example.com",
        role=Role.ADMIN.value,
    )
    sqlite_session.add(user)
    sqlite_session.commit()

    response = e2e_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin-password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
