"""SHCP (Disciplina Financiera): Registro Público Único and Sistema de Alertas.

- rpu_saldos: 'Indicadores de Obligaciones' 02_04 file, registered balances by municipality (millions of pesos).
  The file is national; only the 'Nuevo León' block is read (there are other 'Santa Catarina's).
- rpu_registro: daily register, one row per loan. `extract_registro` filters it to the three municipalities.
- alertas: municipal Sistema de Alertas results (overall result and indicators).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from gdmty.catalogos import MUNICIPIOS
from gdmty.parsers.xlsx import open_workbook, period_end_from_title, rows
from gdmty.util import ParseError, clean_label, norm_label, parse_date, round_money, to_decimal, to_number

ENTIDADES = [
    "Aguascalientes",
    "Baja California",
    "Baja California Sur",
    "Campeche",
    "Coahuila",
    "Colima",
    "Chiapas",
    "Chihuahua",
    "Ciudad de México",
    "Durango",
    "Guanajuato",
    "Guerrero",
    "Hidalgo",
    "Jalisco",
    "México",
    "Michoacán",
    "Morelos",
    "Nayarit",
    "Nuevo León",
    "Oaxaca",
    "Puebla",
    "Querétaro",
    "Quintana Roo",
    "San Luis Potosí",
    "Sinaloa",
    "Sonora",
    "Tabasco",
    "Tamaulipas",
    "Tlaxcala",
    "Veracruz",
    "Yucatán",
    "Zacatecas",
]
_ENTIDADES_NORM = {norm_label(e) for e in ENTIDADES} | {
    norm_label("Coahuila de Zaragoza"),
    norm_label("Michoacán de Ocampo"),
    norm_label("Veracruz de Ignacio de la Llave"),
    norm_label("Estado de México"),
}
_NOMBRE_A_ID = {norm_label(m["nombre"]): mid for mid, m in MUNICIPIOS.items()}
MILLONES = 1_000_000
MUNICIPIOS_NL = 51


# --- Balances by municipality (quarterly) ---------------------------------------------------------


@dataclass
class SaldoRPU:
    fecha: date
    banca_multiple: float
    banca_desarrollo: float
    emisiones: float
    otros: float
    total: float


def rpu_saldos(path: Path) -> dict[str, SaldoRPU]:
    """{municipio_id: SaldoRPU} in pesos (the file uses millions)."""
    wb = open_workbook(path)
    try:
        all_rows = list(rows(wb.worksheets[0]))
    finally:
        wb.close()
    titulo = next((c for r in all_rows[:6] for c in r if isinstance(c, str) and "Saldos al" in c), None)
    if titulo is None or "millones" not in " ".join(str(c) for r in all_rows[:6] for c in r if c):
        raise ParseError(f"{path.name}: no es el cuadro de saldos por municipio en millones de pesos")
    fecha = period_end_from_title([(titulo.replace("Saldos", "Del 1 de enero"),)])
    data = [
        vals
        for r in all_rows
        if len(vals := [c for c in r if c not in (None, "")]) >= 6 and isinstance(vals[0], str)
    ]
    start = next((i for i, v in enumerate(data) if norm_label(v[0]) == norm_label("Nuevo León")), None)
    if start is None:
        raise ParseError(f"{path.name}: no se encontró el bloque de Nuevo León")
    # Nuevo León has exactly 51 municipalities. "Hidalgo" is both an NL municipality and a state, so
    # the block is delimited by position and then checked: the next row must be another state.
    block = data[start + 1 : start + 1 + MUNICIPIOS_NL]
    if (
        start + 1 + MUNICIPIOS_NL < len(data)
        and norm_label(data[start + 1 + MUNICIPIOS_NL][0]) not in _ENTIDADES_NORM
    ):
        raise ParseError(f"{path.name}: el bloque de Nuevo León no tiene {MUNICIPIOS_NL} municipios")
    out: dict[str, SaldoRPU] = {}
    for vals in block:
        name = norm_label(vals[0])
        if name in _NOMBRE_A_ID:
            nums = [
                round_money(to_decimal(v, where=f"({path.name} {vals[0]})") * MILLONES) for v in vals[1:6]
            ]
            s = SaldoRPU(fecha, *nums)
            if abs(sum(nums[:4]) - nums[4]) > 1:
                raise ParseError(f"{path.name}: el saldo total de {vals[0]} no suma sus componentes")
            out[_NOMBRE_A_ID[name]] = s
    if set(out) != set(MUNICIPIOS):
        raise ParseError(f"{path.name}: faltan municipios en el bloque de Nuevo León ({sorted(out)})")
    return out


# --- Daily register (loan by loan) ----------------------------------------------------------------

REGISTRO_COLS = [
    "municipio",
    "acreedor",
    "tipo",
    "fecha_contratacion",
    "fecha_inscripcion",
    "monto_original",
    "saldo",
    "saldo_fecha",
    "plazo_dias",
    "tasa",
    "sobretasa",
    "vencimiento",
    "fuente_pago",
    "porcentaje_afectado",
    "destino",
]
_DEUDORES = {norm_label(f"Municipio de {m['nombre']}"): mid for mid, m in MUNICIPIOS.items()}


def _registro_header(all_rows: list[tuple]) -> tuple[int, dict[str, int], date]:
    for i, r in enumerate(all_rows[:10]):
        labels = [norm_label(c) for c in r]
        if any(lab.startswith("deudor u obligado") for lab in labels):
            col = {}
            for j, lab in enumerate(labels):
                for key, pref in [
                    ("entidad", "entidad federativa"),
                    ("deudor", "deudor u obligado"),
                    ("acreedor", "institucion financiera"),
                    ("tipo", "tipo de obligacion"),
                    ("fecha_contratacion", "fecha de contratacion"),
                    ("fecha_inscripcion", "fecha de inscripcion"),
                    ("monto_original", "monto original contratado"),
                    ("saldo", "saldo al"),
                    ("tasa", "tasa de interes"),
                    ("sobretasa", "sobretasa"),
                    ("vencimiento", "fecha de vencimiento"),
                    ("fuente_pago", "fuente"),
                    ("porcentaje_afectado", "porcentaje afectado"),
                    ("destino", "destino"),
                    ("plazo", "plazo pactado"),
                ]:
                    if lab.startswith(pref) and key not in col:
                        col[key] = j
            m = re.search(r"saldo al (\d{1,2}) de ([a-z]+) de (\d{4})", labels[col["saldo"]])
            if not m:
                raise ParseError("no se encontró la fecha del saldo en el encabezado del registro")
            fecha = period_end_from_title([(f"al {m.group(1)} de {m.group(2)} de {m.group(3)}",)])
            # 'Plazo pactado' has two sub-columns (MESES, DÍAS) in the next row.
            sub = [norm_label(c) for c in all_rows[i + 1]] if i + 1 < len(all_rows) else []
            if "plazo" in col and col["plazo"] + 1 < len(sub) and sub[col["plazo"] + 1] == "dias":
                col["plazo_dias"] = col["plazo"] + 1
            return i, col, fecha
    raise ParseError("no se encontró el encabezado del registro de deuda")


def extract_registro(xlsx_path: Path, out_csv: Path) -> int:
    """Filter the national register to the loans of the three municipalities (Nuevo León)."""
    wb = open_workbook(xlsx_path)
    try:
        sheet = wb["SHCP"] if "SHCP" in wb.sheetnames else wb.worksheets[0]
        all_rows = list(rows(sheet))
    finally:
        wb.close()
    h, col, fecha = _registro_header(all_rows)
    n = 0
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=REGISTRO_COLS, lineterminator="\n")
        w.writeheader()
        salida = []
        for r in all_rows[h + 1 :]:
            if len(r) <= col["deudor"] or norm_label(r[col["entidad"]]) != norm_label("Nuevo León"):
                continue
            mid = _DEUDORES.get(norm_label(r[col["deudor"]]))
            if mid is None:
                continue

            def g(key: str, row: tuple = r) -> object:
                j = col.get(key)
                return row[j] if j is not None and j < len(row) else None

            salida.append(
                {
                    "municipio": mid,
                    "acreedor": clean_label(g("acreedor")),
                    "tipo": clean_label(g("tipo")),
                    "fecha_contratacion": _iso(g("fecha_contratacion")),
                    "fecha_inscripcion": _iso(g("fecha_inscripcion")),
                    "monto_original": _num_or_blank(g("monto_original")),
                    "saldo": _num_or_blank(g("saldo")),
                    "saldo_fecha": fecha.isoformat(),
                    "plazo_dias": _num_or_blank(g("plazo_dias")),
                    "tasa": clean_label(g("tasa")),
                    "sobretasa": _num_or_blank(g("sobretasa")),
                    "vencimiento": _iso(g("vencimiento")),
                    "fuente_pago": clean_label(g("fuente_pago")) if g("fuente_pago") not in ("-",) else "",
                    "porcentaje_afectado": _num_or_blank(g("porcentaje_afectado")),
                    "destino": clean_label(g("destino")),
                }
            )
        salida.sort(
            key=lambda d: (d["municipio"], d["fecha_contratacion"], d["acreedor"], d["monto_original"])
        )
        for d in salida:
            w.writerow(d)
            n += 1
    return n


def _iso(v: object) -> str:
    if v in (None, "", "-"):
        return ""
    return parse_date(str(v)[:10]).isoformat() if not hasattr(v, "year") else parse_date(v).isoformat()


def _num_or_blank(v: object) -> str:
    """Number as text; '-' or blank -> '' (unknown, never 0)."""
    if v is None or (isinstance(v, str) and v.strip() in ("", "-")):
        return ""
    return repr(to_number(v))


@dataclass
class Credito:
    municipio: str
    acreedor: str
    tipo: str
    fecha_contratacion: str
    monto_original: float | None
    saldo: float | None
    saldo_fecha: str
    plazo_dias: float | None
    tasa: str
    sobretasa: float | None
    vencimiento: str
    fuente_pago: str
    destino: str


def rpu_registro(extract_csv: Path) -> list[Credito]:
    out = []
    with extract_csv.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):

            def num(k: str, row: dict = r) -> float | None:
                return float(row[k]) if row[k] else None

            out.append(
                Credito(
                    municipio=r["municipio"],
                    acreedor=r["acreedor"],
                    tipo=r["tipo"],
                    fecha_contratacion=r["fecha_contratacion"],
                    monto_original=num("monto_original"),
                    saldo=num("saldo"),
                    saldo_fecha=r["saldo_fecha"],
                    plazo_dias=num("plazo_dias"),
                    tasa=r["tasa"],
                    sobretasa=num("sobretasa"),
                    vencimiento=r["vencimiento"],
                    fuente_pago=r["fuente_pago"],
                    destino=r["destino"],
                )
            )
    return out


# --- Sistema de Alertas ---------------------------------------------------------------------------

ETIQUETAS_ALERTA = {
    1: "Endeudamiento sostenible",
    2: "Endeudamiento en observación",
    3: "Endeudamiento elevado",
}


@dataclass
class Alerta:
    resultado: int | None
    indicadores: list[float | None]  # [1: deuda/ILD, 2: servicio deuda/ILD, 3: corto plazo/ingresos totales]
    nota: str = ""


def alertas(path: Path) -> tuple[str, dict[str, Alerta]]:
    """Return (evaluation title, {municipio_id: Alerta}) for the three municipalities."""
    wb = open_workbook(path)
    try:
        all_rows = list(rows(wb.worksheets[0]))
    finally:
        wb.close()
    titulo = next(
        (clean_label(c) for r in all_rows[:6] for c in r if isinstance(c, str) and "Evaluación" in c), ""
    )
    if not titulo:
        raise ParseError(f"{path.name}: no se encontró el título de la evaluación")
    out: dict[str, Alerta] = {}
    for r in all_rows:
        vals = [c for c in r if c not in (None, "")]
        if len(vals) < 3 or norm_label(vals[0]) != norm_label("Nuevo León"):
            continue
        mid = _NOMBRE_A_ID.get(norm_label(vals[1]))
        if mid is None:
            continue
        try:
            resultado = int(float(str(vals[2])))
        except ValueError:
            out[mid] = Alerta(None, [None, None, None], nota=clean_label(vals[2]))
            continue
        nums: list[float | None] = []
        for k in (3, 5, 7):
            try:
                nums.append(round(float(str(vals[k])), 4) if k < len(vals) else None)
            except ValueError:
                nums.append(None)
        out[mid] = Alerta(resultado, nums)
    return titulo, out
