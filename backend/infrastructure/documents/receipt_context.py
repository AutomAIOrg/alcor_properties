"""
Construcción del contexto de la plantilla del recibo (bill_templates/bill_receipt.html).

Port del formateo de etiquetas de `bill-receipt.component.ts`: fecha, semana natural,
horas, tarifa, importe y su expresión en letra. Es la ÚNICA fuente de estas derivaciones
en backend y debe mantenerse en sync con el componente del front. Se mantiene como función
pura (sin Jinja ni Chromium) para poder testear el "los datos salen correctos" sin I/O.
"""

from datetime import date, timedelta
from decimal import Decimal

from application.bills.bill_pdf_renderer_interface import BillPdfData
from infrastructure.documents.amount_to_words import amount_to_spanish_words


def _format_date(value: date) -> str:
    """Fecha en formato DD/MM/YYYY (igual que el front)."""
    return value.strftime("%d/%m/%Y")


def _decimal_label(value: Decimal) -> str:
    """
    Número con coma decimal y sin ceros sobrantes, p. ej. Decimal('15.00') -> "15",
    Decimal('2.50') -> "2,5". Equivale a `String(x)` del front sobre un número JS.
    """
    # normalize() quita ceros finales pero puede producir notación exponencial
    # (Decimal('10.0').normalize() -> '1E+1'); format(..., 'f') la evita.
    text = format(value.normalize(), "f")
    return text.replace(".", ",")


def _hours_label(hours: Decimal) -> str:
    """Horas con coma decimal y singular/plural, p. ej. "2,5 horas" / "1 hora"."""
    return f"{_decimal_label(hours)} {'hora' if hours == 1 else 'horas'}"


def _week_label(cleaning_date: date) -> str:
    """
    Rango de la semana natural (lunes a domingo) que contiene la fecha de limpieza,
    p. ej. "del 6 al 12" (mismo mes) o "del 29/6 al 5/7" (a caballo entre meses).
    """
    monday = cleaning_date - timedelta(days=cleaning_date.weekday())
    sunday = monday + timedelta(days=6)

    if monday.month == sunday.month:
        return f"del {monday.day} al {sunday.day}"
    return f"del {monday.day}/{monday.month} al {sunday.day}/{sunday.month}"


def _cost_label(cost: Decimal) -> str:
    """Importe con dos decimales y coma, p. ej. "37,50" (equivale a `toFixed(2)`)."""
    return f"{cost:.2f}".replace(".", ",")


def build_receipt_context(data: BillPdfData, logo_uri: str) -> dict:
    """Transforma los datos de negocio en las variables de la plantilla del recibo."""
    rate_label = _decimal_label(data.hourly_rate) if data.hourly_rate is not None else ""

    return {
        "logo_uri": logo_uri,
        "emission_label": _format_date(data.emission_date),
        "week_label": _week_label(data.cleaning_date),
        "apartment_id": data.apartment_id,
        "address": data.address,
        "cleaning_date_label": _format_date(data.cleaning_date),
        "cleaning_type_name": data.cleaning_type_name,
        "hours_label": _hours_label(data.clean_hours),
        "hourly_rate_label": rate_label,
        "cost_label": _cost_label(data.cost),
        "cost_words": amount_to_spanish_words(data.cost),
        "paid": data.paid,
        "paid_at_label": _format_date(data.paid_at) if data.paid_at else "",
        "paid_confirmations": list(data.paid_confirmations),
    }
