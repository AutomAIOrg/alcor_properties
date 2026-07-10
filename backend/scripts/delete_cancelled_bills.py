"""Elimina de la base de datos las facturas en estado 'Cancelada'.

La cancelación de facturas se retiró del flujo (ahora se rectifica en su lugar), por lo
que las facturas canceladas que pudieran quedar de antes ya no tienen sentido. Este script
las elimina de forma permanente.

Uso:
    python scripts/delete_cancelled_bills.py            # dry-run: solo cuenta y lista
    python scripts/delete_cancelled_bills.py --apply    # elimina de verdad

Solo toca la base de datos; no borra archivos PDF del disco.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Se importan TODOS los modelos ORM para que el metadata resuelva las claves foráneas de
# 'bills' (a bookings, cleaning_types y Apartamentos) al hacer flush del DELETE.
import infrastructure.models.apartment  # noqa: E402, F401
import infrastructure.models.booking  # noqa: E402, F401
import infrastructure.models.cleaning_type  # noqa: E402, F401
import infrastructure.models.user  # noqa: E402, F401
from config import settings  # noqa: E402
from domain.bills.entity import BILL_STATE_CANCELLED  # noqa: E402
from infrastructure.database.session import SessionLocal  # noqa: E402
from infrastructure.models.bill import BillORM  # noqa: E402


def main(apply: bool) -> int:
    with SessionLocal() as session:
        cancelled = session.query(BillORM).filter(BillORM.state == BILL_STATE_CANCELLED).all()

        print(f"Base de datos: {settings.DB_NAME} @ {settings.DB_HOST}:{settings.DB_PORT}")
        print(f"Facturas canceladas encontradas: {len(cancelled)}")
        for bill in cancelled:
            print(
                f"  - #{bill.bill_id}  piso {bill.apartment_id}  "
                f"limpieza {bill.cleaning_date}  (reserva {bill.record_id})"
            )

        if not cancelled:
            print("No hay nada que eliminar.")
            return 0

        if not apply:
            print("\n[DRY-RUN] No se ha eliminado nada. Ejecuta con --apply para borrarlas.")
            return 0

        for bill in cancelled:
            session.delete(bill)
        session.commit()
        print(f"\nEliminadas {len(cancelled)} facturas canceladas.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(apply="--apply" in sys.argv))
