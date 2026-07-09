"""
Unit tests — construcción del contexto de la plantilla del recibo (etiquetas del PDF).

Garantiza que "los datos salen correctos" en el PDF, espejo de bill-receipt.component.ts.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from application.bills.bill_pdf_renderer_interface import BillPdfData, PaidConfirmation
from infrastructure.documents.receipt_context import build_receipt_context

pytestmark = pytest.mark.unit

_LOGO = "data:image/png;base64,QUJD"


def _data(**overrides) -> BillPdfData:
    defaults: dict = {
        "bill_id": 1,
        "emission_date": date(2026, 7, 8),
        "cleaning_date": date(2026, 7, 8),
        "apartment_id": "R180",
        "address": "Calle Mayor 12, 3ºB",
        "cleaning_type_name": "Limpieza check-out",
        "clean_hours": Decimal("2.50"),
        "hourly_rate": Decimal("15.00"),
        "cost": Decimal("37.50"),
        "paid": False,
        "paid_at": None,
    }
    return BillPdfData(**{**defaults, **overrides})


def test_labels_created_state() -> None:
    ctx = build_receipt_context(_data(), _LOGO)

    assert ctx["logo_uri"] == _LOGO
    assert ctx["emission_label"] == "08/07/2026"
    assert ctx["week_label"] == "del 6 al 12"
    assert ctx["cleaning_date_label"] == "08/07/2026"
    assert ctx["hours_label"] == "2,5 horas"
    assert ctx["hourly_rate_label"] == "15"
    assert ctx["cost_label"] == "37,50"
    assert ctx["cost_words"] == "treinta y siete euros con cincuenta céntimos"
    assert ctx["paid"] is False
    assert ctx["paid_at_label"] == ""
    assert ctx["paid_confirmations"] == []


def test_labels_paid_state() -> None:
    ctx = build_receipt_context(
        _data(
            paid=True,
            paid_at=date(2026, 7, 9),
            paid_confirmations=(
                PaidConfirmation("María López", datetime(2026, 7, 9, 10, 15)),
                PaidConfirmation("Ana García", datetime(2026, 7, 9, 12, 40)),
            ),
        ),
        _LOGO,
    )

    assert ctx["paid"] is True
    assert ctx["paid_at_label"] == "09/07/2026"
    assert ctx["paid_confirmations"] == [
        "Pago confirmado por María López el día 09/07/2026 a las 10:15",
        "Pago confirmado por Ana García el día 09/07/2026 a las 12:40",
    ]


def test_hours_singular() -> None:
    ctx = build_receipt_context(_data(clean_hours=Decimal("1.00")), _LOGO)
    assert ctx["hours_label"] == "1 hora"


def test_rate_without_trailing_zeros() -> None:
    ctx = build_receipt_context(_data(hourly_rate=Decimal("12.50")), _LOGO)
    assert ctx["hourly_rate_label"] == "12,5"


def test_rate_none_hides_label() -> None:
    ctx = build_receipt_context(_data(hourly_rate=None), _LOGO)
    assert ctx["hourly_rate_label"] == ""


def test_week_label_crosses_month() -> None:
    # 2026-07-01 es miércoles; su semana natural va del lunes 29/6 al domingo 5/7.
    ctx = build_receipt_context(_data(cleaning_date=date(2026, 7, 1)), _LOGO)
    assert ctx["week_label"] == "del 29/6 al 5/7"
