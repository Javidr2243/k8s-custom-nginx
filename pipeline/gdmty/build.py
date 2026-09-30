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
from gdmty.parsers import (
    contratos as contratos_mod,
)
from gdmty.parsers import (
    efipem,
    inegi_poblacion,
    mty_deuda,
    mty_estado_analitico,
    shcp,
    sipot_xxiib,
)
from gdmty.paths import CACHE_DIR, DATA_INTERMEDIO, DATA_RAW, PUBLIC_V1
from gdmty.util import ParseError, norm_label, quarter_of, round_money, slugify
from gdmty.validate import (
    CHEQUEOS,
    UMBRAL_ANOMALIA,
    Reporte,
    cambio_relativo,
    identidades_egresos,
    suma_cuadra,
)

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


def _identidades(report: Reporte, montos: dict, donde: str, fuente: str, municipio: str) -> None:
    problemas = identidades_egresos(montos, donde)
    report.chequeo(
        "identidad", not problemas, fuente=fuente, municipio=municipio, detalle="; ".join(problemas)
    )
    for p in problemas:
        report.advertencia(p, fuente=fuente, municipio=municipio)


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
        report.chequeo("periodo", quarter_of(obj.fecha_corte) == pid, fuente=obj_f.id, municipio="monterrey")
        if quarter_of(obj.fecha_corte) != pid:
            report.error(f"{obj_f.id}: el documento dice corte {obj.fecha_corte}, se esperaba {pid}")
        notas: list[str] = []
        problemas = suma_cuadra([c.montos for c in obj.lineas], obj.total, EGRESOS)
        report.chequeo("suma", not problemas, fuente=obj_f.id, municipio="monterrey")
        for problema in problemas:
            report.error(f"{obj_f.id}: capítulos no suman el total ({problema})")
        capitulos = []
        for c in obj.lineas:
            _identidades(report, c.montos, f"{obj_f.id} capítulo {c.clave}", obj_f.id, "monterrey")
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
            problemas = suma_cuadra([d.montos for d in adm.lineas], adm.total, EGRESOS)
            report.chequeo("suma", not problemas, fuente=adm_f.id, municipio="monterrey")
            for problema in problemas:
                report.error(f"{adm_f.id}: dependencias no suman el total ({problema})")
            dif = suma_cuadra([adm.total], obj.total, EGRESOS)
            report.chequeo(
                "dependencias_vs_capitulos",
                not dif,
                fuente=adm_f.id,
                municipio="monterrey",
                detalle="; ".join(dif),
            )
            if dif:
                report.advertencia(
                    f"monterrey {pid}: total por dependencia ≠ total por capítulo ({dif})",
                    fuente=adm_f.id,
                    municipio="monterrey",
                )
                notas.append(
                    "El total por dependencia no coincide exactamente con el total por capítulo del gasto."
                )
            deps = []
            for d in adm.lineas:
                _identidades(report, d.montos, f"{adm_f.id} {d.nombre}", adm_f.id, "monterrey")
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
                report.advertencia(f"{f.id} {pid}: celdas vacías: {vacias}", fuente=f.id, municipio=municipio)
            if p.fecha_inicio.month != 1:
                notas.append(
                    "El formato indica el periodo "
                    f"{p.fecha_inicio:%d/%m/%Y}–{p.fecha_corte:%d/%m/%Y}, pero los montos son acumulados desde enero."
                )
            for fila in p.filas:
                _identidades(report, fila.montos, f"{f.id} {pid} clave {fila.clave}", f.id, municipio)
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
            report.chequeo(
                "repetidos",
                len(grupo) == 1,
                fuente=periodos[grupo[0]]["fuente"],
                municipio=municipio,
                detalle=f"cifras idénticas en {', '.join(sorted(grupo))}",
            )
            if len(grupo) > 1:
                for pid in grupo:
                    motivos[pid] = (
                        "El documento oficial repite exactamente las mismas cifras en los trimestres "
                        f"{', '.join(sorted(grupo))}; no es posible saber a qué periodo corresponden."
                    )
                report.advertencia(
                    f"{municipio}: cifras idénticas en {sorted(grupo)}; se marcan como faltantes",
                    fuente=periodos[grupo[0]]["fuente"],
                    municipio=municipio,
                )
    for pid in motivos:
        periodos.pop(pid, None)
    return motivos


def _checar_acumulados(municipio: str, periodos: dict[str, dict], report: Reporte) -> None:
    pids = sorted(periodos)
    for a, b in pairwise(pids):
        if a[:4] == b[:4]:
            da, db = periodos[a]["total"]["devengado"], periodos[b]["total"]["devengado"]
            msg = f"{municipio}: el devengado acumulado baja de {a} ({da:,.2f}) a {b} ({db:,.2f})"
            report.chequeo(
                "acumulado", db + 1 >= da, fuente=periodos[b]["fuente"], municipio=municipio, detalle=msg
            )
            if db + 1 < da:
                report.advertencia(msg, fuente=periodos[b]["fuente"], municipio=municipio)


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
        report.chequeo(
            "periodo", quarter_of(est.fecha_corte) == f.periodo, fuente=f.id, municipio="monterrey"
        )
        if quarter_of(est.fecha_corte) != f.periodo:
            report.error(f"{f.id}: el documento dice corte {est.fecha_corte}, se esperaba {f.periodo}")
        problemas = suma_cuadra([r.montos for r in est.lineas], est.total, INGRESOS_IN)
        report.chequeo("suma", not problemas, fuente=f.id, municipio="monterrey")
        for problema in problemas:
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


# --- Debt ----------------------------------------------------------------------------------------


def _deuda(
    cfg, egresos: dict[str, dict[str, dict]], report: Reporte, out_dir: Path, usadas: set[str]
) -> None:
    saldos: dict[str, list[dict]] = defaultdict(list)
    for f in cfg.fuentes:
        if f.tipo != "shcp_rpu_saldos":
            continue
        datos = shcp.rpu_saldos(DATA_RAW / f.archivo())
        usadas.add(f.id)
        for mid, s in datos.items():
            report.chequeo("periodo", quarter_of(s.fecha) == f.periodo, fuente=f.id, municipio=mid)
            if quarter_of(s.fecha) != f.periodo:
                report.error(f"{f.id}: el cuadro dice {s.fecha}, se esperaba {f.periodo}")
            saldos[mid].append(
                {
                    "periodo": f.periodo,
                    "fecha": s.fecha.isoformat(),
                    "total": s.total,
                    "banca_multiple": s.banca_multiple,
                    "banca_desarrollo": s.banca_desarrollo,
                    "emisiones": s.emisiones,
                    "otros": s.otros,
                    "fuente": f.id,
                }
            )
    registro_f = cfg.fuente("shcp-rpu-registro")
    creditos = shcp.rpu_registro(DATA_RAW / registro_f.archivo())
    usadas.add(registro_f.id)

    alertas: dict[str, list[dict]] = defaultdict(list)
    for f in cfg.fuentes:
        if f.tipo != "shcp_alertas":
            continue
        titulo, res = shcp.alertas(DATA_RAW / f.archivo())
        usadas.add(f.id)
        for mid in MUNICIPIOS:
            a = res.get(mid)
            alertas[mid].append(
                {
                    "evaluacion": titulo,
                    "resultado": a.resultado if a else None,
                    "etiqueta": shcp.ETIQUETAS_ALERTA.get(a.resultado) if a and a.resultado else None,
                    "indicadores": a.indicadores if a else [None, None, None],
                    "nota": (a.nota if a else "El municipio no aparece en esta evaluación."),
                    "fuente": f.id,
                }
            )

    anual_mty = []
    f_mty = cfg.fuente("mty-deuda-total")
    for d in mty_deuda.parse(DATA_RAW / f_mty.archivo()):
        if d.anio >= 2018:
            anual_mty.append(
                {
                    "anio": d.anio,
                    "amortizacion": d.amortizacion,
                    "intereses": d.intereses,
                    "gastos": d.gastos,
                    "total": d.total,
                }
            )
    usadas.add(f_mty.id)

    for mid in MUNICIPIOS:
        serie = sorted(saldos[mid], key=lambda x: x["periodo"])
        pagos = [
            {
                "periodo": pid,
                "montos": next((c["montos"] for c in p["capitulos"] if c["clave"] == "9000"), None),
                "fuente": p["fuente"],
            }
            for pid, p in sorted(egresos[mid].items())
        ]
        mis_creditos = [
            {k: v for k, v in c.__dict__.items() if k != "municipio"} for c in creditos if c.municipio == mid
        ]
        vigentes = [c for c in mis_creditos if c["saldo"]]
        # Cross-check: loan-by-loan sum vs. the quarterly table for the same date.
        if vigentes and serie:
            fecha = vigentes[0]["saldo_fecha"]
            trimestral = next((s for s in serie if s["fecha"] == fecha), None)
            suma = sum(c["saldo"] for c in vigentes)
            if trimestral and trimestral["total"]:
                ok = abs(suma - trimestral["total"]) / trimestral["total"] <= 0.01
                msg = (
                    f"{mid}: suma de créditos del registro ({suma:,.0f}) ≠ saldo trimestral "
                    f"({trimestral['total']:,.0f}); el registro solo incluye créditos vigentes a la fecha de consulta"
                )
                report.chequeo("cruce_creditos", ok, fuente=registro_f.id, municipio=mid, detalle=msg)
                if not ok:
                    report.advertencia(msg, fuente=registro_f.id, municipio=mid)
        # Cross-check (Monterrey): the drop in the SHCP balance vs. the amortisation reported by the municipality.
        if mid == "monterrey":
            por_fecha = {s["periodo"]: s["total"] for s in serie}
            for d in anual_mty:
                ini, fin = por_fecha.get(f"{d['anio'] - 1}T4"), None
                for q in (4, 3, 2, 1):
                    if f"{d['anio']}T{q}" in por_fecha:
                        fin = por_fecha[f"{d['anio']}T{q}"]
                        break
                if ini is None or fin is None or d["amortizacion"] <= 0:
                    continue
                baja = ini - fin
                ok = abs(baja - d["amortizacion"]) <= max(1_000.0, 0.01 * d["amortizacion"])
                msg = (
                    f"monterrey {d['anio']}: la baja del saldo en el RPU ({baja:,.2f}) frente a la "
                    f"amortización reportada por el municipio ({d['amortizacion']:,.2f})"
                )
                report.chequeo("cruce_amortizacion", ok, fuente=f_mty.id, municipio="monterrey", detalle=msg)
                if not ok:
                    report.advertencia(msg, fuente=f_mty.id, municipio="monterrey")
        _write(
            out_dir / "deuda" / f"{mid}.json",
            {
                "municipio": mid,
                "unidad": "MXN",
                "saldos": serie,
                "creditos": mis_creditos,
                "fuente_creditos": registro_f.id,
                "nota_creditos": (
                    "Créditos inscritos en el Registro Público Único a la fecha de consulta. Los créditos ya "
                    "liquidados salen del registro, por lo que la suma puede diferir del saldo trimestral."
                ),
                "pagos_capitulo_9000": pagos,
                "nota_pagos": (
                    "Capítulo 9000 'Deuda pública' del gasto: incluye pago de capital (amortización), intereses "
                    "y otros costos de la deuda. Acumulado de enero a la fecha de corte."
                ),
                "anual_detalle": anual_mty if mid == "monterrey" else [],
                "fuente_anual_detalle": f_mty.id if mid == "monterrey" else None,
                "alertas": alertas[mid],
                "nota_alertas": (
                    "Sistema de Alertas de la SHCP. Indicador 1: deuda y obligaciones ÷ ingresos de libre "
                    "disposición. Indicador 2: servicio de la deuda ÷ ingresos de libre disposición. Indicador 3: "
                    "obligaciones de corto plazo y proveedores, menos efectivo ÷ ingresos totales."
                ),
            },
            report,
            out_dir,
        )


# --- Contracts -----------------------------------------------------------------------------------

CATEGORIAS = {
    "licitacion": "Licitación pública",
    "invitacion": "Invitación restringida",
    "directa": "Adjudicación directa o por excepción",
    "modificatorio": "Convenio modificatorio",
    "otro": "Otro",
}


NOTAS_CONTRATOS = {
    "monterrey": [
        "Fuente: formato de transparencia NLA95FXXIX (adjudicaciones directas, invitaciones y licitaciones). "
        "En varios contratos el municipio clasificó como reservado el nombre del proveedor."
    ],
    "san-pedro": [
        "Fuente: relación de contratos de adquisiciones y servicios de la administración 2024–2027. "
        "No incluye contratos de obra pública (se publican aparte, en su portal de obra)."
    ],
    "santa-catarina": [
        "Fuente: formato de transparencia NLA95FXXIX de la Dirección de Adquisiciones. Solo se encontraron "
        "invitaciones y licitaciones; no se encontraron adjudicaciones directas de 2025–2026 en formato abierto."
    ],
}


def _contratos_de(f, manifest: Manifest, intermedio_dir: Path) -> list[dict]:
    """Masked contract rows of one source (RFC of individuals already hidden by the parser).

    The original is not archived because it contains personal data. When it is present (after 'fetch') it is parsed
    and its rows are saved as the committed intermediate; otherwise the intermediate is used, and it must belong to
    the exact original recorded in the manifest (same SHA-256)."""
    sha = (manifest.get(f.id) or {}).get("sha256")
    ruta = intermedio_dir / "contratos" / f"{f.id}.json"
    original = DATA_RAW / f.archivo()
    if original.exists():
        parser = contratos_mod.parse_san_pedro if f.tipo == "sp_contratos" else contratos_mod.parse_sipot_xxix
        filas = [dict(c.__dict__) for c in parser(original)]
        ruta.parent.mkdir(parents=True, exist_ok=True)
        datos = {"fuente": f.id, "sha256_original": sha, "contratos": filas}
        ruta.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        return filas
    if not ruta.exists():
        raise ParseError(f"{f.id}: falta el original y su intermedio (ejecuta 'fetch')")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if datos.get("sha256_original") != sha:
        raise ParseError(f"{f.id}: el intermedio no corresponde al original del manifiesto (ejecuta 'fetch')")
    return datos["contratos"]


def _contratos(
    cfg, manifest: Manifest, intermedio_dir: Path, report: Reporte, out_dir: Path, usadas: set[str]
) -> dict[str, list[dict]]:
    todos: dict[str, list[dict]] = {}
    for mid in MUNICIPIOS:
        items: list[dict] = []
        fuentes = []
        for f in cfg.fuentes:
            if f.municipio != mid or f.tipo not in ("sipot_xxix", "sp_contratos"):
                continue
            for c in _contratos_de(f, manifest, intermedio_dir):
                items.append({**c, "fuente": f.id})
            fuentes.append(f.id)
            usadas.add(f.id)
        items.sort(key=lambda c: (c["fecha"] or "", c["monto"] or 0), reverse=True)
        con_monto = [c for c in items if c["monto"]]
        total = round_money(sum(c["monto"] for c in con_monto))
        por_cat: dict[str, dict] = {}
        for c in items:
            d = por_cat.setdefault(
                c["categoria"], {"nombre": CATEGORIAS[c["categoria"]], "n": 0, "monto": 0.0}
            )
            d["n"] += 1
            d["monto"] = round_money(d["monto"] + (c["monto"] or 0))
        prov: dict[str, dict] = {}
        for c in con_monto:
            if c["tipo_persona"] == "reservada":
                continue
            key = c["rfc"] or norm_label(c["proveedor"])
            d = prov.setdefault(key, {"proveedor": c["proveedor"], "rfc": c["rfc"], "n": 0, "monto": 0.0})
            d["n"] += 1
            d["monto"] = round_money(d["monto"] + c["monto"])
        top = sorted(prov.values(), key=lambda d: d["monto"], reverse=True)
        for d in top:
            d["porcentaje"] = round(d["monto"] / total, 4) if total else None
        top10 = round(sum(d["monto"] for d in top[:10]) / total, 4) if total else None
        _write(
            out_dir / "contratos" / f"{mid}.json",
            {
                "municipio": mid,
                "unidad": "MXN",
                "fuentes": fuentes,
                "resumen": {
                    "contratos": len(items),
                    "con_monto": len(con_monto),
                    "monto_total": total,
                    "proveedores": len(prov),
                    "reservados": sum(1 for c in items if c["tipo_persona"] == "reservada"),
                    "por_categoria": por_cat,
                    "proveedores_top": top[:15],
                    "concentracion_top10": top10,
                    "fechas": [
                        min((c["fecha"] for c in items if c["fecha"]), default=None),
                        max((c["fecha"] for c in items if c["fecha"]), default=None),
                    ],
                },
                "notas": [
                    *NOTAS_CONTRATOS.get(mid, []),
                    "Montos con impuestos incluidos, tal como los publica el municipio. Los contratos sin monto "
                    "publicado no se suman.",
                    "Solo se muestra el RFC de empresas (personas morales); el de personas físicas se oculta.",
                    "Los proveedores marcados como información reservada no se incluyen en la concentración.",
                ],
                "contratos": items,
            },
            report,
            out_dir,
        )
        todos[mid] = items
    return todos


# --- Recent changes ------------------------------------------------------------------------------


def _fmt(m: float) -> str:
    return f"${m / 1e6:,.1f} millones" if abs(m) >= 1e6 else f"${m:,.0f}"


def _movimientos(egresos, deuda_dir: Path, contratos: dict[str, list[dict]], report: Reporte, out_dir: Path):
    items: list[dict] = []
    for mid, periodos in egresos.items():
        nombre = MUNICIPIOS[mid]["nombre"]
        pids = sorted(periodos)
        if not pids:
            continue
        ult = periodos[pids[-1]]
        pid = ult["periodo"]
        # 1) New period against the same quarter of the previous year.
        prev_year = periodos.get(f"{int(pid[:4]) - 1}{pid[4:]}")
        cambio = (
            cambio_relativo(ult["total"]["devengado"], prev_year["total"]["devengado"]) if prev_year else None
        )
        items.append(
            {
                "fecha": ult["fecha_corte"],
                "municipio": mid,
                "tipo": "periodo",
                "titulo": f"{nombre} gastó {_fmt(ult['total']['devengado'])} de enero a {_mes(ult['fecha_corte'])}",
                "detalle": (
                    f"{cambio:+.0%} frente al mismo periodo de {int(pid[:4]) - 1}."
                    if cambio is not None
                    else "No hay dato comparable del año anterior."
                ),
                "monto": ult["total"]["devengado"],
                "cambio": cambio,
                "fuente": ult["fuente"],
            }
        )
        # 2) Mid-year changes (Ampliaciones/Reducciones) against the previous quarter of the same year.
        prev_q = periodos.get(pids[-2]) if len(pids) > 1 and pids[-2][:4] == pid[:4] else None
        base_ant = {}
        if prev_q:
            base_ant = {c["clave"]: c["montos"]["ampliaciones"] or 0 for c in prev_q["capitulos"]}
        lineas = [(c["nombre"], c["montos"], base_ant.get(c["clave"], 0.0)) for c in ult["capitulos"]]
        if ult["dependencias"]:
            ant_dep = {
                d["id"]: d["montos"]["ampliaciones"] or 0 for d in (prev_q or {}).get("dependencias") or []
            }
            lineas = [(d["nombre"], d["montos"], ant_dep.get(d["id"], 0.0)) for d in ult["dependencias"]]
        for nombre_l, montos, amp_ant in lineas:
            amp = montos.get("ampliaciones") or 0.0
            delta = amp - amp_ant
            apr = montos.get("aprobado") or 0.0
            if abs(delta) >= 50_000_000 or (apr > 0 and abs(delta) / apr > 0.2 and abs(delta) >= 10_000_000):
                verbo = "recibió" if delta > 0 else "perdió"
                items.append(
                    {
                        "fecha": ult["fecha_corte"],
                        "municipio": mid,
                        "tipo": "modificacion",
                        "titulo": f"{nombre_l} {verbo} {_fmt(abs(delta))} en cambios al presupuesto",
                        "detalle": (
                            f"{nombre}: presupuesto aprobado {_fmt(apr)}; modificado a {_mes(ult['fecha_corte'])}: "
                            f"{_fmt(montos.get('modificado') or 0)}."
                        ),
                        "monto": delta,
                        "cambio": None,
                        "fuente": ult["fuente_dependencias"] if ult["dependencias"] else ult["fuente"],
                    }
                )
    for mid in MUNICIPIOS:
        nombre = MUNICIPIOS[mid]["nombre"]
        d = json.loads((deuda_dir / f"{mid}.json").read_text(encoding="utf-8"))
        s = d["saldos"]
        if len(s) >= 2:
            a, b = s[-2], s[-1]
            delta = b["total"] - a["total"]
            if abs(delta) >= 1:
                items.append(
                    {
                        "fecha": b["fecha"],
                        "municipio": mid,
                        "tipo": "deuda",
                        "titulo": (
                            f"La deuda de {nombre} {'bajó' if delta < 0 else 'subió'} {_fmt(abs(delta))} "
                            f"en el trimestre"
                        ),
                        "detalle": f"Saldo registrado al {b['fecha']}: {_fmt(b['total'])}.",
                        "monto": delta,
                        "cambio": cambio_relativo(b["total"], a["total"]),
                        "fuente": b["fuente"],
                    }
                )
        al = [x for x in d["alertas"] if x["resultado"]]
        if len(al) >= 2 and al[-1]["resultado"] != al[-2]["resultado"]:
            items.append(
                {
                    "fecha": None,
                    "municipio": mid,
                    "tipo": "alerta",
                    "titulo": f"Cambió la calificación de deuda de {nombre}: {al[-1]['etiqueta']}",
                    "detalle": al[-1]["evaluacion"],
                    "monto": None,
                    "cambio": None,
                    "fuente": al[-1]["fuente"],
                }
            )
    for mid, cs in contratos.items():
        nombre = MUNICIPIOS[mid]["nombre"]
        fechas = [c["fecha"] for c in cs if c["fecha"]]
        if not fechas:
            continue
        ultima = max(fechas)
        desde = f"{int(ultima[:4]) - (1 if int(ultima[5:7]) <= 3 else 0)}-{(int(ultima[5:7]) - 4) % 12 + 1:02d}-01"
        recientes = sorted(
            (c for c in cs if c["fecha"] and c["fecha"] >= desde and c["monto"]),
            key=lambda c: c["monto"],
            reverse=True,
        )[:3]
        for c in recientes:
            items.append(
                {
                    "fecha": c["fecha"],
                    "municipio": mid,
                    "tipo": "contrato",
                    "titulo": f"Contrato de {_fmt(c['monto'])}: {c['descripcion'][:90]}".rstrip(),
                    "detalle": f"{nombre} · {c['proveedor']} · {c['procedimiento']}",
                    "monto": c["monto"],
                    "cambio": None,
                    "fuente": c["fuente"],
                }
            )
    items.sort(key=lambda x: (x["fecha"] or "", abs(x["monto"] or 0)), reverse=True)
    _write(out_dir / "movimientos.json", {"movimientos": items}, report, out_dir)


_MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def _mes(iso: str) -> str:
    return f"{_MESES[int(iso[5:7]) - 1]} de {iso[:4]}"


# --- Main ----------------------------------------------------------------------------------------


def build(out_dir: Path = PUBLIC_V1, intermedio_dir: Path = DATA_INTERMEDIO) -> Reporte:
    cfg = sources_mod.load()
    manifest = Manifest(DATA_RAW / "manifest.json")
    report = Reporte()

    def disponible(f) -> bool:
        if (DATA_RAW / f.archivo()).exists():
            return True
        # Not archived (personal data): its masked intermediate stands in for it.
        return f.tipo in sources_mod.SIN_COPIA and (intermedio_dir / "contratos" / f"{f.id}.json").exists()

    faltan_archivos = [f.id for f in cfg.fuentes if manifest.get(f.id) is None or not disponible(f)]
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
                msg = (
                    f"{mid} {anio_rec['anio']}: devengado 4T ({dev:,.0f}) difiere {rel:+.1%} del gasto anual "
                    f"del INEGI ({anio_rec['gasto_total']:,.0f})"
                )
                ok = rel is not None and abs(rel) <= 0.02
                report.chequeo("cruce_inegi", ok, fuente=p4["fuente"], municipio=mid, detalle=msg)
                if not ok:
                    report.advertencia(msg, fuente=p4["fuente"], municipio=mid)

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

    try:
        _deuda(cfg, egresos, report, out_dir, fuentes_usadas)
        contratos = _contratos(cfg, manifest, intermedio_dir, report, out_dir, fuentes_usadas)
    except ParseError as exc:
        report.error(f"error al leer un original de deuda o contratos: {exc}")
        return report
    _movimientos(egresos, out_dir / "deuda", contratos, report, out_dir)

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

    # Documents cited by a warning or a failed check are listed too, so every inconsistency links to its original.
    fuentes_usadas.update(a["fuente"] for a in report.advertencias_det if a["fuente"])
    fuentes_usadas.update(x["fuente"] for c in report.chequeos.values() for x in c.fallas if x["fuente"])
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
            # Archived copy of the exact file used, served by the site itself (/data/originales/…).
            # Not archived when the original contains personal data: only its link and fingerprint are published.
            "copia": None
            if f.tipo in sources_mod.SIN_COPIA
            else f"/data/originales/{f.archivo().as_posix()}",
            "sin_copia": (
                "Contiene RFC de personas físicas; descárgalo del sitio oficial y compara su huella SHA-256."
                if f.tipo in sources_mod.SIN_COPIA
                else None
            ),
            "extracto": f.tipo in sources_mod.EXTRACTOS,
            "sha256_original": m.get("sha256_original"),
            "bytes": m.get("bytes")
            or ((DATA_RAW / f.archivo()).stat().st_size if (DATA_RAW / f.archivo()).exists() else None),
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

    _write(
        out_dir / "validacion.json",
        {
            "chequeos": [
                {
                    "id": clave,
                    "descripcion": CHEQUEOS[clave],
                    "revisados": c.revisados,
                    "aprobados": c.aprobados,
                    "fallas": c.fallas,
                }
                for clave, c in sorted(report.chequeos.items(), key=lambda kv: list(CHEQUEOS).index(kv[0]))
            ],
            "advertencias": report.advertencias_det,
            "nota": (
                "Las advertencias son inconsistencias dentro de los documentos oficiales o diferencias entre fuentes. "
                "Las cifras se publican tal como aparecen en el documento; no se corrigen ni se estiman."
            ),
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
