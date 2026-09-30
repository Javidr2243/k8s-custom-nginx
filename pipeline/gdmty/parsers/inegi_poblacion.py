"""INEGI Marco Geoestadístico: catalogue of Nuevo León municipalities with 2020 Census population."""

from __future__ import annotations

import json
from pathlib import Path

from gdmty.catalogos import MUNICIPIOS
from gdmty.util import ParseError


def parse(path: Path) -> dict[str, int]:
    """{municipio_id: total population (Censo 2020)}."""
    data = json.loads(path.read_text(encoding="utf-8"))
    fuente = str(data.get("metadatos", {}).get("Fuente_informacion_estadistica", ""))
    if "Censo de Población y Vivienda, 2020" not in fuente:
        raise ParseError(f"fuente de población inesperada: {fuente!r}")
    by_cvegeo = {r["cvegeo"]: r for r in data["datos"]}
    out = {}
    for mid, m in MUNICIPIOS.items():
        rec = by_cvegeo.get(m["cvegeo"])
        if rec is None:
            raise ParseError(f"falta el municipio {m['cvegeo']} en el catálogo del INEGI")
        pob = int(str(rec["pob_total"]))
        if pob <= 0:
            raise ParseError(f"población inválida para {mid}")
        out[mid] = pob
    return out
