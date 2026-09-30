"""Generate data/public/v1/ from the originals in data/raw/ (never from the internet).

Deterministic: the same originals always produce the same JSON (no timestamps from the clock).
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date
from itertools import pairwise
from pathlib import Path
from typing import Any

from gdmty import __version__
from gdmty import sources as sources_mod
from gdmty.catalogos import CAPITULOS, MUNICIPIOS, capitulo_por_nombre
from gdmty.manifest import Manifest
from gdmty.parsers import efipem, inegi_poblacion, mty_estado_analitico, sipot_xxiib
from gdmty.paths import CACHE_DIR, DATA_RAW, PUBLIC_V1
from gdmty.util import ParseError, norm_label, quarter_of, round_money, slugify
from gdmty.validate import UMBRAL_ANOMALIA, Reporte, cambio_relativo, identidades_egresos, suma_cuadra

EGRESOS = ("aprobado", "ampliaciones", "modificado", "devengado", "pagado", "subejercicio")
INGRESOS_IN = ("aprobado", "ampliaciones", "modificado", "devengado", "pagado")
# In revenue statements the columns are called Estimado and Recaudado.
INGRESOS_OUT = {
    "aprobado": "estimado",
    "ampliaciones": "ampliaciones",
    "modificado": "modificado",
    "devengado": "devengado",
    "pagado": "recaudado",
}

MOTIVO_SIN_DEPENDENCIAS = "El municipio publica el gasto por dependencia solo en PDF escaneado; no está disponible en formato abierto."
MOTIVO_SIN_INGRESOS = "El municipio publica los ingresos trimestrales solo en PDF escaneado; se muestran los datos anuales del INEGI."


def _periodos_hasta(inicio: str, fin: str) -> list[str]:
    out, y, q = [], int(inicio[:4]), int(inicio[-1])
    while (y, q) <= (int(fin[:4]), int(fin[-1])):
        out.append(f"{y}T{q}")
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    return out


def _montos(d: dict[str, float | None], medidas: tuple[str, ...]) -> dict[str, float | None]:
    return {m: (round_money(d[m]) if d.get(m) is not None else None) for m in medidas}


def _write(path: Path, data: Any, report: Reporte, base: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    report.archivos.append(path.relative_to(base).as_posix())


# --- Spending ------------------------------------------------------------------------------------


def _egresos_monterrey(cfg, report: Reporte) -> dict[str, dict]:
    periodos: dict[str, dict] = {}
    by_period: dict[str, dict[str, sources_mod.Fuente]] = defaultdict(dict)
    for f in cfg.fuentes:
        if f.municipio == "monterrey" and f.tipo.startswith("mty_egresos"):
            by_period[f.periodo][f.tipo] = f
    for pid, fs in sorted(by_period.items()):
        obj_f, adm_f = fs.get("mty_egresos_objeto"), fs.get("mty_egresos_administrativa")
        if obj_f is None:
            report.error(f"monterrey {pid}: falta la clasificación por objeto del gasto")
            continue
        obj = mty_estado_analitico.parse_egresos_objeto(DATA_RAW / obj_f.archivo())
        if quarter_of(obj.fecha_corte) != pid:
            report.error(f"{obj_f.id}: el documento dice corte {obj.fecha_corte}, se esperaba {pid}")
        notas: list[str] = []
        for problema in suma_cuadra([c.montos for c in obj.lineas], obj.total, EGRESOS):
            report.error(f"{obj_f.id}: capítulos no suman el total ({problema})")
        capitulos = []
        for c in obj.lineas:
            for p in identidades_egresos(c.montos, f"{obj_f.id} capítulo {c.clave}"):
                report.advertencia(p)
            capitulos.append(
                {
                    "clave": c.clave,
                    "nombre": CAPITULOS[c.clave]["nombre"],
                    "montos": _montos(c.montos, EGRESOS),
                    "conceptos": [
                        {"nombre": k.nombre, "montos": _montos(k.montos, EGRESOS)} for k in c.conceptos
                    ],
                }
            )
        entry: dict[str, Any] = {
            "periodo": pid,
            "fecha_corte": obj.fecha_corte.isoformat(),
            "fuente": obj_f.id,
            "total": _montos(obj.total, EGRESOS),
            "capitulos": capitulos,
            "dependencias": None,
            "fuente_dependencias": None,
            "notas": notas,
        }
        if adm_f is not None:
            adm = mty_estado_analitico.parse_egresos_administrativa(DATA_RAW / adm_f.archivo())
            for problema in suma_cuadra([d.montos for d in adm.lineas], adm.total, EGRESOS):
                report.error(f"{adm_f.id}: dependencias no suman el total ({problema})")
            dif = suma_cuadra([adm.total], obj.total, EGRESOS)
            if dif:
                report.advertencia(f"monterrey {pid}: total por dependencia ≠ total por capítulo ({dif})")
                notas.append(
                    "El total por dependencia no coincide exactamente con el total por capítulo del gasto."
                )
            deps = []
            for d in adm.lineas:
                for p in identidades_egresos(d.montos, f"{adm_f.id} {d.nombre}"):
                    report.advertencia(p)
                deps.append(
                    {
                        "id": slugify(d.nombre),
                        "nombre": d.nombre,
                        "montos": _montos(d.montos, EGRESOS),
                        **({"notas": d.notas} if d.notas else {}),
                    }
                )
            entry["dependencias"] = deps
            entry["fuente_dependencias"] = adm_f.id
        periodos[pid] = entry
    return periodos


def _egresos_sipot(cfg, municipio: str, report: Reporte, sin_datos: dict[str, str]) -> dict[str, dict]:
    periodos: dict[str, dict] = {}
    for f in cfg.fuentes:
        if f.municipio != municipio or f.tipo != "sipot_xxiib":
            continue
        archivo = sipot_xxiib.parse(DATA_RAW / f.archivo())
        parsed = archivo.periodos
        for pid, nota in archivo.sin_datos.items():
            motivo = "El formato publicado no contiene cifras."
            if nota:
                motivo += f" Nota del municipio: «{nota[:300]}»"
            if pid in archivo.enlaces:
                motivo += f" El municipio enlaza a este documento: {archivo.enlaces[pid]}"
            sin_datos.setdefault(pid, motivo)
        if f.periodo is not None and f.periodo not in parsed and f.periodo not in archivo.sin_datos:
            report.error(f"{f.id}: se esperaba el periodo {f.periodo} y el archivo trae {sorted(parsed)}")
            continue
        for pid, p in parsed.items():
            if pid in periodos:
                if json.dumps(periodos[pid]["total"]) != json.dumps(_montos(p.total(), EGRESOS)):
                    report.error(
                        f"{municipio} {pid}: el periodo aparece en dos archivos con cifras distintas "
                        f"({periodos[pid]['fuente']}, {f.id})"
                    )
                continue  # same period repeated with the same figures: keep the first source
            notas = []
            vacias = p.celdas_vacias()
            if vacias:
                notas.append(
                    "El documento deja vacías algunas celdas; las sumas incluyen solo las celdas con valor: "
                    + "; ".join(vacias)
                    + "."
                )
                report.advertencia(f"{f.id} {pid}: celdas vacías: {vacias}")
            if p.fecha_inicio.month != 1:
                notas.append(
                    "El formato indica el periodo "
                    f"{p.fecha_inicio:%d/%m/%Y}–{p.fecha_corte:%d/%m/%Y}, pero los montos son acumulados desde enero."
                )
            for fila in p.filas:
                for prob in identidades_egresos(fila.montos, f"{f.id} {pid} clave {fila.clave}"):
                    report.advertencia(prob)
            capitulos = [
                {"clave": k, "nombre": CAPITULOS[k]["nombre"], "montos": _montos(v, EGRESOS), "conceptos": []}
                for k, v in p.por_capitulo().items()
            ]
            periodos[pid] = {
                "periodo": pid,
                "fecha_corte": p.fecha_corte.isoformat(),
                "fuente": f.id,
                "total": _montos(p.total(), EGRESOS),
                "capitulos": capitulos,
                "dependencias": None,
                "fuente_dependencias": None,
                "motivo_sin_dependencias": MOTIVO_SIN_DEPENDENCIAS,
                "notas": notas,
            }
    return periodos


def _descartar_repetidos(municipio: str, periodos: dict[str, dict], report: Reporte) -> dict[str, str]:
    """Quarters in the same year with identical figures cannot be told apart: all of them are dropped."""
    motivos: dict[str, str] = {}
    by_year: dict[str, list[str]] = defaultdict(list)
    for pid in periodos:
        by_year[pid[:4]].append(pid)
    for pids in by_year.values():
        firmas: dict[str, list[str]] = defaultdict(list)
        for pid in pids:
            firma = json.dumps(periodos[pid]["capitulos"], sort_keys=True)
            firmas[firma].append(pid)
        for grupo in firmas.values():
            if len(grupo) > 1:
                for pid in grupo:
                    motivos[pid] = (
                        "El documento oficial repite exactamente las mismas cifras en los trimestres "
                        f"{', '.join(sorted(grupo))}; no es posible saber a qué periodo corresponden."
                    )
                report.advertencia(
                    f"{municipio}: cifras idénticas en {sorted(grupo)}; se marcan como faltantes"
                )
    for pid in motivos:
        periodos.pop(pid, None)
    return motivos


def _checar_acumulados(municipio: str, periodos: dict[str, dict], report: Reporte) -> None:
    pids = sorted(periodos)
    for a, b in pairwise(pids):
        if a[:4] == b[:4]:
            da, db = periodos[a]["total"]["devengado"], periodos[b]["total"]["devengado"]
            if db + 1 < da:
                report.advertencia(
                    f"{municipio}: el devengado acumulado baja de {a} ({da:,.2f}) a {b} ({db:,.2f})"
                )


def _anomalias(municipio: str, periodos: dict[str, dict], report: Reporte) -> None:
    """Chapter changes > ±30 % against the same quarter of the previous year (cumulative figures)."""
    for pid, p in periodos.items():
        prev = periodos.get(f"{int(pid[:4]) - 1}{pid[4:]}")
        if prev is None:
            continue
        anteriores = {c["clave"]: c["montos"]["devengado"] for c in prev["capitulos"]}
        for c in p["capitulos"]:
            ant, nuevo = anteriores.get(c["clave"]), c["montos"]["devengado"]
            if ant is None or nuevo is None:
                continue
            cambio = cambio_relativo(nuevo, ant)
            if cambio is not None and abs(cambio) > UMBRAL_ANOMALIA and max(abs(nuevo), abs(ant)) > 5_000_000:
                report.anomalias.append(
                    f"{municipio} {pid} capítulo {c['clave']} ({c['nombre']}): devengado {cambio:+.0%} "
                    f"vs {prev['periodo']} ({ant:,.0f} → {nuevo:,.0f})"
                )


# --- Revenue -------------------------------------------------------------------------------------


def _ingresos_monterrey(cfg, report: Reporte) -> list[dict]:
    out = []
    for f in cfg.fuentes:
        if f.municipio != "monterrey" or f.tipo != "mty_ingresos":
            continue
        est = mty_estado_analitico.parse_ingresos(DATA_RAW / f.archivo())
        if quarter_of(est.fecha_corte) != f.periodo:
            report.error(f"{f.id}: el documento dice corte {est.fecha_corte}, se esperaba {f.periodo}")
        for problema in suma_cuadra([r.montos for r in est.lineas], est.total, INGRESOS_IN):
            report.error(f"{f.id}: rubros no suman el total ({problema})")

        def ren(m: dict) -> dict:
            return {INGRESOS_OUT[k]: v for k, v in _montos(m, INGRESOS_IN).items()}

        rubros = [
            {"id": slugify(r.nombre)[:60], "nombre": r.nombre, "montos": ren(r.montos)}
            for r in est.lineas
            if any(abs(v) > 0 for v in r.montos.values())
        ]
        out.append(
            {
                "periodo": f.periodo,
                "fecha_corte": est.fecha_corte.isoformat(),
                "fuente": f.id,
                "total": ren(est.total),
                "rubros": rubros,
            }
        )
    return sorted(out, key=lambda x: x["periodo"])


# --- Annual comparison (EFIPEM) and population ---------------------------------------------------


# EFIPEM lines that are not CONAC chapters.
EGRESOS_EFIPEM_EXTRA = {
    "otros egresos": "otros",
    "disponibilidad final": "disponibilidad-final",
    "por cuenta de terceros": "por-cuenta-de-terceros",
}


def _efipem_capitulos(d: dict[str, float], report: Reporte, donde: str) -> dict[str, float]:
    out = {}
    for nombre, valor in d.items():
        clave = capitulo_por_nombre(nombre) or EGRESOS_EFIPEM_EXTRA.get(norm_label(nombre))
        if clave is None:
            report.advertencia(f"{donde}: capítulo EFIPEM no reconocido '{nombre}'")
            continue
        out[clave] = round_money(valor)
    return dict(sorted(out.items()))


INGRESOS_EFIPEM = {
    norm_label(k): v
    for k, v in {
        "Impuestos": "impuestos",
        "Derechos": "derechos",
        "Productos": "productos",
        "Aprovechamientos": "aprovechamientos",
        "Contribuciones de mejoras": "contribuciones-de-mejoras",
        "Participaciones federales": "participaciones",
        "Aportaciones federales y estatales": "aportaciones",
        "Otros ingresos": "otros",
        "Financiamiento": "financiamiento",
        "Por cuenta de terceros": "por-cuenta-de-terceros",
        "Disponibilidad inicial": "disponibilidad-inicial",
    }.items()
}


def _efipem_ingresos(d: dict[str, float], report: Reporte, donde: str) -> dict[str, float]:
    out = {}
    for nombre, valor in d.items():
        key = INGRESOS_EFIPEM.get(norm_label(nombre))
        if key is None:
            report.advertencia(f"{donde}: rubro de ingreso EFIPEM no reconocido '{nombre}'")
            continue
        out[key] = round_money(valor)
    return out


def _gasto_efipem(egresos_total: float | None, caps: dict[str, float]) -> float | None:
    """EFIPEM total minus year-end cash ('Disponibilidad final'), which is not spending."""
    if egresos_total is None:
        return None
    return round_money(egresos_total - caps.get("disponibilidad-final", 0.0))


# --- Main ----------------------------------------------------------------------------------------


def build(out_dir: Path = PUBLIC_V1) -> Reporte:
    cfg = sources_mod.load()
    manifest = Manifest(DATA_RAW / "manifest.json")
    report = Reporte()
    faltan_archivos = [
        f.id for f in cfg.fuentes if manifest.get(f.id) is None or not (DATA_RAW / f.archivo()).exists()
    ]
    if faltan_archivos:
        report.error(f"faltan originales (ejecuta 'fetch'): {faltan_archivos}")
        return report

    try:
        sin_datos: dict[str, dict[str, str]] = {"monterrey": {}, "san-pedro": {}, "santa-catarina": {}}
        egresos = {
            "monterrey": _egresos_monterrey(cfg, report),
            "san-pedro": _egresos_sipot(cfg, "san-pedro", report, sin_datos["san-pedro"]),
            "santa-catarina": _egresos_sipot(cfg, "santa-catarina", report, sin_datos["santa-catarina"]),
        }
        ingresos_mty = _ingresos_monterrey(cfg, report)
        efi = efipem.parse(DATA_RAW / cfg.fuente("inegi-efipem-municipal").archivo())
        poblacion = inegi_poblacion.parse(DATA_RAW / cfg.fuente("inegi-mgem-19").archivo())
    except ParseError as exc:
        report.error(f"error al leer un original: {exc}")
        return report

    motivos_descartados = {m: _descartar_repetidos(m, p, report) for m, p in egresos.items()}
    ultimo_global = max(max(p) for p in egresos.values() if p)
    esperados = _periodos_hasta(cfg.periodo_inicial, ultimo_global)
    conocidos = {(f.municipio, f.periodo): f.motivo for f in cfg.faltantes_conocidos}

    fuentes_usadas: set[str] = set()
    municipios_out = []
    for mid, periodos in egresos.items():
        _checar_acumulados(mid, periodos, report)
        _anomalias(mid, periodos, report)
        faltantes = []
        for pid in esperados:
            if pid in periodos:
                continue
            motivo = (
                motivos_descartados[mid].get(pid)
                or sin_datos[mid].get(pid)
                or conocidos.get((mid, pid))
                or "No se encontró el documento publicado en formato abierto."
            )
            faltantes.append({"periodo": pid, "motivo": motivo})
        for p in periodos.values():
            fuentes_usadas.add(p["fuente"])
            if p["fuente_dependencias"]:
                fuentes_usadas.add(p["fuente_dependencias"])
        _write(
            out_dir / "egresos" / f"{mid}.json",
            {
                "municipio": mid,
                "unidad": "MXN",
                "nota_unidad": "Pesos mexicanos nominales (sin ajustar por inflación). Montos acumulados de enero a la fecha de corte.",
                "periodos": [periodos[k] for k in sorted(periodos)],
                "faltantes": faltantes,
            },
            report,
            out_dir,
        )

        anual = []
        for anio, rec in sorted(efi.get(mid, {}).items()):
            caps = _efipem_capitulos(rec.egresos_capitulo, report, f"EFIPEM {mid} {anio}")
            anual.append(
                {
                    "anio": anio,
                    "estatus": rec.estatus,
                    "egresos_total": rec.egresos_total,
                    "gasto_total": _gasto_efipem(rec.egresos_total, caps),
                    "ingresos_total": rec.ingresos_total,
                    "egresos_capitulo": caps,
                    "ingresos_rubro": _efipem_ingresos(rec.ingresos_capitulo, report, f"EFIPEM {mid} {anio}"),
                }
            )
        trimestral = ingresos_mty if mid == "monterrey" else []
        fuentes_usadas.update(t["fuente"] for t in trimestral)
        _write(
            out_dir / "ingresos" / f"{mid}.json",
            {
                "municipio": mid,
                "unidad": "MXN",
                "trimestral": trimestral,
                "motivo_sin_trimestral": None if trimestral else MOTIVO_SIN_INGRESOS,
                "anual": anual,
                "fuente_anual": "inegi-efipem-municipal",
            },
            report,
            out_dir,
        )

        # Cross-check: Q4 cumulative (own document) vs EFIPEM annual.
        for anio_rec in anual:
            p4 = periodos.get(f"{anio_rec['anio']}T4")
            if p4 and anio_rec["gasto_total"]:
                dev = p4["total"]["devengado"]
                rel = cambio_relativo(dev, anio_rec["gasto_total"])
                if rel is not None and abs(rel) > 0.02:
                    report.advertencia(
                        f"{mid} {anio_rec['anio']}: devengado 4T ({dev:,.0f}) difiere {rel:+.1%} del gasto anual "
                        f"del INEGI ({anio_rec['gasto_total']:,.0f})"
                    )

        municipios_out.append(
            {
                "id": mid,
                "nombre": MUNICIPIOS[mid]["nombre"],
                "cvegeo": MUNICIPIOS[mid]["cvegeo"],
                "poblacion": poblacion[mid],
                "fuente_poblacion": "inegi-mgem-19",
                "ultimo_periodo": max(periodos) if periodos else None,
                "detalle": {
                    "capitulos": True,
                    "dependencias": any(p["dependencias"] for p in periodos.values()),
                    "ingresos_trimestrales": bool(trimestral),
                },
            }
        )
    fuentes_usadas.update({"inegi-efipem-municipal", "inegi-mgem-19"})

    _write(out_dir / "municipios.json", {"municipios": municipios_out}, report, out_dir)

    anios = sorted({anio for m in efi.values() for anio in m})
    comparativo = {
        "anios": anios,
        "fuente": "inegi-efipem-municipal",
        "fuente_poblacion": "inegi-mgem-19",
        "metodo": (
            "Gasto = 'Total de egresos' del INEGI (EFIPEM) menos 'Disponibilidad final' (efectivo que queda en caja "
            "al cierre del año, que no es gasto). Por habitante = gasto ÷ población del Censo 2020."
        ),
        "municipios": {},
    }
    for mid in MUNICIPIOS:
        filas = []
        for anio, rec in sorted(efi.get(mid, {}).items()):
            caps = _efipem_capitulos(rec.egresos_capitulo, Reporte(), "")
            gasto = _gasto_efipem(rec.egresos_total, caps)
            filas.append(
                {
                    "anio": anio,
                    "estatus": rec.estatus,
                    "gasto_total": gasto,
                    "gasto_por_habitante": round_money(gasto / poblacion[mid]) if gasto else None,
                    "capitulos": {k: v for k, v in caps.items() if k in CAPITULOS},
                }
            )
        comparativo["municipios"][mid] = {"poblacion": poblacion[mid], "anual": filas}
    _write(out_dir / "comparativo.json", comparativo, report, out_dir)

    fuentes_out = {}
    for f in cfg.fuentes:
        if f.id not in fuentes_usadas:
            continue
        m = manifest.get(f.id) or {}
        fuentes_out[f.id] = {
            "titulo": f.titulo,
            "emisor": f.emisor,
            "municipio": f.municipio,
            "periodo": f.periodo,
            "url": f.url,
            "pagina": f.pagina,
            "formato": f.formato,
            "archivo": f"data/raw/{f.archivo().as_posix()}",
            "sha256": m.get("sha256"),
            "publicado": m.get("publicado"),
            "descargado": m.get("descargado"),
        }
    _write(out_dir / "fuentes.json", {"fuentes": fuentes_out}, report, out_dir)

    descargas = [e.get("descargado") for e in manifest.entries.values() if e.get("descargado")]
    _write(
        out_dir / "meta.json",
        {
            "version_datos": 1,
            "version_pipeline": __version__,
            "datos_al": max(descargas) if descargas else None,
            "periodo_mas_reciente": ultimo_global,
            "periodo_inicial": cfg.periodo_inicial,
            "municipios": {m["id"]: m["ultimo_periodo"] for m in municipios_out},
            "unidad": "Pesos mexicanos (MXN) nominales",
        },
        report,
        out_dir,
    )

    if not report.errores:
        _write_checksums(out_dir, report)
    _write_report(report)
    return report


def _write_checksums(out_dir: Path, report: Reporte) -> None:
    lines = []
    for rel in sorted(report.archivos):
        digest = hashlib.sha256((out_dir / rel).read_bytes()).hexdigest()
        lines.append(f"{digest}  {rel}")
    (out_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_report(report: Reporte) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / "build-report.json").write_text(
        json.dumps(
            {
                "fecha": date.today().isoformat(),
                "errores": report.errores,
                "advertencias": report.advertencias,
                "anomalias": report.anomalias,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
