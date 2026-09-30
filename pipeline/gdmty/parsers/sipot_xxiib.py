"""SIPOT format NLA95FXXIIB — 'Ejercicio de los egresos presupuestarios' (Ley de Transparencia NL, Art. 95
fr. XXII inciso B). Published as XLSX by every municipality in Nuevo León.

Structure (standard SIPOT export):
- Main sheet ('Reporte de Formatos' or 'Informacion'): one row per period with start/end dates and an
  ID pointing to rows in the 'Tabla_393674' sheet.
- 'Tabla_393674': chapter/concept rows with Aprobado, Ampliación/(Reducciones), Modificado, Devengado,
  Pagado and Subejercicio. Several rows can share an ID.

Amounts are cumulative from January even when the main sheet states a quarterly period
(e.g. 01/04/2026–30/06/2026); the cumulative check in validate.py confirms it.
"""

from __future__ import annotations

import contextlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from gdmty.catalogos import CAPITULOS, capitulo_por_clave
from gdmty.parsers.xlsx import measure_of, open_workbook, rows
from gdmty.util import ParseError, clean_label, norm_label, parse_date, round_money, to_amount

MEASURES = ("aprobado", "ampliaciones", "modificado", "devengado", "pagado", "subejercicio")


@dataclass
class FilaXXIIB:
    clave: str  # original key (e.g. '1000' or '1100')
    capitulo: str  # '1000'…'9000'
    denominacion: str
    montos: dict[str, float | None]  # None = empty cell in the document (never replaced with 0)


@dataclass
class PeriodoXXIIB:
    fecha_inicio: date
    fecha_corte: date
    filas: list[FilaXXIIB] = field(default_factory=list)
    fecha_actualizacion: date | None = None

    def por_capitulo(self) -> dict[str, dict[str, float]]:
        """Sum by chapter. Empty cells are left out of the sum (see celdas_vacias())."""
        out: dict[str, dict[str, float]] = {}
        for f in self.filas:
            acc = out.setdefault(f.capitulo, dict.fromkeys(MEASURES, 0.0))
            for m in MEASURES:
                v = f.montos[m]
                if v is not None:
                    acc[m] = round_money(acc[m] + v)
        return dict(sorted(out.items()))

    def total(self) -> dict[str, float]:
        return {
            m: round_money(sum(v for f in self.filas if (v := f.montos[m]) is not None)) for m in MEASURES
        }

    def celdas_vacias(self) -> list[str]:
        """Description of each empty cell, e.g. 'capítulo 7000 (Inversiones…): devengado'."""
        out = []
        for f in self.filas:
            vacias = [m for m in MEASURES if f.montos[m] is None]
            if vacias:
                out.append(f"clave {f.clave} ({f.denominacion}): {', '.join(vacias)}")
        return out


def _amount_or_blank(value: object, *, where: str) -> float | None:
    """Empty cell -> None (never 0). '-' is the accounting convention for zero."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if isinstance(value, str) and value.strip() == "-":
        return 0.0
    return to_amount(value, where=where)


def _find_header(all_rows: list[tuple[object, ...]], names: dict[str, tuple[str, ...]]) -> tuple[int, dict]:
    for i, row in enumerate(all_rows):
        labels = [norm_label(c) for c in row]
        cols: dict[str, int] = {}
        for key, variants in names.items():
            for j, lab in enumerate(labels):
                if any(lab.startswith(v) for v in variants):
                    cols[key] = j
                    break
        if len(cols) == len(names):
            return i, cols
    raise ParseError(f"no se encontró el encabezado con {list(names)}")


@dataclass
class ArchivoXXIIB:
    periodos: dict[str, PeriodoXXIIB]
    sin_datos: dict[str, str]  # period -> the municipality's note (placeholder file with no figures)
    enlaces: dict[str, str] = field(default_factory=dict)  # period -> linked document (e.g. PDF)


def parse(path: Path) -> ArchivoXXIIB:
    """Parse a file: periods with figures and periods published without data."""
    wb = open_workbook(path)
    try:
        sheets = wb.sheetnames
        tabla_name = next((s for s in sheets if s.startswith("Tabla")), None)
        if tabla_name is None:
            raise ParseError(f"{path.name}: no tiene hoja 'Tabla_…'")
        main = list(rows(wb[sheets[0]]))
        tabla = list(rows(wb[tabla_name]))
    finally:
        wb.close()

    # Identify the format by its fixed SIPOT IDs (format 46571, table 393674). The "nombre corto" cell
    # is not reliable: some municipalities overwrite it.
    if tabla_name != "Tabla_393674" or not any(str(c).strip() == "46571" for r in main[:3] for c in r):
        raise ParseError(f"{path.name}: no es el formato SIPOT 46571 (NLA95FXXIIB)")

    # --- Main sheet: periods and their IDs -------------------------------------------------------
    h_idx, hcols = _find_header(
        main,
        {
            "inicio": ("fecha de inicio del periodo",),
            "fin": ("fecha de termino del periodo",),
            "id": ("clasificacion del estado analitico",),
        },
    )
    act_col = next(
        (j for j, c in enumerate(main[h_idx]) if norm_label(c).startswith("fecha de actualizacion")), None
    )
    nota_col = next((j for j, c in enumerate(main[h_idx]) if norm_label(c) == "nota"), None)
    link_col = next((j for j, c in enumerate(main[h_idx]) if norm_label(c).startswith("hipervinculo")), None)
    notas_periodo: dict[tuple[date, date], str] = {}
    links_periodo: dict[tuple[date, date], str] = {}
    id_to_period: dict[str, tuple[date, date]] = {}
    actualizacion: dict[tuple[date, date], date] = {}
    for r in main[h_idx + 1 :]:
        if len(r) <= max(hcols.values()) or r[hcols["id"]] in (None, ""):
            continue
        inicio, fin = parse_date(r[hcols["inicio"]]), parse_date(r[hcols["fin"]])
        id_to_period[str(r[hcols["id"]]).strip()] = (inicio, fin)
        if nota_col is not None and nota_col < len(r) and r[nota_col]:
            notas_periodo[(inicio, fin)] = clean_label(r[nota_col])
        if link_col is not None and link_col < len(r) and str(r[link_col] or "").startswith("https://"):
            links_periodo[(inicio, fin)] = str(r[link_col]).strip()
        if act_col is not None and r[act_col] not in (None, ""):
            with contextlib.suppress(ParseError):
                actualizacion[(inicio, fin)] = parse_date(r[act_col])
    if not id_to_period:
        raise ParseError(f"{path.name}: la hoja principal no tiene periodos")

    # --- Table: chapter/concept rows -------------------------------------------------------------
    t_idx = next((i for i, r in enumerate(tabla) if r and norm_label(r[0]) == "id"), None)
    if t_idx is None:
        raise ParseError(f"{path.name}: la hoja {tabla_name} no tiene encabezado 'ID'")
    header = tabla[t_idx]
    mcols = {m: j for j, c in enumerate(header) if (m := measure_of(c))}
    missing = [m for m in MEASURES if m not in mcols]
    if missing:
        raise ParseError(f"{path.name}: faltan columnas {missing}")
    clave_col = next(j for j, c in enumerate(header) if norm_label(c).startswith("clave del capitulo"))
    den_col = next(j for j, c in enumerate(header) if norm_label(c).startswith("denominacion"))

    single_period = len(set(id_to_period.values())) == 1
    only_period = next(iter(id_to_period.values()))
    grouped: dict[tuple[date, date], list[FilaXXIIB]] = defaultdict(list)
    for n, r in enumerate(tabla[t_idx + 1 :], start=t_idx + 2):
        if not r or all(c in (None, "") for c in r):
            continue
        rid = str(r[0]).strip()
        if rid in id_to_period:
            key = id_to_period[rid]
        elif single_period:
            # Some files number the rows 1..n instead of using the main sheet's ID.
            key = only_period
        else:
            raise ParseError(f"{path.name}: fila {n} con ID {rid} que no aparece en la hoja principal")
        where = f"{path.name} fila {n}"
        clave = str(r[clave_col] if r[clave_col] is not None else "").strip()
        if clave in ("", "0") and all(
            (v := _amount_or_blank(r[mcols[m]], where=where)) is None or v == 0 for m in MEASURES
        ):
            continue  # placeholder row ("no information yet"): no figures
        try:
            capitulo = capitulo_por_clave(clave)
        except ValueError as exc:
            raise ParseError(f"{where}: {exc}") from exc
        montos = {m: _amount_or_blank(r[mcols[m]], where=f"({m}, {where})") for m in MEASURES}
        grouped[key].append(
            FilaXXIIB(clave=clave, capitulo=capitulo, denominacion=clean_label(r[den_col]), montos=montos)
        )

    sin_datos, enlaces = {}, {}
    for inicio, fin in set(id_to_period.values()) - set(grouped):
        pid = f"{fin.year}T{(fin.month + 2) // 3}"
        sin_datos[pid] = notas_periodo.get((inicio, fin), "")
        if (inicio, fin) in links_periodo:
            enlaces[pid] = links_periodo[(inicio, fin)]

    out: dict[str, PeriodoXXIIB] = {}
    for (inicio, fin), filas in sorted(grouped.items()):
        if fin.month not in (3, 6, 9, 12):
            raise ParseError(f"{path.name}: periodo que no termina en fin de trimestre ({fin})")
        pid = f"{fin.year}T{fin.month // 3}"
        if pid in out:
            raise ParseError(f"{path.name}: el periodo {pid} aparece dos veces con fechas distintas")
        out[pid] = PeriodoXXIIB(
            fecha_inicio=inicio,
            fecha_corte=fin,
            filas=filas,
            fecha_actualizacion=actualizacion.get((inicio, fin)),
        )
    return ArchivoXXIIB(periodos=out, sin_datos=sin_datos, enlaces=enlaces)


def nombre_capitulo(clave: str) -> str:
    return CAPITULOS[clave]["nombre"]
