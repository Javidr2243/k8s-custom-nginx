"""Security cases for gdmty.safeio: nothing unexpected gets past it."""

import io
import zipfile
from pathlib import Path

import httpx
import pytest

from gdmty.safeio import UnsafeInputError, check_type, download, safe_zip_members, sniff_type

ALLOWED = ["www.monterrey.gob.mx"]


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def _xlsx_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("xl/workbook.xml", "<workbook/>")
    return buf.getvalue()


def test_sniff_types() -> None:
    assert sniff_type(_xlsx_bytes()) == "xlsx"
    assert sniff_type(b"%PDF-1.7 ...") == "pdf"
    assert sniff_type(b'{"a": 1}') == "json"
    assert sniff_type(b"<!DOCTYPE html><html>") == "html"
    assert sniff_type(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1rest") == "xls"


def test_pdf_disguised_as_xlsx_is_rejected() -> None:
    # Seen in the wild: a portal serves a PDF under an .xlsx URL.
    with pytest.raises(UnsafeInputError, match="pdf"):
        check_type(b"%PDF-1.4 fake", "xlsx")


def test_html_error_page_is_rejected() -> None:
    with pytest.raises(UnsafeInputError):
        check_type(b"<html><body>Not found</body></html>", "xlsx")


def test_download_rejects_http() -> None:
    with pytest.raises(UnsafeInputError, match="https"):
        download("http://www.monterrey.gob.mx/a.xlsx", ALLOWED, client=_client(lambda r: httpx.Response(200)))


def test_download_rejects_unlisted_domain() -> None:
    with pytest.raises(UnsafeInputError, match="dominio no permitido"):
        download("https://evil.example.com/a.xlsx", ALLOWED, client=_client(lambda r: httpx.Response(200)))


def test_redirect_to_unlisted_domain_is_blocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://evil.example.com/x.xlsx"})

    with pytest.raises(UnsafeInputError, match="dominio no permitido"):
        download("https://www.monterrey.gob.mx/a.xlsx", ALLOWED, client=_client(handler))


def test_redirect_loop_is_bounded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://www.monterrey.gob.mx/again"})

    with pytest.raises(UnsafeInputError, match="redirecciones"):
        download("https://www.monterrey.gob.mx/a.xlsx", ALLOWED, client=_client(handler))


def test_size_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 2048)

    with pytest.raises(UnsafeInputError, match="demasiado grande"):
        download("https://www.monterrey.gob.mx/a.xlsx", ALLOWED, max_bytes=1024, client=_client(handler))


def test_download_ok_follows_allowed_redirect() -> None:
    body = _xlsx_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/a.xlsx":
            return httpx.Response(301, headers={"location": "/b.xlsx"})
        return httpx.Response(200, content=body, headers={"last-modified": "Tue, 04 Aug 2026 10:00:00 GMT"})

    dl = download("https://www.monterrey.gob.mx/a.xlsx", ALLOWED, client=_client(handler))
    assert dl.content == body
    assert dl.final_url.endswith("/b.xlsx")


def test_zip_path_traversal_is_rejected(tmp_path: Path) -> None:
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("../../etc/passwd", "x")
    with pytest.raises(UnsafeInputError, match="ruta peligrosa"):
        safe_zip_members(z)


def test_zip_bomb_is_rejected(tmp_path: Path) -> None:
    z = tmp_path / "bomb.zip"
    with zipfile.ZipFile(z, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.csv", b"0" * 5_000_000)
    with pytest.raises(UnsafeInputError, match="compresión"):
        safe_zip_members(z)


def test_zip_too_many_members(tmp_path: Path) -> None:
    z = tmp_path / "many.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for i in range(20):
            zf.writestr(f"f{i}.csv", "a")
    with pytest.raises(UnsafeInputError, match="demasiadas entradas"):
        safe_zip_members(z, max_members=10)
