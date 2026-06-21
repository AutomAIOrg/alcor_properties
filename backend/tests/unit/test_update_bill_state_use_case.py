"""
Unit tests — caso de uso de cambio de estado de facturas.
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from application.bills.commands import UpdateBillStateUseCase
from domain.bills.repository import IBillRepository
from domain.exceptions import BillNotFound, DomainValidationError
from tests.helpers import make_bill

pytestmark = pytest.mark.unit


def _use_case(bills: MagicMock) -> UpdateBillStateUseCase:
    return UpdateBillStateUseCase(bills)


def _bills_with(bill) -> MagicMock:
    bills = MagicMock(spec=IBillRepository)
    bills.get_by_id.return_value = bill
    bills.update.side_effect = lambda updated: updated
    return bills


def test_created_to_paid_sets_payment_date_today():
    bills = _bills_with(make_bill(bill_id=1, state="Creada"))

    result = _use_case(bills).execute(1, "Pagada")

    assert result.state == "Pagada"
    assert result.paid_at == date.today()


def test_created_to_paid_uses_explicit_payment_date():
    bills = _bills_with(make_bill(bill_id=1, state="Creada"))

    result = _use_case(bills).execute(1, "Pagada", paid_at=date(2026, 5, 20))

    assert result.paid_at == date(2026, 5, 20)


def test_created_to_cancelled_leaves_paid_at_empty():
    bills = _bills_with(make_bill(bill_id=1, state="Creada"))

    result = _use_case(bills).execute(1, "Cancelada")

    assert result.state == "Cancelada"
    assert result.paid_at is None


def test_paid_to_created_clears_payment_date():
    bills = _bills_with(make_bill(bill_id=1, state="Pagada", paid_at=date(2026, 5, 20)))

    result = _use_case(bills).execute(1, "Creada")

    assert result.state == "Creada"
    assert result.paid_at is None


def test_cancelled_to_created_is_allowed():
    bills = _bills_with(make_bill(bill_id=1, state="Cancelada"))

    result = _use_case(bills).execute(1, "Creada")

    assert result.state == "Creada"


def test_invalid_transition_raises_validation_error():
    bills = _bills_with(make_bill(bill_id=1, state="Pagada"))

    with pytest.raises(DomainValidationError):
        _use_case(bills).execute(1, "Cancelada")

    bills.update.assert_not_called()


def test_transition_to_pending_is_rejected():
    bills = _bills_with(make_bill(bill_id=1, state="Creada"))

    with pytest.raises(DomainValidationError):
        _use_case(bills).execute(1, "Pendiente")

    bills.update.assert_not_called()


def test_missing_bill_raises_not_found():
    bills = MagicMock(spec=IBillRepository)
    bills.get_by_id.side_effect = BillNotFound(99)

    with pytest.raises(BillNotFound):
        _use_case(bills).execute(99, "Pagada")

    bills.update.assert_not_called()
