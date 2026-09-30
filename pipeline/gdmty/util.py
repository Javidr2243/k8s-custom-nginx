"""Strict conversions: a value that is not clearly a number is an error, never a zero."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_NUM_RE = re.compile(r"^\(?-?\$?\s*[\d,]*\.?\d+\)?$")


class ParseError(ValueError):
    """The file does not have the expected structure or contains invalid values."""


def to_amount(value: object, *, where: str = "") -> float:
    """Convert a cell into pesos with 2 decimals. Accepts numbers or numeric text ("1,234.50", "(12)")."""
    return round_money(to_decimal(value, where=where))


def to_number(value: object, *, where: str = "") -> float:
    """Like to_amount but without rounding (rates, percentages, amounts in millions)."""
    return float(to_decimal(value, where=where))


def to_decimal(value: object, *, where: str = "") -> Decimal:
    """Strict conversion to Decimal; anything that is not clearly a number raises ParseError."""
    if isinstance(value, bool):
        raise ParseError(f"valor booleano inesperado {where}")
    if isinstance(value, int | float):
        return Decimal(str(value))
    if isinstance(value, str):
        s = value.strip().replace(" ", "")
        if s in ("", "-"):
            raise ParseError(f"monto vacío {where}")
        if not _NUM_RE.match(s.replace(" ", "")):
            raise ParseError(f"monto no numérico {value!r} {where}")
        negative = s.startswith("(") and s.endswith(")")
        s = s.strip("()").replace("$", "").replace(",", "").replace(" ", "")
        try:
            d = Decimal(s)
        except InvalidOperation as exc:
            raise ParseError(f"monto no numérico {value!r} {where}") from exc
        return -d if negative else d
    raise ParseError(f"tipo de valor inesperado {type(value).__name__} {where}")


def is_number(value: object) -> bool:
    try:
        to_amount(value)
    except ParseError:
        return False
    return True


def round_money(value: float | int | Decimal) -> float:
    """Round to cents (removes float artefacts such as 1.19e-07)."""
    d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(d) + 0.0  # + 0.0 turns -0.0 into 0.0


def norm_label(text: object) -> str:
    """Normalise a label for comparison: no accents, lowercase, collapsed spaces."""
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def clean_label(text: object) -> str:
    """Label for display: collapsed spaces, original accents and case kept."""
    return re.sub(r"\s+", " ", str(text or "")).strip()


def slugify(text: object) -> str:
    return re.sub(r"[^a-z0-9]+", "-", norm_label(text)).strip("-")


def parse_date(value: object) -> date:
    """Dates from SIPOT (dd/mm/yyyy), ISO, or datetime cells."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ParseError(f"fecha no reconocida: {value!r}")


def quarter_of(end: date) -> str:
    """Period id from its end date: 2026-06-30 -> '2026T2'."""
    if end.month not in (3, 6, 9, 12):
        raise ParseError(f"la fecha de corte {end} no es fin de trimestre")
    return f"{end.year}T{end.month // 3}"


def quarter_end(period: str) -> date:
    year, q = int(period[:4]), int(period[-1])
    month = q * 3
    day = 31 if month in (3, 12) else 30
    return date(year, month, day)
