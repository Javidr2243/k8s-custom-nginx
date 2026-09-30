"""Linking contracts to departments and the patterns worth a closer look."""

import json
from datetime import date
from pathlib import Path

import pytest

from gdmty.contratos_analisis import fecha_constitucion, ligar_dependencia, senales
from gdmty.paths import PUBLIC_V1

DEPS = {  # chronological: the renamed security department appears first with its old name
    "secretaria-de-seguridad-y-proteccion-a-la-ciudadania": "Secretaría de Seguridad y Protección a la Ciudadanía",
    "ayuntamiento": "Ayuntamiento",
    "secretaria-del-ayuntamiento": "Secretaría del Ayuntamiento",
    "secretaria-de-obras-publicas": "Secretaría de Obras Públicas",
    "secretaria-de-administracion": "Secretaría de Administración",
    "secretaria-de-servicios-publicos": "Secretaría de Servicios Públicos",
    "tesoreria-municipal": "Tesorería Municipal",
    "secretaria-de-seguridad-y-proteccion-ciudadana": "Secretaría de Seguridad y Protección Ciudadana",
}


@pytest.mark.parametrize(
    ("area", "esperado"),
    [
        ("Secretaría de Obras Públicas", "secretaria-de-obras-publicas"),
        ("DIRECCION DE SERVICIOS MEDICOS DE LA SECRETARIA DE ADMINISTRACION", "secretaria-de-administracion"),
        ("DIRECCION DE PATRIMONIO DE LA TESORERIA MUNICIPAL", "tesoreria-municipal"),
        # Old and new names of the renamed department both resolve to the current one.
        (
            "SECRETARIA DE SEGURIDAD Y PROTECCION A LA CIUDADANIA",
            "secretaria-de-seguridad-y-proteccion-ciudadana",
        ),
        (
            "DIRECCION DE ENLACE MUNICIPAL DE LA SECRETRIA DE SERVICIOS PUBLICOS",
            "secretaria-de-servicios-publicos",
        ),
        ("Dirección de Asuntos Jurídicos de la Secretaría de Ayuntamiento", "secretaria-del-ayuntamiento"),
        # Never guessed: no department named, two departments named, or a one-word name inside a longer one.
        ("DIRECCION DE INGRESOS", None),
        ("Secretaría de Infraestructura Sostenible", None),
        (
            "DIRECCION DE ENLACE MUNICIPAL DE LA SECRETARIA DE SERVICIOS PUBLICOS Y LA DIRECCION DE MANTENIMIENTO Y "
            "EQUIPAMIENTO DE LA SECRETARIA DE ADMINISTRACION",
            None,
        ),
        ("Sindicatura del R. Ayuntamiento", None),
        ("", None),
    ],
)
def test_ligar_dependencia(area: str, esperado: str | None) -> None:
    assert ligar_dependencia(area, DEPS) == esperado


def test_fecha_constitucion() -> None:
    assert fecha_constitucion("SHO120316NQ2", date(2026, 8, 1)) == date(2012, 3, 16)
    assert fecha_constitucion("CSN920313N6A", date(2025, 1, 1)) == date(1992, 3, 13)
    # A date after the contract belongs to the previous century.
    assert fecha_constitucion("ABC990101XX1", date(2026, 1, 1)) == date(1999, 1, 1)
    assert fecha_constitucion("ABC261231XX1", date(2026, 6, 1)) == date(1926, 12, 31)
    # Not a company RFC, or not a valid date.
    assert fecha_constitucion("PEJU800101AB1", date(2026, 1, 1)) is None
    assert fecha_constitucion("ABC991301XX1", date(2026, 1, 1)) is None
    assert fecha_constitucion(None, date(2026, 1, 1)) is None


def _c(**kw) -> dict:
    base = {
        "numero": "1", "fecha": "2026-05-01", "proveedor": "EMPRESA, S.A. DE C.V.", "rfc": "EMP100101AB1",
        "tipo_persona": "moral", "monto": 1000.0, "descripcion": "x", "area": "a", "fuente": "f",
        "categoria": "directa",
    }  # fmt: skip
    return {**base, **kw}


def test_senales_reglas() -> None:
    cs = [
        _c(rfc="NUE251001AB1", monto=5_000_000.0),  # 7 months old → young
        _c(rfc="VIE240101AB1"),  # 2 years 4 months → not young
        _c(rfc=None, proveedor="Juan Pérez", tipo_persona="fisica", monto=9e9),  # individuals never listed
        _c(rfc=None, proveedor="Información reservada", tipo_persona="reservada", monto=8e9),
        *[_c(rfc="REP100101AB1", proveedor="REPETIDA SA", numero=str(i)) for i in range(3)],
        _c(categoria="modificatorio", monto=250.0),
    ]
    s = senales(cs)
    assert [x["rfc"] for x in s["empresas_jovenes"]] == ["NUE251001AB1"]
    assert s["empresas_jovenes"][0]["dias"] == 212
    assert [(x["proveedor"], x["n"]) for x in s["directas_repetidas"]] == [("REPETIDA SA", 3)]
    assert s["mayores_directas"][0]["monto"] == 5_000_000.0
    assert all(x["proveedor"] not in ("Juan Pérez", "Información reservada") for x in s["mayores_directas"])
    assert s["modificatorios"] == {"n": 1, "monto": 250.0, "mayores": [s["modificatorios"]["mayores"][0]]}


def test_senales_publicadas_sin_personas_fisicas() -> None:
    archivos = sorted((PUBLIC_V1 / "contratos").glob("*.json"))
    if not archivos:
        pytest.skip("sin datos publicados")
    for a in archivos:
        d = json.loads(Path(a).read_text(encoding="utf-8"))
        s = d["senales"]
        filas = [
            *s["empresas_jovenes"],
            *s["directas_repetidas"],
            *s["mayores_directas"],
            *s["modificatorios"]["mayores"],
        ]
        assert all(x["rfc"] is None or len(x["rfc"]) == 12 for x in filas), a.name
        assert all(x["dias"] < 365 for x in s["empresas_jovenes"]), a.name
        assert all(x["n"] >= 3 for x in s["directas_repetidas"]), a.name
