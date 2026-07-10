"""
Conversión de un importe en euros a su expresión en letra (español).

Port de `frontend/src/app/shared/utils/amount-to-words.ts`: reproduce la línea
"el importe asciende a la cantidad de ..." del recibo. Debe mantenerse en sync con esa
utilidad del front (ver la nota de memoria del proyecto sobre el PDF de factura).
"""

import re
from decimal import ROUND_HALF_UP, Decimal

_UNITS = [
    "cero",
    "uno",
    "dos",
    "tres",
    "cuatro",
    "cinco",
    "seis",
    "siete",
    "ocho",
    "nueve",
    "diez",
    "once",
    "doce",
    "trece",
    "catorce",
    "quince",
    "dieciséis",
    "diecisiete",
    "dieciocho",
    "diecinueve",
    "veinte",
    "veintiuno",
    "veintidós",
    "veintitrés",
    "veinticuatro",
    "veinticinco",
    "veintiséis",
    "veintisiete",
    "veintiocho",
    "veintinueve",
]

_TENS = [
    "",
    "",
    "veinte",
    "treinta",
    "cuarenta",
    "cincuenta",
    "sesenta",
    "setenta",
    "ochenta",
    "noventa",
]

_HUNDREDS = [
    "",
    "ciento",
    "doscientos",
    "trescientos",
    "cuatrocientos",
    "quinientos",
    "seiscientos",
    "setecientos",
    "ochocientos",
    "novecientos",
]


def _apocopate(words: str) -> str:
    """Apócope de "uno" -> "un" y "veintiuno" -> "veintiún" ante sustantivo masculino o "mil"."""
    words = re.sub(r"veintiuno$", "veintiún", words)
    words = re.sub(r"(^|\s)uno$", r"\1un", words)
    return words


def _below_thousand(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "cien"

    hundreds = n // 100
    rest = n % 100
    parts: list[str] = []

    if hundreds > 0:
        parts.append(_HUNDREDS[hundreds])

    if rest > 0:
        if rest < 30:
            parts.append(_UNITS[rest])
        else:
            tens = rest // 10
            units = rest % 10
            parts.append(f"{_TENS[tens]} y {_UNITS[units]}" if units > 0 else _TENS[tens])

    return " ".join(parts)


def _integer_to_words(n: int) -> str:
    """Convierte un entero (0..999999) a letra, con la apócope de contar en masculino."""
    if n == 0:
        return "cero"

    thousands = n // 1000
    rest = n % 1000
    parts: list[str] = []

    if thousands == 1:
        parts.append("mil")
    elif thousands > 1:
        parts.append(f"{_apocopate(_below_thousand(thousands))} mil")

    if rest > 0:
        parts.append(_below_thousand(rest))

    return _apocopate(" ".join(parts))


def amount_to_spanish_words(amount: Decimal) -> str:
    """
    Expresa un importe en euros en letra, p. ej. 30 -> "treinta euros",
    37.5 -> "treinta y siete euros con cincuenta céntimos".
    """
    total_cents = int(
        (Decimal(amount).copy_abs() * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    euros = total_cents // 100
    cents = total_cents % 100

    euros_words = f"{_integer_to_words(euros)} {'euro' if euros == 1 else 'euros'}"

    if cents == 0:
        return euros_words

    cents_words = f"{_integer_to_words(cents)} {'céntimo' if cents == 1 else 'céntimos'}"
    return f"{euros_words} con {cents_words}"
