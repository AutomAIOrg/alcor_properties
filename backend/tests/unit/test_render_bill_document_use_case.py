"""
Unit tests — RenderBillDocumentUseCase.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from application.bills.render_bill_document_use_case import RenderBillDocumentUseCase
from domain.apartments.repository import IApartmentRepository
from domain.bills.repository import IBillRepository
from domain.exceptions import BillDocumentRenderError, BillNotFoundError, DomainValidationError
from tests.helpers import make_apartment, make_bill

pytestmark = pytest.mark.unit

_PDF_BYTES = b"%PDF-1.4 stub"


def _use_case(
    bills: MagicMock | None = None,
    apartments: MagicMock | None = None,
    renderer: MagicMock | None = None,
) -> RenderBillDocumentUseCase:
    if bills is None:
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(bill_id=1)
    if apartments is None:
        apartments = MagicMock(spec=IApartmentRepository)
        apartments.get_by_apartment_id.return_value = make_apartment(address="Calle Glaucio 15")
    if renderer is None:
        renderer = MagicMock()
        renderer.render.return_value = _PDF_BYTES

    return RenderBillDocumentUseCase(bills, apartments, renderer)


class TestRenderBillDocumentUseCase:
    def test_returns_rendered_pdf_with_nas_filename_convention(self):
        result = _use_case().execute(1)

        assert result.content == _PDF_BYTES
        assert result.filename == "TEST-001 LIMPIEZA 01.06.2026.pdf"

    def test_renders_with_bill_and_apartment_data(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(
            bill_id=7, apartment_id="A-42", cost=Decimal("45.00")
        )
        renderer = MagicMock()
        renderer.render.return_value = _PDF_BYTES

        _use_case(bills, None, renderer).execute(7)

        data = renderer.render.call_args.args[0]
        assert data.bill_id == 7
        assert data.apartment_id == "A-42"
        assert data.cost == Decimal("45.00")
        assert data.address == "Calle Glaucio 15"

    def test_paid_bill_renders_its_paid_version(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(
            bill_id=1, state="Pagada", paid_at=date(2026, 6, 5)
        )
        renderer = MagicMock()
        renderer.render.return_value = _PDF_BYTES

        _use_case(bills, None, renderer).execute(1)

        data = renderer.render.call_args.args[0]
        assert data.paid is True
        assert data.paid_at == date(2026, 6, 5)

    def test_does_not_touch_the_nas(self):
        """La descarga es una lectura pura: sin subidas ni estado documental que mantener."""
        use_case = _use_case()

        # El caso de uso ni siquiera recibe almacenamiento ni repositorio de documentos.
        assert not hasattr(use_case, "_file_storage")
        assert not hasattr(use_case, "_document_repository")

    def test_unknown_bill_propagates_not_found(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.side_effect = BillNotFoundError(99)

        with pytest.raises(BillNotFoundError):
            _use_case(bills).execute(99)

    def test_incomplete_bill_is_rejected_before_rendering(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(bill_id=1, cleaning_date=None)
        renderer = MagicMock()

        with pytest.raises(DomainValidationError):
            _use_case(bills, None, renderer).execute(1)

        renderer.render.assert_not_called()

    def test_render_failure_propagates(self):
        renderer = MagicMock()
        renderer.render.side_effect = BillDocumentRenderError("Chromium no disponible")

        with pytest.raises(BillDocumentRenderError):
            _use_case(None, None, renderer).execute(1)
