"""Monterrey: 'Estado Analítico del Ejercicio del Presupuesto de Egresos' and 'Estado Analítico de Ingresos'.

Published quarterly by the Tesorería Municipal as XLSX (cumulative from January to the cut-off date).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from gdmty.catalogos import CAPITULOS, capitulo_por_nombre
from gdmty.parsers.xlsx import find_measure_columns, first_text, open_workbook, period_end_from_title, rows
from gdmty.util import ParseError, clean_label, is_number, norm_label, to_amount

EGRESOS_MEASURES = ("aprobado", "ampliaciones", "modificado", "devengado", "pagado", "subejercicio")
INGRESOS_MEASURES = ("aprobado", "ampliaciones", "modificado", "devengado", "pagado")


@dataclass
class Linea:
    nombre: str
    montos: dict[str, float]
    clave: str | None = None
    conceptos: list[Linea] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)


@dataclass
class Estado:
    fecha_corte: date
    lineas: list[Linea]
    total: dict[str, float]


def _blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in ("", "-"))


def _montos(
    row: tuple[object, ...], cols: dict[str, int], measures: tuple[str, ...], where: str
) -> tuple[dict[str, float], list[str]]:
    """Read a line's amounts.

    Only one blank cell is tolerated, in 'aprobado' or 'ampliaciones', and only if the document's own
    identity (Modificado = Aprobado + Ampliaciones) proves it is 0. A note records this.
    Any other blank or non-numeric cell is an error.
    """
    raw = {m: (row[cols[m]] if cols[m] < len(row) else None) for m in measures}
    blanks = [m for m, v in raw.items() if _blank(v)]
    notas: list[str] = []
    if blanks:
        if len(blanks) > 1 or blanks[0] not in ("aprobado", "ampliaciones"):
            raise ParseError(f"celdas vacías {blanks} ({where})")
        other = "ampliaciones" if blanks[0] == "aprobado" else "aprobado"
        modificado = to_amount(raw["modificado"], where=f"(modificado, {where})")
        otro = to_amount(raw[other], where=f"({other}, {where})")
        if abs(modificado - otro) > 1:
            raise ParseError(f"celda vacía en '{blanks[0]}' y Modificado ≠ Aprobado + Ampliaciones ({where})")
        raw[blanks[0]] = 0
        notas.append(
            f"La celda '{blanks[0]}' aparece vacía en el documento; vale 0 porque "
            "Modificado = Aprobado + Ampliaciones/(Reducciones)."
        )
    return {m: to_amount(v, where=f"({m}, {where})") for m, v in raw.items()}, notas


def _data_rows(path: Path, measures: tuple[str, ...]):
    wb = open_workbook(path)
    try:
        all_rows = list(rows(wb.worksheets[0]))
    finally:
        wb.close()
    fecha = period_end_from_title(all_rows)
    header_idx, cols = find_measure_columns(all_rows, required=measures)
    first_col = min(cols.values())
    out = []
    for i, row in enumerate(all_rows[header_idx + 1 :], start=header_idx + 2):
        label = first_text(row, first_col)
        values = [row[cols[m]] if cols[m] < len(row) else None for m in measures]
        if label is None:
            continue
        if not any(is_number(v) for v in values):
            if out and norm_label(label).startswith("total"):
                raise ParseError(f"fila de total sin montos (fila {i})")
            continue
        out.append((i, label, row))
    return fecha, cols, out


def parse_egresos_administrativa(path: Path) -> Estado:
    """One line per dependencia, plus 'Total del Gasto'."""
    fecha, cols, data = _data_rows(path, EGRESOS_MEASURES)
    lineas: list[Linea] = []
    total = None
    for i, label, row in data:
        montos, notas = _montos(row, cols, EGRESOS_MEASURES, f"fila {i}")
        if norm_label(label).startswith("total"):
            total = montos
            break
        lineas.append(Linea(nombre=clean_label(label), montos=montos, notas=notas))
    if total is None:
        raise ParseError(f"{path.name}: no se encontró la fila 'Total del Gasto'")
    return Estado(fecha_corte=fecha, lineas=lineas, total=total)


def parse_egresos_objeto(path: Path) -> Estado:
    """Chapter lines (1000…9000), each with its concepts."""
    fecha, cols, data = _data_rows(path, EGRESOS_MEASURES)
    capitulos: list[Linea] = []
    total = None
    current: Linea | None = None
    for i, label, row in data:
        montos, notas = _montos(row, cols, EGRESOS_MEASURES, f"fila {i}")
        if norm_label(label).startswith("total"):
            total = montos
            break
        clave = capitulo_por_nombre(label)
        if clave:
            current = Linea(nombre=CAPITULOS[clave]["nombre"], clave=clave, montos=montos, notas=notas)
            capitulos.append(current)
        elif current is None:
            raise ParseError(
                f"{path.name}: concepto '{clean_label(label)}' antes de cualquier capítulo (fila {i})"
            )
        else:
            current.conceptos.append(Linea(nombre=clean_label(label), montos=montos, notas=notas))
    if total is None:
        raise ParseError(f"{path.name}: no se encontró la fila 'Total del Gasto'")
    return Estado(fecha_corte=fecha, lineas=capitulos, total=total)


def parse_ingresos(path: Path) -> Estado:
    """First table (by revenue category) up to its 'Total'. 'pagado' holds the amount collected."""
    fecha, cols, data = _data_rows(path, INGRESOS_MEASURES)
    lineas: list[Linea] = []
    total = None
    for i, label, row in data:
        montos, notas = _montos(row, cols, INGRESOS_MEASURES, f"fila {i}")
        if norm_label(label) == "total":
            total = montos
            break
        lineas.append(Linea(nombre=clean_label(label), montos=montos, notas=notas))
    if total is None:
        raise ParseError(f"{path.name}: no se encontró la fila 'Total'")
    return Estado(fecha_corte=fecha, lineas=lineas, total=total)
