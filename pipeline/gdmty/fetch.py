"""Download the sources declared in sources.yaml into data/raw/ and update the manifest.

- An already-downloaded file that has not changed is left untouched (no noise in the diff).
- A file that CHANGED upstream is reported as 'modificado' (the PR shows it prominently).
- A source that fails (site down, 404) does not stop the others; it is reported as an error.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

from gdmty import sources as sources_mod
from gdmty.manifest import Manifest
from gdmty.parsers import efipem
from gdmty.paths import CACHE_DIR, DATA_RAW
from gdmty.safeio import (
    TIMEOUT,
    USER_AGENT,
    UnsafeInputError,
    check_type,
    download,
    sha256_bytes,
    sha256_file,
)
from gdmty.safeio import ssl_context as make_ssl_context


@dataclass
class Resultado:
    id: str
    estado: str  # nuevo | sin_cambios | modificado | error
    detalle: str = ""


def _fecha_http(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return None


def fetch(
    only: str | None = None, *, raw_dir: Path = DATA_RAW, report_path: Path | None = None
) -> list[Resultado]:
    cfg = sources_mod.load()
    manifest = Manifest(raw_dir / "manifest.json")
    hoy = datetime.now(UTC).date().isoformat()
    resultados: list[Resultado] = []
    client = httpx.Client(
        verify=make_ssl_context(), timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": USER_AGENT}
    )
    try:
        for f in cfg.fuentes:
            if only and not f.id.startswith(only):
                continue
            try:
                dl = download(f.url, cfg.dominios_permitidos, client=client)
                check_type(dl.content, f.formato)
                destino = raw_dir / f.archivo()
                destino.parent.mkdir(parents=True, exist_ok=True)
                entry = {
                    "url": f.url,
                    "archivo": f.archivo().as_posix(),
                    "publicado": _fecha_http(dl.last_modified),
                    "descargado": hoy,
                }
                if f.tipo == "inegi_efipem":
                    # Large original: keep its hash and store only the extract.
                    entry["sha256_original"] = sha256_bytes(dl.content)
                    entry["bytes_original"] = len(dl.content)
                    with tempfile.TemporaryDirectory(dir=_cache_dir()) as tmp:
                        zpath = Path(tmp) / "efipem.zip"
                        zpath.write_bytes(dl.content)
                        extract_tmp = Path(tmp) / "extract.csv"
                        entry["filas"] = efipem.extract(zpath, extract_tmp)
                        entry["sha256"] = sha256_file(extract_tmp)
                        estado = manifest.record(f.id, entry)
                        if estado != "sin_cambios":
                            destino.write_bytes(extract_tmp.read_bytes())
                else:
                    entry["sha256"] = sha256_bytes(dl.content)
                    entry["bytes"] = len(dl.content)
                    estado = manifest.record(f.id, entry)
                    if estado != "sin_cambios" or not destino.exists():
                        destino.write_bytes(dl.content)
                resultados.append(Resultado(f.id, estado))
            except (httpx.HTTPError, UnsafeInputError, OSError, ValueError) as exc:
                resultados.append(Resultado(f.id, "error", f"{type(exc).__name__}: {exc}"))
    finally:
        client.close()
    manifest.save()
    report = report_path or _cache_dir() / "fetch-report.json"
    report.write_text(
        json.dumps([asdict(r) for r in resultados], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return resultados


def _cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR
