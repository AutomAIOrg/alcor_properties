"""
Unit tests — caso de uso de generación y guardado del PDF de factura.

Con un renderer y un repositorio de apartamentos falsos: comprueba que resuelve la
dirección, construye los datos correctos y escribe el PDF en la carpeta indicada.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from application.bills.bill_pdf_renderer_interface import BillPdfData
from application.bills.generate_bill_document_use_case import GenerateBillDocumentUseCase
from domain.exceptions import DomainValidationError
from tests.helpers import make_apartment, make_bill

pytestmark = pytest.mark.unit


class _FakeRenderer:
    """Renderer falso: registra los datos recibidos y devuelve unos bytes de PDF."""

    def __init__(self) -> None:
        self.received: BillPdfData | None = None

    def render(self, data: BillPdfData) -> bytes:
        self.received = data
        return b"%PDF-1.4 fake-content"


class _FakeApartmentRepository:
    def __init__(self, apartment=None) -> None:
        self._apartment = apartment

    def get_by_apartment_id(self, apartment_id: str):
        return self._apartment


def test_generates_pdf_and_saves_to_output_dir(tmp_path: Path) -> None:
    renderer = _FakeRenderer()
    apartment = make_apartment(apartment_id="R180", address="Calle Glaucio 15")
    use_case = GenerateBillDocumentUseCase(_FakeApartmentRepository(apartment), renderer, tmp_path)
    bill = make_bill(
        bill_id=7,
        apartment_id="R180",
        cost=Decimal("37.50"),
        hourly_rate=Decimal("15.00"),
        cleaning_type_name="Limpieza check-out",
    )

    output_path = use_case.execute(bill)

    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF")
    assert output_path.parent == tmp_path
    # La dirección se resuelve desde el repositorio de apartamentos.
    assert renderer.received is not None
    assert renderer.received.address == "Calle Glaucio 15"
    assert renderer.received.paid is False


def test_paid_bill_marks_data_as_paid(tmp_path: Path) -> None:
    renderer = _FakeRenderer()
    use_case = GenerateBillDocumentUseCase(
        _FakeApartmentRepository(make_apartment()), renderer, tmp_path
    )
    bill = make_bill(bill_id=9, state="Pagada", paid_at=date(2026, 7, 9))

    use_case.execute(bill)

    assert renderer.received is not None
    assert renderer.received.paid is True
    assert renderer.received.paid_at == date(2026, 7, 9)


def test_missing_address_apartment_is_tolerated(tmp_path: Path) -> None:
    renderer = _FakeRenderer()
    use_case = GenerateBillDocumentUseCase(_FakeApartmentRepository(None), renderer, tmp_path)

    use_case.execute(make_bill(bill_id=3))

    assert renderer.received is not None
    assert renderer.received.address is None


def test_bill_without_cost_is_rejected(tmp_path: Path) -> None:
    renderer = _FakeRenderer()
    use_case = GenerateBillDocumentUseCase(
        _FakeApartmentRepository(make_apartment()), renderer, tmp_path
    )
    bill = make_bill(bill_id=1, cost=None)

    with pytest.raises(DomainValidationError):
        use_case.execute(bill)
