"""Discover new official documents (new quarters) and add them to sources.yaml.

Only predictable or listed sources are discovered automatically. Anything else goes to the
"revisar manualmente" list in the PR summary. New entries are never published without the PR review.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import httpx
import yaml

from gdmty import sources as sources_mod
from gdmty.paths import SOURCES_FILE
from gdmty.safeio import TIMEOUT, USER_AGENT, UnsafeInputError, download, ssl_context

Q_ORD = {1: "1er", 2: "2º", 3: "3er", 4: "4º"}
Q_FOLDER = {1: "1erTrimestre", 2: "2doTrimestre", 3: "3erTrimestre", 4: "4toTrimestre"}
SHCP = "https://www.disciplinafinanciera.hacienda.gob.mx/work/models/DISCIPLINA_FINANCIERA"
MTY_TES = "https://www.monterrey.gob.mx/pdf/tesoreria"
MTY_PAGINA = "https://www.monterrey.gob.mx/transparencia/Oficial_/Informacion_Fiscal/"
SP_LISTA = (
    "https://transparencia.sanpedro.gob.mx/transparencia/descFraccion.aspx?articuloId=1&fraccionid=28"
    "&area=5302&idDireccion=0&inc=True"
)


@dataclass
class Descubrimiento:
    nuevas: list[dict] = field(default_factory=list)
    actualizadas: list[str] = field(default_factory=list)
    manuales: list[str] = field(default_factory=list)


def _siguientes(ultimo: str, hasta: date) -> list[str]:
    """Quarters after `ultimo` whose cut-off date has already passed."""
    y, q = int(ultimo[:4]), int(ultimo[-1])
    out = []
    while True:
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
        corte = date(y, q * 3, 28)
        if corte > hasta:
            return out
        out.append(f"{y}T{q}")


def _existe(client: httpx.Client, url: str, dominios: list[str]) -> bool:
    try:
        download(url, dominios, client=client, max_bytes=60 * 1024 * 1024)
        return True
    except (httpx.HTTPError, UnsafeInputError):
        return False


def _q(url: str) -> str:
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, quote(unquote(p.path), safe="/%()"), p.query, ""))


def descubrir(hoy: date | None = None) -> Descubrimiento:
    hoy = hoy or datetime.now(UTC).date()
    cfg = sources_mod.load()
    ids = {f.id for f in cfg.fuentes}
    d = Descubrimiento()
    client = httpx.Client(
        verify=ssl_context(), timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": USER_AGENT}
    )
    dom = cfg.dominios_permitidos
    try:
        # --- Monterrey: quarterly statements (predictable names since 2025) -------------------
        ult = max(
            f.periodo for f in cfg.fuentes if f.municipio == "monterrey" and f.tipo == "mty_egresos_objeto"
        )
        for pid in _siguientes(ult, hoy):
            y, q = pid[:4], pid[-1]
            candidatos = {
                f"mty-ing-{pid}": (
                    "mty_ingresos",
                    f"{y}/1_Estado_Analitico_de_Ingresos_{q}T_{y}.xlsx",
                    "Estado Analítico de Ingresos",
                ),
                f"mty-egr-adm-{pid}": (
                    "mty_egresos_administrativa",
                    f"{y}/3_Estado_Analitico_del_Ejercicio_del_PE_Clasificacion_Administrativa_Municipal_{q}T_{y}.xlsx",
                    "Estado Analítico del Ejercicio del Presupuesto de Egresos — Clasificación Administrativa",
                ),
                f"mty-egr-obj-{pid}": (
                    "mty_egresos_objeto",
                    f"{y}/5_Estado_Analitico_del_Ejercicio_del_PE_Clasificacion_Objeto_del_Gasto_{q}T_{y}.xlsx",
                    "Estado Analítico del Ejercicio del Presupuesto de Egresos — Clasificación por Objeto del Gasto",
                ),
            }
            encontrados = {
                k: v
                for k, v in candidatos.items()
                if k not in ids and _existe(client, f"{MTY_TES}/{v[1]}", dom)
            }
            if len(encontrados) < len([k for k in candidatos if k not in ids]):
                if encontrados:
                    d.manuales.append(
                        f"Monterrey {pid}: solo se encontraron {sorted(encontrados)}; revisa los nombres de archivo."
                    )
                if not encontrados:
                    continue
            for k, (tipo, path, titulo) in encontrados.items():
                d.nuevas.append(
                    {
                        "id": k,
                        "municipio": "monterrey",
                        "tipo": tipo,
                        "periodo": pid,
                        "titulo": f"{titulo}, {Q_ORD[int(q)]} trimestre {y} (acumulado)",
                        "emisor": "Municipio de Monterrey — Tesorería Municipal",
                        "url": _q(f"{MTY_TES}/{path}"),
                        "pagina": MTY_PAGINA,
                        "formato": "xlsx",
                    }
                )

        # --- San Pedro: NLA95FXXIIB listing ---------------------------------------------------
        try:
            page = download(SP_LISTA, dom, client=client).content.decode("utf-8", "ignore")
            conocidas = {f.url for f in cfg.fuentes if f.municipio == "san-pedro"}
            for path, y, mes in sorted(
                set(re.findall(r"(/1/30/(20\d\d)/(\d+)/5302/[^'\"<>]+?\.xlsx)", page))
            ):
                url = _q(
                    "https://transparencia.sanpedro.gob.mx/documentosTransparencia" + html.unescape(path)
                )
                pid = f"{y}T{(int(mes) + 2) // 3}"
                sid = f"sp-xxiib-{pid}"
                if int(y) >= 2023 and url not in conocidas and sid not in ids:
                    d.nuevas.append(
                        {
                            "id": sid,
                            "municipio": "san-pedro",
                            "tipo": "sipot_xxiib",
                            "periodo": pid,
                            "titulo": f"Formato NLA95FXXIIB — Ejercicio de los egresos presupuestarios, {Q_ORD[int(pid[-1])]} trimestre {y}",
                            "emisor": "Municipio de San Pedro Garza García — Secretaría de Finanzas y Tesorería",
                            "url": url,
                            "pagina": SP_LISTA,
                            "formato": "xlsx",
                        }
                    )
                    ids.add(sid)
        except (httpx.HTTPError, UnsafeInputError) as exc:
            d.manuales.append(f"San Pedro: no se pudo leer la lista de la fracción XXII ({exc}).")

        # --- SHCP: registered balances by municipality (index page per year) ----------------------
        ult_rpu = max(f.periodo for f in cfg.fuentes if f.tipo == "shcp_rpu_saldos")
        for pid in _siguientes(ult_rpu, hoy):
            y, q = pid[:4], int(pid[-1])
            url = f"{SHCP}/Indicadores_de_Obligaciones/{y}/{Q_FOLDER[q]}/02_04_{q}_trim_{y}.xlsx"
            if f"shcp-rpu-saldos-{pid}" not in ids and _existe(client, url, dom):
                d.nuevas.append(
                    {
                        "id": f"shcp-rpu-saldos-{pid}",
                        "municipio": None,
                        "tipo": "shcp_rpu_saldos",
                        "periodo": pid,
                        "titulo": f"Registro Público Único — saldos de financiamientos y obligaciones por municipio, {Q_ORD[q]} trimestre {y} (millones de pesos)",
                        "emisor": "SHCP — Unidad de Coordinación con Entidades Federativas",
                        "url": url,
                        "pagina": f"https://www.disciplinafinanciera.hacienda.gob.mx/es/DISCIPLINA_FINANCIERA/{y}",
                        "formato": "xlsx",
                    }
                )

        # --- SHCP: Sistema de Alertas (next evaluations) -------------------------------------------
        for y in (hoy.year - 1, hoy.year):
            for ev, lab in (("1S", "1er semestre"), ("2S", "2º semestre"), ("CP", "Cuenta Pública")):
                sid = f"shcp-alertas-{y}-{ev.lower()}"
                url = (
                    f"{SHCP}/Documentos/SistemaAlertas/{y}/Municipio/{ev}/Resultados%20SdA%20municipios.xlsx"
                )
                if sid not in ids and _existe(client, url, dom):
                    d.nuevas.append(
                        {
                            "id": sid,
                            "municipio": None,
                            "tipo": "shcp_alertas",
                            "periodo": None,
                            "titulo": f"Sistema de Alertas — resultados de municipios, evaluación {lab} {y}",
                            "emisor": "SHCP — Unidad de Coordinación con Entidades Federativas",
                            "url": url,
                            "pagina": "https://www.disciplinafinanciera.hacienda.gob.mx/es/DISCIPLINA_FINANCIERA/Sistema_de_Alertas",
                            "formato": "xlsx",
                        }
                    )

        # --- Monterrey: cumulative contracts file for the year (the month in the name changes) ------
        for y in (hoy.year,):
            sid = f"mty-contratos-{y}"
            actual = next((f for f in cfg.fuentes if f.id == sid), None)
            for mes in range(hoy.month, 0, -1):
                url = f"https://www.monterrey.gob.mx/pdf/portaln/{y}/MTY_{y}_{mes:02d}_FORMATO_95_XXIX.xlsx"
                if actual is not None and actual.url == url:
                    break
                if _existe(client, url, dom):
                    if actual is None:
                        d.nuevas.append(
                            {
                                "id": sid,
                                "municipio": "monterrey",
                                "tipo": "sipot_xxix",
                                "periodo": None,
                                "titulo": f"Formato NLA95FXXIX — resultados de adjudicaciones, invitaciones y licitaciones, {y} (acumulado del año)",
                                "emisor": "Municipio de Monterrey",
                                "url": url,
                                "pagina": "https://www.monterrey.gob.mx/transparencia/Oficial_/",
                                "formato": "xlsx",
                            }
                        )
                    else:
                        _actualizar_url(sid, url)
                        d.actualizadas.append(f"{sid}: {url}")
                    break

        # --- Monterrey: debt series (the quarter is in the name) ---------------------------------
        deuda = next((f for f in cfg.fuentes if f.id == "mty-deuda-total"), None)
        if deuda:
            m = re.search(r"_(\d)T_(\d{4})\.xlsx$", deuda.url)
            if m:
                for pid in _siguientes(f"{m.group(2)}T{m.group(1)}", hoy):
                    y, q = pid[:4], pid[-1]
                    url = (
                        f"https://www.monterrey.gob.mx/pdf/portaln/ITDIF/4_Deuda_total_2014_{y}_{q}T_{y}.xlsx"
                    )
                    if _existe(client, url, dom):
                        _actualizar_url("mty-deuda-total", url)
                        d.actualizadas.append(f"mty-deuda-total: {url}")
    finally:
        client.close()

    d.manuales += [
        "Santa Catarina: revisar en su portal (Transparencia → Artículo 95 → fracción XXII y XXIX) si hay "
        "archivos nuevos y agregarlos a sources.yaml.",
        "San Pedro: revisar si la relación de contratos en licitaciones.sanpedro.gob.mx tiene una versión nueva.",
    ]
    if d.nuevas:
        _agregar(d.nuevas)
    return d


def _cargar_texto(path: Path) -> tuple[str, dict]:
    text = path.read_text(encoding="utf-8")
    return text.split("version:", 1)[0], yaml.safe_load(text)


def _guardar(path: Path, header: str, doc: dict) -> None:
    path.write_text(
        header + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=140), encoding="utf-8"
    )
    sources_mod.load(path)  # validate the result


def _agregar(nuevas: list[dict], path: Path = SOURCES_FILE) -> None:
    header, doc = _cargar_texto(path)
    doc["fuentes"].extend(nuevas)
    _guardar(path, header, doc)


def _actualizar_url(fid: str, url: str, path: Path = SOURCES_FILE) -> None:
    header, doc = _cargar_texto(path)
    for f in doc["fuentes"]:
        if f["id"] == fid:
            f["url"] = url
    _guardar(path, header, doc)
