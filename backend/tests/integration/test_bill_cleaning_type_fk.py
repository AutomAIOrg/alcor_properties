"""
Integration test — comportamiento ON DELETE SET NULL de la FK bills → cleaning_types.

Al borrar un tipo de limpieza usado por una factura, la factura debe conservar el
nombre congelado (snapshot) y perder únicamente la referencia viva (cleaning_type_id
pasa a NULL), sin que el borrado falle por integridad referencial.

Usa un motor SQLite propio con las claves ajenas activadas (SQLite no las aplica por
defecto), de modo que el test refleja el comportamiento referencial de producción.
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from infrastructure.database.base import Base
from infrastructure.models.apartment import ApartmentORM
from infrastructure.models.bill import BillORM
from infrastructure.models.cleaning_type import CleaningTypeORM
from infrastructure.repositories.sqlalchemy_cleaning_type_repository import (
    SQLAlchemyCleaningTypeRepository,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def fk_session():
    """Sesión SQLite con enforcement de claves ajenas activado."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_deleting_cleaning_type_nulls_reference_and_keeps_snapshot(fk_session):
    fk_session.add(ApartmentORM(apartment_id="APT-1"))
    cleaning_type = CleaningTypeORM(name="Limpieza normal", hourly_rate=Decimal("15.00"))
    fk_session.add(cleaning_type)
    fk_session.flush()

    bill = BillORM(
        apartment_id="APT-1",
        clean_hours=Decimal("2.00"),
        cleaning_type_id=cleaning_type.cleaning_type_id,
        cleaning_type_name="Limpieza normal",
        state="Creada",
    )
    fk_session.add(bill)
    fk_session.commit()
    bill_id = bill.bill_id

    # Borrar el tipo no debe fallar aunque exista una factura que lo referencia.
    SQLAlchemyCleaningTypeRepository(fk_session).delete(cleaning_type.cleaning_type_id)

    refreshed = fk_session.get(BillORM, bill_id)
    fk_session.refresh(refreshed)
    assert refreshed.cleaning_type_id is None
    assert refreshed.cleaning_type_name == "Limpieza normal"
