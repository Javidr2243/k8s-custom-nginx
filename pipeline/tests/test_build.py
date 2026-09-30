"""Build end to end on the real originals, into a temporary folder."""

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from gdmty import build as build_mod
from gdmty.build import build
from gdmty.paths import DATA_INTERMEDIO, DATA_RAW


@pytest.fixture(scope="module")
def out(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if not (DATA_RAW / "manifest.json").exists():
        pytest.skip("faltan originales (ejecuta 'make fetch')")
    d = tmp_path_factory.mktemp("v1")
    report = build(d)
    assert report.errores == []
    return d


def _load(out: Path, rel: str) -> dict:
    return json.loads((out / rel).read_text(encoding="utf-8"))


def test_verified_totals(out: Path) -> None:
    for mid, expected in [
        ("monterrey", 6_027_598_288.12),
        ("san-pedro", 2_385_560_166.99),
        ("santa-catarina", 822_308_619.97),
    ]:
        periodos = {p["periodo"]: p for p in _load(out, f"egresos/{mid}.json")["periodos"]}
        assert periodos["2026T2"]["total"]["devengado"] == expected


def test_every_period_points_to_a_listed_source(out: Path) -> None:
    fuentes = _load(out, "fuentes.json")["fuentes"]
    for mid in ("monterrey", "san-pedro", "santa-catarina"):
        for p in _load(out, f"egresos/{mid}.json")["periodos"]:
            assert p["fuente"] in fuentes
            assert fuentes[p["fuente"]]["url"].startswith("https://")
            assert fuentes[p["fuente"]]["sha256"]


def test_gaps_are_explicit_never_filled(out: Path) -> None:
    sc = _load(out, "egresos/santa-catarina.json")
    faltan = {f["periodo"]: f["motivo"] for f in sc["faltantes"]}
    # The 2023 file repeats identical figures in all four quarters: all are marked as missing.
    assert {"2023T1", "2023T2", "2023T3", "2023T4"} <= set(faltan)
    assert "repite" in faltan["2023T1"]
    assert "2023T1" not in {p["periodo"] for p in sc["periodos"]}


def test_san_pedro_only_capitulos(out: Path) -> None:
    sp = _load(out, "egresos/san-pedro.json")
    for p in sp["periodos"]:
        assert p["dependencias"] is None
        assert p["motivo_sin_dependencias"]


def test_comparativo_per_capita(out: Path) -> None:
    c = _load(out, "comparativo.json")
    mty2024 = next(a for a in c["municipios"]["monterrey"]["anual"] if a["anio"] == 2024)
    assert mty2024["gasto_por_habitante"] == round(mty2024["gasto_total"] / 1_142_994, 2)


def test_checksums_match(out: Path) -> None:
    for line in (out / "SHA256SUMS").read_text().splitlines():
        digest, rel = line.split("  ", 1)
        assert hashlib.sha256((out / rel).read_bytes()).hexdigest() == digest


def test_build_is_deterministic(out: Path, tmp_path: Path) -> None:
    build(tmp_path)
    assert (tmp_path / "SHA256SUMS").read_text() == (out / "SHA256SUMS").read_text()


def test_provenance_archived_copy_and_validation(out: Path) -> None:
    fuentes = _load(out, "fuentes.json")["fuentes"]
    for fid, f in fuentes.items():
        # Every source has a fingerprint; an archived copy unless the original contains personal data.
        assert f["sha256"] and len(f["sha256"]) == 64, fid
        if f["copia"] is None:
            assert f["sin_copia"] and "-contratos" in f["archivo"], fid
            continue
        assert f["copia"].startswith("/data/originales/"), fid
        assert (DATA_RAW / f["copia"].removeprefix("/data/originales/")).is_file(), fid
    val = _load(out, "validacion.json")
    ids = {c["id"] for c in val["chequeos"]}
    assert {"suma", "periodo", "identidad", "cruce_inegi"} <= ids
    suma = next(c for c in val["chequeos"] if c["id"] == "suma")
    assert suma["revisados"] == suma["aprobados"] > 0  # our sums always match the documents
    assert all(a["mensaje"] for a in val["advertencias"])
    # Every document a warning or failed check points to can be opened from the site.
    citadas = {a["fuente"] for a in val["advertencias"]} | {
        x["fuente"] for c in val["chequeos"] for x in c["fallas"]
    }
    assert citadas - {None} <= set(fuentes)


def test_intermediates_hide_rfc_of_individuals() -> None:
    archivos = sorted((DATA_INTERMEDIO / "contratos").glob("*.json"))
    assert archivos
    rfc_persona = re.compile(r"\b[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}\b")
    for a in archivos:
        texto = a.read_text(encoding="utf-8")
        assert not rfc_persona.search(texto), a.name
        for c in json.loads(texto)["contratos"]:
            assert c["rfc"] is None or len(c["rfc"]) == 12


def test_build_without_contract_originals(out: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # As in CI and the public repo: contract originals are absent, their masked intermediates stand in for them.
    raw = tmp_path / "raw"
    shutil.copytree(DATA_RAW, raw, ignore=shutil.ignore_patterns("*-contratos*"))
    monkeypatch.setattr(build_mod, "DATA_RAW", raw)
    report = build(tmp_path / "v1")
    assert report.errores == []
    assert (tmp_path / "v1" / "SHA256SUMS").read_text() == (out / "SHA256SUMS").read_text()
