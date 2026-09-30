"""Helpers for reading XLSX files safely (read-only, no macros, XML parsed through defusedxml)."""

from __future__ import annotations

import re
import warnings
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import openpyxl

from gdmty.util import ParseError, norm_label, parse_date

# openpyxl warns when it cannot parse a sheet's print header/footer; irrelevant for data.
warnings.filterwarnings("ignore", message="Cannot parse header or footer", module="openpyxl")
warnings.filterwarnings("ignore", message="Workbook contains no default style", module="openpyxl")

# Measure columns and their header variants (compared after norm_label).
MEASURES: dict[str, tuple[str, ...]] = {
    "aprobado": ("aprobado", "presupuesto aprobado", "estimado"),
    "ampliaciones": (
        "ampliaciones/ (reducciones)",
        "ampliaciones/(reducciones)",
        "ampliacion / (reducciones)",
        "ampliaciones y reducciones",
        "ampliaciones / (reducciones)",
        "ampliaciones",
    ),
    "modificado": ("modificado",),
    "devengado": ("devengado",),
    "pagado": ("pagado", "recaudado"),
    "subejercicio": ("subejercicio", "diferencia"),
}

_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def open_workbook(path: Path) -> openpyxl.Workbook:
    return openpyxl.load_workbook(path, read_only=True, data_only=True, keep_vba=False, keep_links=False)


def rows(ws: object) -> Iterator[tuple[object, ...]]:
    for r in ws.iter_rows(values_only=True):  # type: ignore[attr-defined]
        yield tuple(r)


def measure_of(header: object) -> str | None:
    h = norm_label(header).replace("\n", " ")
    h = re.sub(r"\s+", " ", h)
    for measure, variants in MEASURES.items():
        if h in variants:
            return measure
    return None


def find_measure_columns(
    all_rows: list[tuple[object, ...]], *, required: tuple[str, ...]
) -> tuple[int, dict]:
    """Find the header row with 'Aprobado'/'Estimado' and return (index, {measure: column}).

    'Subejercicio' sometimes sits one row above the other headers; it is searched in that row too.
    """
    for i, row in enumerate(all_rows):
        cols = {m: j for j, c in enumerate(row) if (m := measure_of(c))}
        if "aprobado" in cols and "modificado" in cols:
            if i > 0:
                for j, c in enumerate(all_rows[i - 1]):
                    m = measure_of(c)
                    if m and m not in cols:
                        cols[m] = j
            missing = [m for m in required if m not in cols]
            if missing:
                raise ParseError(f"faltan columnas {missing} en el encabezado (fila {i + 1})")
            return i, cols
    raise ParseError("no se encontró la fila de encabezado con 'Aprobado' y 'Modificado'")


def period_end_from_title(all_rows: list[tuple[object, ...]]) -> date:
    """Read the cut-off date from titles such as 'Del 1° de enero al 30 de junio de 2026'."""
    for row in all_rows[:12]:
        for c in row:
            if not isinstance(c, str):
                continue
            m = re.search(
                r"al\s+(\d{1,2})\s+(?:de\s+)?([a-záéíóú]+)\s+(?:de\s+|del\s+)?(\d{4})", norm_label(c)
            )
            if m and m.group(2) in _MONTHS:
                return date(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
    raise ParseError("no se encontró la fecha de corte en el título")


def first_text(row: tuple[object, ...], before: int) -> str | None:
    """First non-empty text cell to the left of column `before` (the row label)."""
    for c in row[:before]:
        if isinstance(c, str) and c.strip():
            return c
    return None


__all__ = [
    "find_measure_columns",
    "first_text",
    "open_workbook",
    "parse_date",
    "period_end_from_title",
    "rows",
]
