"""Parsers against the real originals committed in data/raw/.

The expected figures were checked by hand against the official documents (see the README).
"""

from pathlib import Path

import pytest

from gdmty.parsers import efipem, inegi_poblacion, mty_estado_analitico, sipot_xxiib
from gdmty.paths import DATA_RAW

MTY = DATA_RAW / "monterrey"
SP = DATA_RAW / "san-pedro"
SC = DATA_RAW / "santa-catarina"


def _need(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"falta el original {path} (ejecuta 'make fetch')")
    return path


def test_monterrey_objeto_2026t2_matches_document() -> None:
    e = mty_estado_analitico.parse_egresos_objeto(_need(MTY / "mty-egr-obj-2026T2.xlsx"))
    assert e.total["aprobado"] == 9_792_675_886.97
    assert e.total["modificado"] == 11_429_544_461.51
    assert e.total["devengado"] == 6_027_598_288.12
    assert e.total["pagado"] == 5_390_155_544.26
    assert [c.clave for c in e.lineas][:2] == ["1000", "2000"]
    serv_pers = e.lineas[0]
    assert serv_pers.montos["devengado"] == 1_432_151_162.05


def test_monterrey_administrativa_2026t2_has_19_dependencias() -> None:
    e = mty_estado_analitico.parse_egresos_administrativa(_need(MTY / "mty-egr-adm-2026T2.xlsx"))
    assert len(e.lineas) == 19
    seguridad = next(d for d in e.lineas if "Seguridad" in d.nombre)
    assert seguridad.montos["aprobado"] == 1_757_102_315.08
    assert seguridad.montos["devengado"] == 883_272_281.16
    assert round(sum(d.montos["devengado"] for d in e.lineas), 2) == e.total["devengado"]


def test_monterrey_blank_aprobado_is_proven_zero_and_noted() -> None:
    # New dependencias in 2025 have no approved budget: empty cell, Modificado = Ampliaciones.
    e = mty_estado_analitico.parse_egresos_administrativa(_need(MTY / "mty-egr-adm-2025T3.xlsx"))
    admin = next(d for d in e.lineas if d.nombre == "Secretaría de Administración")
    assert admin.montos["aprobado"] == 0
    assert admin.montos["modificado"] == admin.montos["ampliaciones"]
    assert admin.notas and "vacía" in admin.notas[0]


def test_monterrey_ingresos_2026t2() -> None:
    e = mty_estado_analitico.parse_ingresos(_need(MTY / "mty-ing-2026T2.xlsx"))
    assert e.total["pagado"] == 6_192_741_850.04  # 'Recaudado' column
    impuestos = next(r for r in e.lineas if r.nombre == "Impuestos")
    assert impuestos.montos["pagado"] == 2_418_095_214.86


def test_san_pedro_2026t2() -> None:
    f = sipot_xxiib.parse(_need(SP / "sp-xxiib-2026T2.xlsx"))
    p = f.periodos["2026T2"]
    t = p.total()
    assert t["aprobado"] == 6_137_023_798.00
    assert t["modificado"] == 6_431_825_352.26
    assert t["devengado"] == 2_385_560_166.99
    assert sorted(p.por_capitulo()) == ["1000", "2000", "3000", "4000", "5000", "6000", "9000"]


def test_san_pedro_placeholder_file_has_no_data() -> None:
    f = sipot_xxiib.parse(_need(SP / "sp-xxiib-2023T3.xlsx"))
    assert f.periodos == {}
    assert "2023T3" in f.sin_datos


def test_santa_catarina_2026t2() -> None:
    f = sipot_xxiib.parse(_need(SC / "sc-xxiib-2026T2.xlsx"))
    t = f.periodos["2026T2"].total()
    assert t["aprobado"] == 1_899_760_916.61
    assert t["modificado"] == 1_929_320_264.92
    assert t["devengado"] == 822_308_619.97
    assert t["pagado"] == 694_907_021.99


def test_santa_catarina_blank_cells_stay_empty() -> None:
    p = sipot_xxiib.parse(_need(SC / "sc-xxiib-2025T4.xlsx")).periodos["2025T4"]
    fila = next(f for f in p.filas if f.capitulo == "7000")
    assert fila.montos["devengado"] is None  # never replaced with 0
    assert p.celdas_vacias()


def test_efipem_and_population() -> None:
    efi = efipem.parse(_need(DATA_RAW / "inegi" / "inegi-efipem-municipal.csv"))
    assert efi["monterrey"][2024].egresos_total == 10_286_997_010
    pob = inegi_poblacion.parse(_need(DATA_RAW / "inegi" / "inegi-mgem-19.json"))
    assert pob == {"monterrey": 1_142_994, "san-pedro": 132_169, "santa-catarina": 306_322}
