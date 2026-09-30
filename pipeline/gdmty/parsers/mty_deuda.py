"""Monterrey: 'Deuda Pública (Total)', annual amortisation, interest and debt costs (Tesorería)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gdmty.parsers.xlsx import open_workbook, rows
from gdmty.util import ParseError, norm_label, to_amount


@dataclass
class DeudaAnual:
    anio: int
    amortizacion: float
    intereses: float
    gastos: float
    total: float


def parse(path: Path) -> list[DeudaAnual]:
    wb = open_workbook(path)
    try:
        all_rows = list(rows(wb.worksheets[0]))
    finally:
        wb.close()
    years_row = next(
        (
            r
            for r in all_rows
            if sum(1 for c in r if str(c or "").strip().isdigit() and len(str(c).strip()) == 4) >= 5
        ),
        None,
    )
    if years_row is None:
        raise ParseError(f"{path.name}: no se encontró la fila de años")
    cols = {j: int(str(c).strip()) for j, c in enumerate(years_row) if str(c or "").strip().isdigit()}
    series: dict[str, dict[int, float]] = {}
    for r in all_rows:
        label = next((norm_label(c) for c in r if isinstance(c, str) and c.strip()), "")
        key = {
            "amortizacion de la deuda": "amortizacion",
            "intereses de la deuda": "intereses",
            "gastos de la deuda": "gastos",
            "total": "total",
        }.get(label)
        if key and key not in series:
            series[key] = {y: to_amount(r[j], where=f"({path.name} {label} {y})") for j, y in cols.items()}
    if set(series) != {"amortizacion", "intereses", "gastos", "total"}:
        raise ParseError(f"{path.name}: faltan renglones ({sorted(series)})")
    out = []
    for y in sorted(cols.values()):
        d = DeudaAnual(
            y, series["amortizacion"][y], series["intereses"][y], series["gastos"][y], series["total"][y]
        )
        if abs(d.amortizacion + d.intereses + d.gastos - d.total) > 1:
            raise ParseError(f"{path.name}: el total de {y} no suma sus componentes")
        out.append(d)
    return out
