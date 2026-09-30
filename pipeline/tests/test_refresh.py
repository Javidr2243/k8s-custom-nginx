"""Automatic refresh (M8): quarter discovery, upstream-change detection and PR summary."""

import json
from datetime import date
from pathlib import Path

from gdmty.discover import _siguientes
from gdmty.manifest import Manifest
from gdmty.resumen import generar


def test_siguientes_trimestres_solo_si_ya_cerraron() -> None:
    assert _siguientes("2026T2", date(2026, 9, 30)) == ["2026T3"]
    assert _siguientes("2026T2", date(2026, 9, 1)) == []
    assert _siguientes("2025T4", date(2026, 7, 1)) == ["2026T1", "2026T2"]


def test_manifest_detecta_cambio_en_la_fuente(tmp_path: Path) -> None:
    m = Manifest(tmp_path / "manifest.json")
    assert m.record("x", {"sha256": "a", "descargado": "2026-07-01", "publicado": "2026-06-30"}) == "nuevo"
    assert m.record("x", {"sha256": "a", "descargado": "2026-08-01"}) == "sin_cambios"
    assert m.record("x", {"sha256": "b", "descargado": "2026-09-01"}) == "modificado"
    m.save()
    data = json.loads((tmp_path / "manifest.json").read_text())
    assert data["archivos"]["x"]["historial"] == [
        {"sha256": "a", "descargado": "2026-07-01", "publicado": "2026-06-30"}
    ]


def test_resumen_marca_fuente_modificada(tmp_path: Path) -> None:
    (tmp_path / "fetch-report.json").write_text(
        json.dumps(
            [
                {"id": "sp-xxiib-2026T2", "estado": "modificado", "detalle": ""},
                {"id": "mty-ing-2026T3", "estado": "nuevo", "detalle": ""},
            ]
        )
    )
    (tmp_path / "build-report.json").write_text(
        json.dumps({"anomalias": ["monterrey 2026T3 capítulo 6000 +45 %"]})
    )
    texto = generar(tmp_path)
    assert "⚠️ Fuente modificada" in texto
    assert "`sp-xxiib-2026T2`" in texto
    assert "mty-ing-2026T3" in texto
    assert "+45 %" in texto
