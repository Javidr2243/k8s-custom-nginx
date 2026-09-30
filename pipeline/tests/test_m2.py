"""Debt, contracts and recent changes (M2), against the real originals."""

import json
from pathlib import Path

import pytest

from gdmty.build import build
from gdmty.parsers import contratos, shcp
from gdmty.paths import DATA_RAW


def _need(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"falta el original {path} (ejecuta 'make fetch')")
    return path


def test_rpu_saldos_reads_only_the_nuevo_leon_block() -> None:
    # "Santa Catarina" also exists in other states; "Hidalgo" is both an NL municipality and a state.
    s = shcp.rpu_saldos(_need(DATA_RAW / "shcp" / "shcp-rpu-saldos-2026T2.xlsx"))
    assert s["monterrey"].total == 1_457_039_379.53
    assert s["santa-catarina"].total == 102_167_717.79
    assert s["san-pedro"].total == 0


def test_rpu_registro_monterrey_loans() -> None:
    creditos = [c for c in shcp.rpu_registro(_need(DATA_RAW / "shcp" / "shcp-rpu-registro.csv"))
                if c.municipio == "monterrey"]  # fmt: skip
    assert sorted(c.saldo for c in creditos) == [585_785_906.0, 871_253_473.0]
    assert all(c.fuente_pago == "Fondo General de Participaciones" for c in creditos)
    assert {c.sobretasa for c in creditos} == {0.005, 0.0064}  # rates are not rounded to cents


def test_alertas_2026() -> None:
    titulo, res = shcp.alertas(_need(DATA_RAW / "shcp" / "shcp-alertas-2026-1s.xlsx"))
    assert "2026" in titulo
    assert {m: a.resultado for m, a in res.items()} == {"monterrey": 1, "san-pedro": 1, "santa-catarina": 1}


def test_rfc_privacy() -> None:
    assert contratos._rfc("DCA1511108Y4") == ("DCA1511108Y4", "moral")
    assert contratos._rfc("PEJU800101AB1") == (None, "fisica")  # individual: never published
    assert contratos._rfc("Información reservada") == (None, "desconocido")


def test_categorias() -> None:
    assert contratos.categoria("Excepción") == "directa"
    assert contratos.categoria("Tres cotizaciones") == "directa"
    assert contratos.categoria("Licitación pública") == "licitacion"
    assert contratos.categoria("Convenio modificatorio") == "modificatorio"


def test_monterrey_contracts_reserved_and_masked() -> None:
    cs = contratos.parse_sipot_xxix(_need(DATA_RAW / "monterrey" / "mty-contratos-2025.xls"))
    assert len(cs) > 250
    reservados = [c for c in cs if c.tipo_persona == "reservada"]
    assert reservados and all(c.proveedor == contratos.RESERVADA and c.rfc is None for c in reservados)
    assert all(c.rfc is None for c in cs if c.tipo_persona == "fisica")


def test_placeholder_month_has_no_contracts() -> None:
    # July 2026: "no contracts were made" -> no invented rows.
    assert contratos.parse_sipot_xxix(_need(DATA_RAW / "santa-catarina" / "sc-contratos-2026-07.xlsx")) == []


def test_build_outputs(tmp_path: Path) -> None:
    if not (DATA_RAW / "manifest.json").exists():
        pytest.skip("faltan originales")
    report = build(tmp_path)
    assert report.errores == []
    deuda = json.loads((tmp_path / "deuda" / "monterrey.json").read_text())
    assert deuda["saldos"][-1]["total"] == 1_457_039_379.53
    assert deuda["alertas"][-1]["etiqueta"] == "Endeudamiento sostenible"
    movs = json.loads((tmp_path / "movimientos.json").read_text())["movimientos"]
    fuentes = json.loads((tmp_path / "fuentes.json").read_text())["fuentes"]
    assert movs and all(m["fuente"] in fuentes for m in movs)
    for mid in ("monterrey", "san-pedro", "santa-catarina"):
        c = json.loads((tmp_path / "contratos" / f"{mid}.json").read_text())
        assert all(x["fuente"] in fuentes for x in c["contratos"])
        assert not any(x["rfc"] and len(x["rfc"]) == 13 for x in c["contratos"])
