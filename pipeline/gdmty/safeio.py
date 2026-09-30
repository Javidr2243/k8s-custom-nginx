"""Safe input/output for untrusted files downloaded from government sites.

Guarantees:
- Only HTTPS to domains on the allowlist, re-checked after **every** redirect.
- TLS always verified (system store + the intermediates in pipeline/certs/). Never ``verify=False``.
- Limits on size, time and number of redirects.
- File type checked by its **magic bytes**, not by extension or Content-Type.
- ZIPs extracted with limits on total size, number of entries and paths (no zip bombs or ``../``).
"""

from __future__ import annotations

import hashlib
import ssl
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin, urlsplit

import httpx

from gdmty.paths import CERTS_FILE

MAX_BYTES_DEFAULT = 150 * 1024 * 1024  # 150 MB
MAX_REDIRECTS = 5
TIMEOUT = httpx.Timeout(connect=20.0, read=120.0, write=20.0, pool=20.0)
USER_AGENT = "adonde-va-tu-dinero-mty/0.1 (+https://github.com/javidr2243/k8s-custom-nginx)"


class UnsafeInputError(Exception):
    """An input broke a safety rule (domain, size, type, path)."""


# --- File types by magic bytes -------------------------------------------------------------------

_MAGIC: dict[str, tuple[bytes, ...]] = {
    "xlsx": (b"PK\x03\x04",),
    "zip": (b"PK\x03\x04",),
    "xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    "pdf": (b"%PDF-",),
}


def sniff_type(data: bytes) -> str:
    """Return the real file type: xlsx, zip, xls, pdf, json, csv/text, html or unknown."""
    head = data[:2048]
    if head.startswith(b"PK\x03\x04"):
        return "xlsx" if b"[Content_Types].xml" in data[:65536] or b"xl/" in data[:65536] else "zip"
    if head.startswith(_MAGIC["xls"][0]):
        return "xls"
    if head.startswith(b"%PDF-"):
        return "pdf"
    stripped = head.lstrip(b"\xef\xbb\xbf \t\r\n")
    if stripped[:1] in (b"{", b"["):
        return "json"
    lower = stripped[:512].lower()
    if lower.startswith((b"<!doctype html", b"<html")) or b"<html" in lower:
        return "html"
    try:
        head.decode("utf-8")
        return "text"
    except UnicodeDecodeError:
        try:
            head.decode("latin-1")
            return "text"
        except UnicodeDecodeError:  # pragma: no cover - latin-1 decodes any byte sequence
            return "unknown"


def check_type(data: bytes, expected: str) -> None:
    """Fail if the content is not of the expected type (csv/text are equivalent)."""
    actual = sniff_type(data)
    ok = actual == expected or (expected in ("csv", "text") and actual == "text")
    ok = ok or (expected == "zip" and actual == "xlsx")  # an xlsx is a zip
    if not ok:
        raise UnsafeInputError(f"se esperaba '{expected}' pero el contenido es '{actual}'")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --- Downloads -----------------------------------------------------------------------------------


def ssl_context(extra_certs: Path | None = CERTS_FILE) -> ssl.SSLContext:
    """System store + intermediates. Hostname verification and certificate checks enabled."""
    ctx = ssl.create_default_context()
    if extra_certs is not None and extra_certs.exists():
        ctx.load_verify_locations(cafile=str(extra_certs))
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def _check_url(url: str, allowed_domains: Iterable[str]) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise UnsafeInputError(f"solo se permite https: {url}")
    host = (parts.hostname or "").lower()
    if host not in {d.lower() for d in allowed_domains}:
        raise UnsafeInputError(f"dominio no permitido: {host}")
    if parts.username or parts.password:
        raise UnsafeInputError("URL con credenciales no permitida")


@dataclass(frozen=True)
class Download:
    url: str
    final_url: str
    content: bytes
    last_modified: str | None
    content_type: str | None


def download(
    url: str,
    allowed_domains: Iterable[str],
    *,
    method: str = "GET",
    data: dict[str, str] | None = None,
    max_bytes: int = MAX_BYTES_DEFAULT,
    client: httpx.Client | None = None,
) -> Download:
    """Download a URL, following redirects by hand so every hop is checked against the allowlist."""
    allowed = list(allowed_domains)
    own_client = client is None
    if client is None:
        client = httpx.Client(
            verify=ssl_context(),
            timeout=TIMEOUT,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
        )
    try:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            _check_url(current, allowed)
            with client.stream(method, current, data=data) as resp:
                if resp.is_redirect:
                    location = resp.headers.get("location")
                    if not location:
                        raise UnsafeInputError("redirección sin Location")
                    current = urljoin(current, location)
                    method, data = "GET", None
                    continue
                resp.raise_for_status()
                declared = resp.headers.get("content-length")
                if declared is not None and declared.isdigit() and int(declared) > max_bytes:
                    raise UnsafeInputError(f"archivo demasiado grande ({declared} bytes)")
                buf = bytearray()
                for chunk in resp.iter_bytes():
                    buf.extend(chunk)
                    if len(buf) > max_bytes:
                        raise UnsafeInputError(f"archivo demasiado grande (> {max_bytes} bytes)")
                return Download(
                    url=url,
                    final_url=current,
                    content=bytes(buf),
                    last_modified=resp.headers.get("last-modified"),
                    content_type=resp.headers.get("content-type"),
                )
        raise UnsafeInputError(f"demasiadas redirecciones (> {MAX_REDIRECTS})")
    finally:
        if own_client:
            client.close()


# --- Safe ZIP extraction -------------------------------------------------------------------------


def safe_zip_members(
    zip_path: Path,
    *,
    max_total_bytes: int = 2 * 1024**3,
    max_members: int = 500,
    max_ratio: int = 200,
) -> list[zipfile.ZipInfo]:
    """Validate a ZIP without extracting it: size, number of entries, compression ratio and paths."""
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        if len(infos) > max_members:
            raise UnsafeInputError(f"ZIP con demasiadas entradas ({len(infos)})")
        total = 0
        for info in infos:
            name = PurePosixPath(info.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in info.filename:
                raise UnsafeInputError(f"ruta peligrosa en ZIP: {info.filename}")
            total += info.file_size
            if info.compress_size and info.file_size / info.compress_size > max_ratio:
                raise UnsafeInputError(f"tasa de compresión sospechosa en {info.filename}")
        if total > max_total_bytes:
            raise UnsafeInputError(f"ZIP descomprimido demasiado grande ({total} bytes)")
        return infos
