"""Markdown summary for the data-refresh PR (from the fetch, discover and build reports)."""

from __future__ import annotations

import json
from pathlib import Path

from gdmty.paths import CACHE_DIR, PUBLIC_V1


def generar(cache: Path = CACHE_DIR) -> str:
    def cargar(nombre: str, defecto):
        p = cache / nombre
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else defecto

    fetch = cargar("fetch-report.json", [])
    build = cargar("build-report.json", {})
    desc = cargar("discover-report.json", {})
    meta = (
        json.loads((PUBLIC_V1 / "meta.json").read_text(encoding="utf-8"))
        if (PUBLIC_V1 / "meta.json").exists()
        else {}
    )

    por_estado: dict[str, list[dict]] = {}
    for r in fetch:
        por_estado.setdefault(r["estado"], []).append(r)
    lineas = ["## Actualización automática de datos", ""]
    if meta:
        lineas += [
            f"Periodo más reciente: **{meta.get('periodo_mas_reciente')}** · datos al {meta.get('datos_al')}.",
            "",
        ]

    if por_estado.get("modificado"):
        lineas += [
            "### ⚠️ Fuente modificada",
            "",
            "Estos documentos **ya descargados cambiaron en el sitio oficial**. Compara con el original anterior "
            "(hash en `data/raw/manifest.json`, historial) antes de aprobar:",
            "",
        ]
        lineas += [f"- `{r['id']}`" for r in por_estado["modificado"]] + [""]
    if desc.get("nuevas") or por_estado.get("nuevo"):
        lineas += ["### Documentos nuevos", ""]
        lineas += [f"- `{x['id']}` — {x['titulo']}" for x in desc.get("nuevas", [])]
        lineas += [
            f"- `{r['id']}`"
            for r in por_estado.get("nuevo", [])
            if r["id"] not in {x["id"] for x in desc.get("nuevas", [])}
        ]
        lineas.append("")
    if desc.get("actualizadas"):
        lineas += ["### URLs actualizadas", ""] + [f"- {x}" for x in desc["actualizadas"]] + [""]
    if build.get("anomalias"):
        lineas += ["### Cambios grandes (±30 % vs. el mismo trimestre del año anterior) — verificar", ""]
        lineas += [f"- {a}" for a in build["anomalias"]] + [""]
    if build.get("advertencias"):
        lineas += [
            "<details><summary>Advertencias de validación (inconsistencias en documentos oficiales)</summary>",
            "",
        ]
        lineas += [f"- {a}" for a in build["advertencias"]] + ["", "</details>", ""]
    if por_estado.get("error"):
        lineas += ["### Fuentes que no se pudieron descargar", ""]
        lineas += [f"- `{r['id']}`: {r['detalle']}" for r in por_estado["error"]] + [""]
    if desc.get("manuales"):
        lineas += ["### Revisar manualmente", ""] + [f"- {x}" for x in desc["manuales"]] + [""]
    lineas += [
        "---",
        "La validación completa (pruebas del pipeline, reconstrucción determinista y compilación del sitio) ya se "
        "ejecutó antes de abrir este PR. Usa la lista de verificación de datos de la plantilla antes de aprobar.",
    ]
    return "\n".join(lineas) + "\n"
