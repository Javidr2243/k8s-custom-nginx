"""Contracts and suppliers.

- SIPOT fr. XXIX (NLA95FXXIX, 'Resultados de procedimientos de adjudicación directa, licitación pública e
  invitación restringida'): Monterrey and Santa Catarina. Old (.xls) and new (.xlsx) formats; columns are
  found by header name.
- San Pedro: 'Relación de contratos' published by the Dirección de Adquisiciones (its own format).

Personal data: only companies' RFCs (12 characters) are published; individuals' RFCs (13) are masked.
Addresses, sex and final beneficiaries are never copied. Supplier names the municipality marks as
reserved are shown as such.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import xlrd

from gdmty.parsers.xlsx import open_workbook, rows
from gdmty.safeio import sniff_type
from gdmty.util import ParseError, clean_label, norm_label, parse_date, to_amount

RESERVADA = "Información reservada por el municipio"


def read_rows(path: Path) -> list[tuple[object, ...]]:
    """First sheet of an .xls or .xlsx file (by content, not extension)."""
    data = path.read_bytes()
    kind = sniff_type(data)
    if kind == "xlsx":
        wb = open_workbook(path)
        try:
            return list(rows(wb.worksheets[0]))
        finally:
            wb.close()
    if kind == "xls":
        book = xlrd.open_workbook(file_contents=data, on_demand=True)
        try:
            sh = book.sheet_by_index(0)
            out = []
            for i in range(sh.nrows):
                row = []
                for c in sh.row(i):
                    if c.ctype == xlrd.XL_CELL_DATE:
                        row.append(xlrd.xldate_as_datetime(c.value, book.datemode))
                    elif c.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                        row.append(None)
                    else:
                        row.append(c.value)
                out.append(tuple(row))
            return out
        finally:
            book.release_resources()
    raise ParseError(f"{path.name}: tipo de archivo no soportado ({kind})")


@dataclass
class Contrato:
    numero: str
    fecha: str | None  # ISO
    procedimiento: str  # label as published
    categoria: str  # licitacion | invitacion | directa | modificatorio | otro
    materia: str
    descripcion: str
    proveedor: str
    tipo_persona: str  # moral | fisica | reservada | desconocido
    rfc: str | None
    area: str  # requesting area (who needed the purchase), or the contracting area if not published
    area_solicitante: str
    area_contratante: str  # office that ran the procurement (often a central purchasing office)
    monto: float | None  # with taxes
    monto_sin_impuestos: float | None
    monto_maximo: float | None
    origen_recursos: str
    lugar_obra: str


_RFC_RE = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")
_PROCEDIMIENTOS = {
    "adjudicacion directa": "Adjudicación directa",
    "invitacion a cuando menos tres personas": "Invitación a cuando menos tres personas",
    "invitacion restringida": "Invitación a cuando menos tres personas",
    "licitacion publica": "Licitación pública",
    "otro (especificar)": "Otro",
    "otro": "Otro",
}


def procedimiento(texto: object) -> str:
    t = norm_label(texto)
    for k, v in _PROCEDIMIENTOS.items():
        if t.startswith(k):
            return v
    if "adjudicacion" in t and "direct" in t:
        return "Adjudicación directa"
    if "licitacion" in t:
        return "Licitación pública"
    if "invitacion" in t:
        return "Invitación a cuando menos tres personas"
    label = clean_label(texto)
    return label[:1].upper() + label[1:].lower() if label.isupper() else (label or "No especificado")


def categoria(proc: str) -> str:
    """Normalised category to compare municipalities (the original label is kept as well).

    'Excepción' and 'Tres cotizaciones' (Ley de Adquisiciones de N.L.) are awards without an open tender:
    they are grouped with direct awards. Contract amendments are counted separately.
    """
    t = norm_label(proc)
    if t.startswith("licitacion"):
        return "licitacion"
    if t.startswith("invitacion"):
        return "invitacion"
    if t.startswith(
        ("adjudicacion directa", "asignacion directa", "excepcion", "tres cotizaciones", "compra directa")
    ):
        return "directa"
    if "modificatorio" in t:
        return "modificatorio"
    return "otro"


def _no_aplica(v: object) -> bool:
    t = norm_label(v)
    return t.startswith(("no aplica", "no aplicable", "n/a", "na ")) or t in ("na", "n/a")


def _reservado(v: object) -> bool:
    return "reservad" in norm_label(v)


def _rfc(raw: object) -> tuple[str | None, str]:
    """(RFC to publish, person type). Individuals' RFCs (13 characters) are not published."""
    s = re.sub(r"[\s-]", "", str(raw or "")).upper()
    if not _RFC_RE.match(s):
        return None, "desconocido"
    if len(s) == 12:
        return s, "moral"
    return None, "fisica"


def _monto(v: object, where: str) -> float | None:
    if v is None or _reservado(v):
        return None
    if isinstance(v, str) and v.strip() in ("", "-", "0", "N/A", "NA", "No aplica"):
        return None
    try:
        m = to_amount(v, where=where)
    except ParseError:
        return None
    return m if m > 0 else None


def _fecha(v: object) -> str | None:
    if v in (None, ""):
        return None
    if isinstance(v, datetime | date):
        return (v.date() if isinstance(v, datetime) else v).isoformat()
    try:
        return parse_date(str(v).strip()[:10]).isoformat()
    except ParseError:
        return None


_SIPOT_FIELDS = {
    "ejercicio": ("ejercicio",),
    "procedimiento": ("tipo de procedimiento",),
    "materia": ("materia o tipo de contratacion", "materia"),
    "expediente": ("numero de expediente",),
    "descripcion": ("descripcion de las obras publicas, los bienes o los servicios",),
    "nombre": (
        "nombre(s) de la persona fisica ganadora",
        "nombre(s) del adjudicado",
        "nombre(s) del contratista",
    ),
    "apellido1": ("primer apellido de la persona fisica ganadora", "primer apellido del adjudicado"),
    "apellido2": ("segundo apellido de la persona fisica ganadora", "segundo apellido del adjudicado"),
    "razon_social": ("denominacion o razon social", "razon social del adjudicado"),
    "rfc": ("registro federal de contribuyentes",),
    "area_contratante": ("area(s) contratante(s)",),
    "area_solicitante": ("area(s) solicitante(s)",),
    "numero_contrato": ("numero que identifique al contrato",),
    "fecha_contrato": ("fecha del contrato",),
    "monto_sin": ("monto del contrato sin impuestos",),
    "monto_con": ("monto total del contrato con impuestos",),
    "monto_max": ("monto maximo, con impuestos",),
    "objeto": ("objeto del contrato",),
    "origen": ("origen de los recursos publicos",),
    "lugar": ("lugar donde se realizara la obra publica",),
}


def parse_sipot_xxix(path: Path) -> list[Contrato]:
    all_rows = read_rows(path)
    h = next(
        (
            i
            for i, r in enumerate(all_rows[:15])
            if any(norm_label(c) == "ejercicio" for c in r)
            and any(norm_label(c).startswith("tipo de procedimiento") for c in r)
        ),
        None,
    )
    if h is None:
        raise ParseError(f"{path.name}: no es el formato SIPOT de la fracción XXIX")
    labels = [norm_label(c) for c in all_rows[h]]
    col: dict[str, int] = {}
    for key, prefixes in _SIPOT_FIELDS.items():
        for j, lab in enumerate(labels):
            if any(lab.startswith(p) for p in prefixes):
                col[key] = j
                break
    faltan = [k for k in ("procedimiento", "razon_social", "rfc", "monto_con", "descripcion") if k not in col]
    if faltan:
        raise ParseError(f"{path.name}: faltan columnas {faltan}")

    out = []
    for n, r in enumerate(all_rows[h + 1 :], start=h + 2):

        def g(key: str, row: tuple = r) -> object:
            j = col.get(key)
            return row[j] if j is not None and j < len(row) else None

        if not str(g("ejercicio") or "").strip().isdigit():
            continue
        where = f"{path.name} fila {n}"
        razon = clean_label(g("razon_social"))
        persona = " ".join(
            clean_label(g(k)) for k in ("nombre", "apellido1", "apellido2") if clean_label(g(k))
        )
        rfc, tipo = _rfc(g("rfc"))
        if _reservado(razon) or (not razon and _reservado(persona)):
            proveedor, tipo, rfc = RESERVADA, "reservada", None
        elif razon:
            proveedor = razon
            tipo = "moral" if tipo == "desconocido" else tipo
        elif persona:
            proveedor, tipo = persona, "fisica"
        else:
            proveedor = "No especificado"
        if tipo == "fisica":
            rfc = None
        desc = clean_label(g("descripcion")) or clean_label(g("objeto"))
        monto = _monto(g("monto_con"), where)
        if proveedor == "No especificado" and not desc and monto is None:
            continue  # placeholder row ("no contracts were made in the period")
        proc = procedimiento(g("procedimiento"))
        out.append(
            Contrato(
                numero=clean_label(g("numero_contrato")) or clean_label(g("expediente")),
                fecha=_fecha(g("fecha_contrato")),
                procedimiento=proc,
                categoria=categoria(proc),
                materia=clean_label(g("materia")),
                descripcion="" if _reservado(desc) else desc,
                proveedor=proveedor,
                tipo_persona=tipo,
                rfc=rfc,
                area=clean_label(g("area_solicitante")) or clean_label(g("area_contratante")),
                area_solicitante=clean_label(g("area_solicitante")),
                area_contratante=clean_label(g("area_contratante")),
                monto=monto,
                monto_sin_impuestos=_monto(g("monto_sin"), where),
                monto_maximo=_monto(g("monto_max"), where),
                origen_recursos=clean_label(g("origen")),
                lugar_obra=""
                if _reservado(g("lugar")) or _no_aplica(g("lugar"))
                else clean_label(g("lugar")),
            )
        )
    return _dedupe(out)


def parse_san_pedro(path: Path) -> list[Contrato]:
    """San Pedro's 'Relación de contratos' (Dirección de Adquisiciones)."""
    all_rows = read_rows(path)
    h = next((i for i, r in enumerate(all_rows[:20]) if any(norm_label(c) == "proveedor" for c in r)), None)
    if h is None:
        raise ParseError(f"{path.name}: no se encontró el encabezado con 'PROVEEDOR'")
    labels = [norm_label(c) for c in all_rows[h]]

    def find(*prefixes: str) -> int | None:
        return next((j for j, lab in enumerate(labels) if any(lab.startswith(p) for p in prefixes)), None)

    c = {
        "secretaria": find("secretaria solicitante"),
        "area": find("area solicitante"),
        "objeto": find("objeto"),
        "proveedor": find("proveedor"),
        "rfc": find("r.f.c", "rfc"),
        "monto": find("monto contratado"),
        "procedimiento": find("procedimiento"),
        "inicio": find("fecha de inicio"),
        "numero": find("no. contrato", "numero de contrato"),
    }
    if None in (c["proveedor"], c["monto"], c["objeto"]):
        raise ParseError(f"{path.name}: faltan columnas básicas")
    out = []
    for n, r in enumerate(all_rows[h + 1 :], start=h + 2):

        def g(key: str, row: tuple = r) -> object:
            j = c.get(key)
            return row[j] if j is not None and j < len(row) else None

        proveedor = clean_label(g("proveedor"))
        if not proveedor:
            continue
        rfc, tipo = _rfc(g("rfc"))
        proc = procedimiento(g("procedimiento"))
        out.append(
            Contrato(
                numero=clean_label(g("numero")),
                fecha=_fecha(g("inicio")),
                procedimiento=proc,
                categoria=categoria(proc),
                materia="Adquisiciones y servicios",
                descripcion=clean_label(g("objeto")),
                proveedor=proveedor,
                tipo_persona="moral" if tipo == "desconocido" else tipo,
                rfc=rfc if tipo == "moral" else None,
                area=clean_label(g("secretaria")) or clean_label(g("area")),
                area_solicitante=clean_label(g("secretaria")) or clean_label(g("area")),
                area_contratante="",
                monto=_monto(g("monto"), f"{path.name} fila {n}"),
                monto_sin_impuestos=None,
                monto_maximo=None,
                origen_recursos="",
                lugar_obra="",
            )
        )
    return _dedupe(out)


def _dedupe(items: list[Contrato]) -> list[Contrato]:
    """SIPOT sometimes repeats the same row (once per sub-table); drop exact duplicates."""
    seen, out = set(), []
    for it in items:
        key = tuple(it.__dict__.values())
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out
