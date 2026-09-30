"""What the contracts say beyond the table: which department asked for each purchase, and objective patterns that
journalists and comptrollers usually review. Pure functions over the parsed (already masked) contract rows.

Nothing here guesses: an area that does not clearly name one budget department stays unlinked, and a pattern is
only reported with the published figures behind it. Contracts with individuals (personas físicas) are left out of
the patterns so that no private person is singled out.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date

from gdmty.util import norm_label, round_money

# Spelling variants found in the contract files for names of the same department in the budget.
VARIANTES: dict[str, str] = {
    # Monterrey's contract files use both names for the security department.
    "secretaria de seguridad y proteccion a la ciudadania": "secretaria de seguridad y proteccion ciudadana",
    # "de" instead of "del" in some requesting areas.
    "secretaria de ayuntamiento": "secretaria del ayuntamiento",
    # Misspellings in Monterrey's files.
    "secretria": "secretaria",
    "sustantitva": "sustantiva",
}

# Thresholds of the patterns (shown on the site next to each one).
MESES_EMPRESA_JOVEN = 12
MIN_DIRECTAS_REPETIDAS = 3
TOP = 5


def _clave(text: object) -> str:
    """Comparable form: no accents, lowercase, punctuation as spaces, variants replaced."""
    s = re.sub(r"[^a-z0-9ñ]+", " ", norm_label(text)).strip()
    for variante, nombre in VARIANTES.items():
        s = re.sub(rf"\b{variante}\b", nombre, s)
    return s


def ligar_dependencia(area: str, dependencias: dict[str, str]) -> str | None:
    """Budget department (id) named by a contract's requesting area, or None when unclear.

    `dependencias` maps id → name in chronological order of the budgets (a later id wins for the same name).

    Matches the full name, or a department name contained in the area ("Dirección de Servicios Médicos de la
    Secretaría de Administración" → Secretaría de Administración). One-word names only match exactly. If the area
    names two different departments, it is ambiguous and stays unlinked."""
    a = _clave(area)
    if not a:
        return None
    # Departments renamed between budget years can share a name once variants are merged; the last id given (the
    # most recent budget) wins, which is the one the site shows.
    por_nombre = {_clave(nombre): dep_id for dep_id, nombre in dependencias.items() if _clave(nombre)}
    hallados: list[tuple[str, str]] = [
        (n, dep_id)
        for n, dep_id in por_nombre.items()
        if a == n or (" " in n and re.search(rf"\b{re.escape(n)}\b", a))
    ]
    # Drop matches contained in a longer match ("ayuntamiento" inside "secretaria del ayuntamiento").
    finales = {dep_id for n, dep_id in hallados if not any(n != m and n in m for m, _ in hallados)}
    return finales.pop() if len(finales) == 1 else None


def fecha_constitucion(rfc: str | None, referencia: date) -> date | None:
    """Founding date encoded in a company's RFC (12 characters: 3 letters + YYMMDD + 3), or None.

    The century is the latest one that does not put the date after `referencia` (the contract date)."""
    if not rfc or len(rfc) != 12 or not rfc[3:9].isdigit():
        return None
    yy, mm, dd = int(rfc[3:5]), int(rfc[5:7]), int(rfc[7:9])
    for siglo in (2000, 1900):
        try:
            d = date(siglo + yy, mm, dd)
        except ValueError:
            return None
        if d <= referencia:
            return d
    return None


def _fecha(iso: str | None) -> date | None:
    try:
        return date.fromisoformat(iso) if iso else None
    except ValueError:
        return None


def _rango(cs: list[dict]) -> list[str | None]:
    fechas = [c["fecha"] for c in cs if c["fecha"]]
    return [min(fechas), max(fechas)] if fechas else [None, None]


def _resumen_contrato(c: dict) -> dict:
    return {
        k: c.get(k) for k in ("numero", "fecha", "proveedor", "rfc", "monto", "descripcion", "area", "fuente")
    }


def _elegible(c: dict) -> bool:
    """Contracts that can appear in a pattern: a named company (not individuals, not withheld names)."""
    return c["tipo_persona"] not in ("fisica", "reservada") and c["proveedor"] != "No especificado"


def senales(contratos: list[dict]) -> dict:
    """Objective patterns worth a closer look. They do not indicate irregularities."""
    elegibles = [c for c in contratos if _elegible(c)]

    jovenes = []
    for c in elegibles:
        f = _fecha(c["fecha"])
        if not (f and c["monto"] and c["rfc"]):
            continue
        const = fecha_constitucion(c["rfc"], f)
        if const is None:
            continue
        dias = (f - const).days
        if 0 <= dias < MESES_EMPRESA_JOVEN * 365 / 12:
            jovenes.append({**_resumen_contrato(c), "constitucion": const.isoformat(), "dias": dias})
    jovenes.sort(key=lambda x: -x["monto"])
    # Context when none qualifies: the youngest company at the time of its contract.
    edades = []
    for c in elegibles:
        f = _fecha(c["fecha"])
        const = fecha_constitucion(c["rfc"], f) if f else None
        if const is not None and f is not None:
            edades.append(
                {**_resumen_contrato(c), "constitucion": const.isoformat(), "dias": (f - const).days}
            )
    mas_joven = min(edades, key=lambda x: x["dias"], default=None)

    directas = [c for c in elegibles if c["categoria"] == "directa"]
    por_prov: dict[str, list[dict]] = defaultdict(list)
    for c in directas:
        por_prov[c["rfc"] or norm_label(c["proveedor"])].append(c)
    repetidas = []
    for cs in por_prov.values():
        if len(cs) >= MIN_DIRECTAS_REPETIDAS:
            nombre = Counter(c["proveedor"] for c in cs).most_common(1)[0][0]
            repetidas.append(
                {
                    "proveedor": nombre,
                    "rfc": cs[0]["rfc"],
                    "n": len(cs),
                    "con_monto": sum(1 for c in cs if c["monto"]),
                    "monto": round_money(sum(c["monto"] for c in cs if c["monto"]))
                    if any(c["monto"] for c in cs)
                    else None,
                    "fechas": _rango(cs),
                    "fuente": cs[0]["fuente"],
                }
            )
    repetidas.sort(key=lambda x: (-x["n"], -(x["monto"] or 0)))

    mayores = sorted((c for c in directas if c["monto"]), key=lambda c: -c["monto"])[:TOP]

    modif = [c for c in contratos if c["categoria"] == "modificatorio"]
    return {
        "umbrales": {
            "meses_empresa_joven": MESES_EMPRESA_JOVEN,
            "min_directas_repetidas": MIN_DIRECTAS_REPETIDAS,
        },
        "empresas_jovenes": jovenes,
        "empresa_mas_joven": mas_joven,
        "directas_repetidas": repetidas,
        "mayores_directas": [_resumen_contrato(c) for c in mayores],
        "modificatorios": {
            "n": len(modif),
            "monto": round_money(sum(c["monto"] or 0 for c in modif)),
            "mayores": [
                _resumen_contrato(c)
                for c in sorted((c for c in modif if c["monto"]), key=lambda c: -c["monto"])[:TOP]
            ],
        },
    }


def _grupo(cs: list[dict]) -> dict:
    con_monto = [c for c in cs if c["monto"]]
    total = round_money(sum(c["monto"] for c in con_monto))
    directa = sum(c["monto"] for c in con_monto if c["categoria"] == "directa")
    return {
        "n": len(cs),
        "monto": total,
        "pct_directa": round(directa / total, 4) if total else None,
    }


def por_area(contratos: list[dict], top: int = 12) -> list[dict]:
    """Contracts grouped by requesting area (label as most often published)."""
    grupos: dict[str, list[dict]] = defaultdict(list)
    for c in contratos:
        grupos[_clave(c["area"]) or "sin area"].append(c)
    out = []
    for cs in grupos.values():
        etiqueta = Counter(c["area"] or "Sin área publicada" for c in cs).most_common(1)[0][0]
        out.append({"area": etiqueta, **_grupo(cs)})
    out.sort(key=lambda x: (-x["monto"], -x["n"]))
    return out[:top]


def por_dependencia(contratos: list[dict], nombres: dict[str, str]) -> dict[str, dict]:
    """Per linked budget department: totals, share without open tender, top suppliers and contracts."""
    grupos: dict[str, list[dict]] = defaultdict(list)
    for c in contratos:
        if c.get("dependencia"):
            grupos[c["dependencia"]].append(c)
    out = {}
    for dep, cs in sorted(grupos.items()):
        prov: dict[str, dict] = {}
        for c in cs:
            if not c["monto"] or c["tipo_persona"] == "reservada":
                continue
            k = c["rfc"] or norm_label(c["proveedor"])
            d = prov.setdefault(k, {"proveedor": c["proveedor"], "rfc": c["rfc"], "n": 0, "monto": 0.0})
            d["n"] += 1
            d["monto"] = round_money(d["monto"] + c["monto"])
        out[dep] = {
            "nombre": nombres.get(dep, dep),
            **_grupo(cs),
            "proveedores": sorted(prov.values(), key=lambda d: -d["monto"])[:3],
            "contratos": [
                _resumen_contrato(c)
                for c in sorted((c for c in cs if c["monto"]), key=lambda c: -c["monto"])[:3]
            ],
            "fechas": _rango(cs),
        }
    return out
