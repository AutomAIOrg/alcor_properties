"""
Unit tests — importe en euros expresado en letra (port de amount-to-words.ts).
"""

from decimal import Decimal

import pytest

from infrastructure.documents.amount_to_words import amount_to_spanish_words

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("0"), "cero euros"),
        (Decimal("1"), "un euro"),
        (Decimal("21"), "veintiún euros"),
        (Decimal("30"), "treinta euros"),
        (Decimal("37.5"), "treinta y siete euros con cincuenta céntimos"),
        (Decimal("0.01"), "cero euros con un céntimo"),
        (Decimal("100"), "cien euros"),
        (Decimal("101"), "ciento un euros"),
        (Decimal("215.75"), "doscientos quince euros con setenta y cinco céntimos"),
        (Decimal("1000"), "mil euros"),
        (Decimal("2021"), "dos mil veintiún euros"),
    ],
)
def test_amount_to_spanish_words(amount: Decimal, expected: str) -> None:
    assert amount_to_spanish_words(amount) == expected


def test_trailing_zeros_do_not_change_words() -> None:
    # Decimal('37.50') y Decimal('37.5') representan el mismo importe.
    assert amount_to_spanish_words(Decimal("37.50")) == amount_to_spanish_words(Decimal("37.5"))
