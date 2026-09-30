from datetime import date

import pytest

from gdmty.catalogos import capitulo_por_clave, capitulo_por_nombre
from gdmty.util import ParseError, parse_date, quarter_of, round_money, to_amount


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (1234.5, 1234.5),
        (7, 7.0),
        ("1,234.50", 1234.5),
        ("-1752526.63", -1752526.63),
        ("(12.00)", -12.0),
        ("$ 1,000", 1000.0),
        (-1.19e-07, 0.0),  # float artefact -> cents
    ],
)
def test_to_amount_accepts_numbers(raw: object, expected: float) -> None:
    assert to_amount(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "-", "N/A", "abc", "12a", True])
def test_to_amount_never_invents_values(raw: object) -> None:
    with pytest.raises(ParseError):
        to_amount(raw)


def test_round_money_no_negative_zero() -> None:
    assert str(round_money(-0.001)) == "0.0"


def test_dates_and_quarters() -> None:
    assert parse_date("30/06/2026") == date(2026, 6, 30)
    assert quarter_of(date(2026, 6, 30)) == "2026T2"
    with pytest.raises(ParseError):
        quarter_of(date(2026, 5, 31))


def test_capitulos() -> None:
    assert capitulo_por_clave("1100") == "1000"
    assert capitulo_por_clave(6000) == "6000"
    assert capitulo_por_nombre(" Servicios Personales   ") == "1000"
    assert capitulo_por_nombre("INVERSION PÚBLICA") == "6000"
    assert capitulo_por_nombre("Remuneraciones al personal") is None
    with pytest.raises(ValueError):
        capitulo_por_clave("0")
