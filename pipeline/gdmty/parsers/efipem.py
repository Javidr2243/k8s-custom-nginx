"""INEGI EFIPEM (Estadística de Finanzas Públicas Estatales y Municipales), annual municipal open data.

The official ZIP is ~96 MB (842 MB uncompressed), so the repository does not store it. `extract` reads
it in streaming mode (without extracting to disk) and keeps only the three municipalities, from
ANIO_MINIMO on. The extract (and the original's hash) is committed; `parse` reads the extract.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from gdmty.catalogos import MUNICIPIOS
from gdmty.safeio import safe_zip_members
from gdmty.util import ParseError, to_amount

ANIO_MINIMO = 2018
COLUMNS = [
    "ANIO",
    "CVEGEO",
    "CVE_ENT",
    "CVE_MUN",
    "TEMA",
    "CATEGORIA",
    "DESCRIPCION_CATEGORIA",
    "VALOR",
    "ESTATUS",
]
_FILE_RE = re.compile(r"^conjunto_de_datos/efipem_municipal_anual_tr_cifra_(\d{4})\.csv$")


def extract(zip_path: Path, out_csv: Path) -> int:
    """Filter the official ZIP to the 3 municipalities (Tema/Capítulo/Concepto levels). Returns the row count."""
    cvegeos = {m["cvegeo"] for m in MUNICIPIOS.values()}
    safe_zip_members(zip_path)
    n = 0
    with zipfile.ZipFile(zip_path) as zf, out_csv.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        members = sorted((m for m in zf.namelist() if _FILE_RE.match(m)), key=lambda s: s)
        if not members:
            raise ParseError("el ZIP de EFIPEM no contiene los archivos esperados")
        for member in members:
            year = int(_FILE_RE.match(member).group(1))  # type: ignore[union-attr]
            if year < ANIO_MINIMO:
                continue
            with zf.open(member) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
                if reader.fieldnames is None or [c.upper() for c in reader.fieldnames] != COLUMNS:
                    raise ParseError(f"{member}: columnas inesperadas {reader.fieldnames}")
                for row in reader:
                    row = {k.upper(): v for k, v in row.items()}
                    if row["CVEGEO"] in cvegeos and row["CATEGORIA"] in ("Tema", "Capítulo", "Concepto"):
                        writer.writerow(row)
                        n += 1
    if n == 0:
        raise ParseError("EFIPEM: no se encontraron filas de los municipios")
    return n


@dataclass
class EfipemAnio:
    anio: int
    estatus: str
    egresos_total: float | None
    ingresos_total: float | None
    egresos_capitulo: dict[str, float]
    ingresos_capitulo: dict[str, float]


def parse(extract_csv: Path) -> dict[str, dict[int, EfipemAnio]]:
    """{municipio_id: {year: EfipemAnio}} from the committed extract."""
    by_cvegeo = {m["cvegeo"]: mid for mid, m in MUNICIPIOS.items()}
    out: dict[str, dict[int, EfipemAnio]] = {}
    with extract_csv.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            mid = by_cvegeo.get(row["CVEGEO"])
            if mid is None:
                continue
            anio = int(row["ANIO"])
            rec = out.setdefault(mid, {}).setdefault(
                anio, EfipemAnio(anio, row["ESTATUS"], None, None, {}, {})
            )
            valor = to_amount(row["VALOR"], where=f"(EFIPEM {row['CVEGEO']} {anio})")
            tema, cat, desc = row["TEMA"], row["CATEGORIA"], row["DESCRIPCION_CATEGORIA"]
            if cat == "Tema" and tema == "Egresos":
                rec.egresos_total = valor
            elif cat == "Tema" and tema == "Ingresos":
                rec.ingresos_total = valor
            elif cat == "Capítulo" and tema == "Egresos":
                rec.egresos_capitulo[desc] = valor
            elif cat == "Capítulo" and tema == "Ingresos":
                rec.ingresos_capitulo[desc] = valor
    return out
