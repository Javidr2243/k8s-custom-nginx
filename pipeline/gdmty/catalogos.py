"""Fixed catalogues: municipalities and CONAC spending chapters (capítulos del gasto)."""

from __future__ import annotations

from gdmty.util import norm_label

MUNICIPIOS: dict[str, dict[str, str]] = {
    "monterrey": {"nombre": "Monterrey", "cvegeo": "19039"},
    "san-pedro": {"nombre": "San Pedro Garza García", "cvegeo": "19019"},
    "santa-catarina": {"nombre": "Santa Catarina", "cvegeo": "19048"},
}

# CONAC "Clasificador por Objeto del Gasto": capítulo -> official name and plain-language name.
CAPITULOS: dict[str, dict[str, str]] = {
    "1000": {"nombre": "Servicios personales", "sencillo": "Sueldos y prestaciones del personal"},
    "2000": {"nombre": "Materiales y suministros", "sencillo": "Materiales, combustible y suministros"},
    "3000": {"nombre": "Servicios generales", "sencillo": "Servicios (luz, renta, mantenimiento, etc.)"},
    "4000": {
        "nombre": "Transferencias, asignaciones, subsidios y otras ayudas",
        "sencillo": "Apoyos, subsidios y transferencias",
    },
    "5000": {"nombre": "Bienes muebles, inmuebles e intangibles", "sencillo": "Compra de equipo y bienes"},
    "6000": {"nombre": "Inversión pública", "sencillo": "Obra pública"},
    "7000": {
        "nombre": "Inversiones financieras y otras provisiones",
        "sencillo": "Inversiones y provisiones",
    },
    "8000": {"nombre": "Participaciones y aportaciones", "sencillo": "Participaciones y aportaciones"},
    "9000": {"nombre": "Deuda pública", "sencillo": "Pago de deuda e intereses"},
}

_CAPITULO_BY_LABEL = {norm_label(v["nombre"]): k for k, v in CAPITULOS.items()}
# Variants seen in the sources.
_CAPITULO_BY_LABEL.update(
    {
        norm_label("Transferencias, Asignaciones, Subsidios y Otras Ayudas"): "4000",
        norm_label("Bienes Muebles, Inmuebles e Intangible"): "5000",
        norm_label("Inversion Publica"): "6000",
        norm_label("Inversiones Financieras y Otras Provisiones"): "7000",
        norm_label("Participaciones y Aportaciones"): "8000",
        norm_label("Deuda Publica"): "9000",
    }
)


def capitulo_por_nombre(label: object) -> str | None:
    """Chapter key (e.g. '1000') for an exact chapter label, or None."""
    return _CAPITULO_BY_LABEL.get(norm_label(label))


def capitulo_por_clave(clave: object) -> str:
    """'1000', '1100', 1200 or '1211' -> '1000'. Raises ValueError if it is not a valid key."""
    s = str(clave).strip().split(".")[0]
    if not s.isdigit() or not 1 <= int(s[0]) <= 9:
        raise ValueError(f"clave de capítulo inválida: {clave!r}")
    return f"{s[0]}000"
